from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import re
from telethon import TelegramClient
from telethon.sessions import StringSession
from pydantic import BaseModel, Field
from loguru import logger
from telethon import events
import asyncio
from crewai.tools import BaseTool


class SignalData(BaseModel):
    """Model for parsed trading signals"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'MINAUSDT')")
    action: str = Field(..., description="Trading action ('buy' or 'sell')")
    price: float = Field(..., description="Entry or exit price for the trade")
    profit_percentage: Optional[float] = Field(None, description="Profit percentage for sell signals")
    timestamp: datetime = Field(default_factory=datetime.now)


class SignalParserInput(BaseModel):
    """Input schema for SignalParserTool"""
    message: str = Field(..., description="Message text to parse for trading signals")


class SignalParserTool(BaseTool):
    name: str = "signal_parser"
    description: str = """Parse trading signals from text messages.
    Handles two specific formats:
    Buy: ⬆️ SYMBOL BUY LONG PRICE: X.XXXX
    Sell: ✔️ SYMBOL 🟢 PROFIT: +/-XX.XX% CLOSE LONG PRICE: X.XXXX"""
    args_schema: Type[BaseModel] = SignalParserInput

    def __init__(self):
        super().__init__()
        # Compile regex patterns
        self.buy_pattern = re.compile(r'.\s(\w+)\s+BUY LONG PRICE:\s+(\d+\.\d+)')
        self.sell_pattern = re.compile(r'.\s(\w+)\s+(?:🟢|🔴)\sPROFIT:\s+((?:[+-]\s*)?\d+\.\d+)\%\sCLOSE LONG PRICE:\s+(\d+\.\d+)')

    def _parse_buy_signal(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse buy signal message"""
        match = self.buy_pattern.search(text)
        if match:
            return {
                "symbol": match.group(1),
                "action": "buy",
                "price": float(match.group(2))
            }
        return None

    def _parse_sell_signal(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse sell signal message"""
        match = self.sell_pattern.search(text)
        if match:
            # Clean up profit percentage string (remove spaces and ensure sign)
            profit_str = match.group(2).replace(' ', '')
            if not profit_str.startswith(('+', '-')):
                profit_str = '+' + profit_str
            
            return {
                "symbol": match.group(1),
                "action": "sell",
                "price": float(match.group(3)),
                "profit_percentage": float(profit_str)
            }
        return None

    def _run(self, message: str) -> Optional[SignalData]:
        """Parse trading signal from message text"""
        try:
            # Try to parse as buy signal first
            signal_data = self._parse_buy_signal(message)
            if not signal_data:
                # If not a buy signal, try to parse as sell signal
                signal_data = self._parse_sell_signal(message)

            if signal_data:
                logger.info(f"Successfully parsed signal: {signal_data}")
                return SignalData(**signal_data)
            else:
                logger.warning(f"Failed to parse message: {message}")
                return None

        except Exception as e:
            logger.error(f"Error parsing signal: {e}")
            return None

    async def _arun(self, message: str) -> Optional[SignalData]:
        """Async version of _run"""
        return self._run(message)


class TelegramListenerInput(BaseModel):
    """Input schema for TelegramListenerTool"""
    channel_url: str = Field(..., description="URL of the Telegram channel to listen to")


class TelegramListenerTool(BaseTool):
    name: str = "telegram_listener"
    description: str = "Listen to Telegram messages from specified channels"
    args_schema: Type[BaseModel] = TelegramListenerInput

    def __init__(self, api_id: int, api_hash: str, session_token: str):
        super().__init__()
        self.client = TelegramClient(StringSession(session_token), api_id, api_hash)
        self._message_handlers: List[Any] = []
        self._is_listening: bool = False
        self._disconnect_event: Optional[asyncio.Event] = None

    def add_message_handler(self, handler):
        """Add a message handler callback"""
        self._message_handlers.append(handler)

    async def initialize(self) -> Dict[str, Any]:
        """Initialize Telegram client"""
        try:
            if not self.client.is_connected():
                await self.client.start()
            self._disconnect_event = asyncio.Event()
            return {'success': True}
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            return {'success': False, 'error': str(e)}

    async def cleanup(self):
        """Cleanup Telegram client"""
        try:
            self._is_listening = False
            if self._disconnect_event:
                self._disconnect_event.set()
            if self.client and self.client.is_connected():
                await self.client.disconnect()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _run(self, channel_url: str) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, channel_url: str) -> Dict[str, Any]:
        """Start listening to messages from the specified channel"""
        try:
            if not self.client.is_connected():
                await self.initialize()

            if self._is_listening:
                logger.warning("Already listening to channel")
                return {'success': True}

            @self.client.on(events.NewMessage(chats=[channel_url]))
            async def message_handler(event):
                try:
                    for handler in self._message_handlers:
                        await handler(event)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")

            self._is_listening = True
            logger.info(f"Started listening to channel: {channel_url}")

            # Run the client until disconnect event is set
            try:
                await self.client.run_until_disconnected()
            except Exception as e:
                if not self._disconnect_event.is_set():
                    logger.error(f"Unexpected disconnect: {e}")
                    return {'success': False, 'error': str(e)}

            return {'success': True}

        except Exception as e:
            logger.error(f"Error starting listener: {e}")
            return {'success': False, 'error': str(e)}
