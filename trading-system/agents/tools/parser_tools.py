from typing import Dict, Any, Optional, List, Type, Callable
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pydantic import BaseModel, Field, ConfigDict, field_validator
from loguru import logger
from crewai.tools import BaseTool
import asyncio
from ..utils.models import SignalData, SignalParserInput


class SignalParserTool(BaseTool):
    """Tool for parsing trading signals from text messages.
    
    This tool is responsible for parsing and validating trading signals
    from text messages in specific formats. It handles both buy and sell
    signals with their respective parameters.
    
    Handles two specific formats:
    Buy: ⬆️ SYMBOL BUY LONG PRICE: X.XXXX
    Sell: ✔️ SYMBOL 🟢 PROFIT: +/-XX.XX% CLOSE LONG PRICE: X.XXXX
    """
    name: str = "signal_parser"
    description: str = """Parse trading signals from text messages.
    Handles two specific formats:
    Buy: ⬆️ SYMBOL BUY LONG PRICE: X.XXXX
    Sell: ✔️ SYMBOL 🟢 PROFIT: +/-XX.XX% CLOSE LONG PRICE: X.XXXX"""
    args_schema: Type[BaseModel] = SignalParserInput
    buy_pattern: re.Pattern = Field(default=None, description="Regex pattern for buy signals")
    sell_pattern: re.Pattern = Field(default=None, description="Regex pattern for sell signals")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        """Initialize SignalParserTool"""
        super().__init__(**kwargs)
        self.buy_pattern = re.compile(r'.\s(\w+)\s+BUY LONG PRICE:\s+(\d+\.\d+)')
        self.sell_pattern = re.compile(r'.\s(\w+)\s+(?:🟢|🔴)\sPROFIT:\s+((?:[+-]\s*)?\d+\.\d+)\%\sCLOSE LONG PRICE:\s+(\d+\.\d+)')

    def _parse_buy_signal(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse buy signal message"""
        try:
            match = self.buy_pattern.search(text)
            if not match:
                return None
                
            return {
                "symbol": match.group(1),
                "action": "buy",
                "price": float(match.group(2))
            }
        except Exception as e:
            logger.error(f"Error parsing buy signal: {e}")
            return None

    def _parse_sell_signal(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse sell signal message"""
        try:
            match = self.sell_pattern.search(text)
            if not match:
                return None
                
            profit_str = match.group(2).replace(' ', '')
            if not profit_str.startswith(('+', '-')):
                profit_str = '+' + profit_str
                
            return {
                "symbol": match.group(1),
                "action": "sell",
                "price": float(match.group(3)),
                "profit_percentage": float(profit_str)
            }
        except Exception as e:
            logger.error(f"Error parsing sell signal: {e}")
            return None

    def _run(self, message: str) -> Optional[SignalData]:
        """Parse trading signal from message text"""
        try:
            signal_data = self._parse_buy_signal(message)
            if not signal_data:
                signal_data = self._parse_sell_signal(message)

            if signal_data:
                logger.info(f"Successfully parsed signal: {signal_data}")
                return SignalData(**signal_data)
            
            logger.warning(f"Failed to parse message: {message}")
            return None

        except Exception as e:
            logger.error(f"Error parsing signal: {e}")
            return None

    async def _arun(self, message: str) -> Optional[SignalData]:
        """Async version of _run"""
        return self._run(message)


class TelegramListenerTool(BaseTool):
    """Tool for listening to Telegram messages.
    
    This tool provides functionality to connect to Telegram and listen
    for messages in specified channels. It handles message reception
    and forwards them to the appropriate callback for processing.
    """
    name: str = "telegram_listener"
    description: str = "Tool for listening to Telegram messages"
    client: Optional[TelegramClient] = Field(default=None, description="Telegram client")
    channel_url: str = Field(str, description="Channel URL to listen to")
    message_callback: Optional[Callable] = Field(default=None, description="Callback for new messages")
    max_retries: int = Field(int, description="Maximum number of reconnection attempts")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_token: str,
        channel_url: str,
        message_callback: Optional[Callable] = None,
        max_retries: int = 3,
        **kwargs
    ):
        """Initialize TelegramListenerTool"""
        super().__init__(**kwargs)
        self.channel_url = channel_url
        self.message_callback = message_callback
        self.max_retries = max_retries
        self.client = TelegramClient(
            StringSession(session_token),
            api_id,
            api_hash
        )

    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _setup_message_handler(self):
        """Setup message handler for Telegram channel"""
        @self.client.on(events.NewMessage(chats=[self.channel_url]))
        async def new_message_handler(event):
            try:
                if self.message_callback:
                    message_text = event.message.message.strip()
                    logger.info(f"Received message: {message_text}")
                    await self.message_callback(message_text)
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _connect_with_retry(self) -> bool:
        """Connect to Telegram with retry logic"""
        retries = 0
        while retries < self.max_retries:
            try:
                if not self.client.is_connected():
                    await self.client.connect()
                    
                if not await self.client.is_user_authorized():
                    await self.client.start()
                    
                return True
            except Exception as e:
                retries += 1
                logger.error(f"Connection attempt {retries} failed: {e}")
                if retries < self.max_retries:
                    await asyncio.sleep(10)  # Wait before retry
                
        return False

    async def _arun(self, **kwargs: Any) -> Dict[str, Any]:
        """Run the Telegram listener"""
        try:
            # Setup message handler
            await self._setup_message_handler()
            
            # Connect with retry logic
            if not await self._connect_with_retry():
                return {
                    "status": "error",
                    "message": "Failed to connect to Telegram after maximum retries"
                }

            logger.info("Successfully connected to Telegram")
            
            # Run until disconnected
            async with self.client:
                await self.client.run_until_disconnected()
                
            return {"status": "success"}
            
        except Exception as e:
            logger.error(f"Error in Telegram listener: {e}")
            return {"status": "error", "message": str(e)}

    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.disconnect()
            self.client = None
