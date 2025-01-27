from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pydantic import BaseModel, Field, ConfigDict, field_validator
from loguru import logger
from crewai.tools import BaseTool


class SignalData(BaseModel):
    """Model for parsed trading signals"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'MINAUSDT')")
    action: str = Field(..., description="Trading action ('buy' or 'sell')")
    price: float = Field(..., description="Entry or exit price for the trade")
    profit_percentage: Optional[float] = Field(None, description="Profit percentage for sell signals")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )

    @field_validator("symbol")
    def validate_symbol(cls, v: str) -> str:
        if not v.endswith("USDT"):
            raise ValueError("Symbol must end with USDT")
        if len(v) < 5:
            raise ValueError("Invalid symbol length")
        return v.upper()

    @field_validator("action")
    def validate_action(cls, v: str) -> str:
        if v.lower() not in ["buy", "sell"]:
            raise ValueError("Action must be either 'buy' or 'sell'")
        return v.lower()

    @field_validator("price")
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

    @field_validator("profit_percentage")
    def validate_profit_percentage(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not -100 <= v <= 1000:
            raise ValueError("Profit percentage must be between -100 and 1000")
        return v


class SignalParserInput(BaseModel):
    """Input schema for SignalParserTool"""
    message: str = Field(..., description="Message text to parse for trading signals")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )

    @field_validator("message")
    def validate_message(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Message must be a non-empty string")
        return v.strip()


class SignalParserTool(BaseTool):
    """Tool for parsing trading signals from text messages"""
    name: str = "signal_parser"
    description: str = """Parse trading signals from text messages.
    Handles two specific formats:
    Buy: ⬆️ SYMBOL BUY LONG PRICE: X.XXXX
    Sell: ✔️ SYMBOL 🟢 PROFIT: +/-XX.XX% CLOSE LONG PRICE: X.XXXX"""
    args_schema: Type[BaseModel] = SignalParserInput

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


class TelegramListenerInput(BaseModel):
    """Input schema for TelegramListenerTool"""
    channel_url: str = Field(..., description="Telegram channel URL to listen to")
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API hash")
    session_token: str = Field(..., description="Telegram session token")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )

    @field_validator("channel_url")
    def validate_channel_url(cls, v: str) -> str:
        if not v.startswith("https://t.me/"):
            raise ValueError("Channel URL must start with https://t.me/")
        return v


class TelegramListenerTool(BaseTool):
    """Tool for listening to Telegram messages"""
    name: str = "telegram_listener"
    description: str = "Listen to Telegram messages from specified channels"
    args_schema: Type[BaseModel] = TelegramListenerInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        """Initialize TelegramListenerTool"""
        super().__init__(**kwargs)
        self.client: Optional[TelegramClient] = None
        self._message_handlers: List[Any] = []
        self._is_listening: bool = False

    def add_message_handler(self, handler):
        """Add a message handler callback"""
        self._message_handlers.append(handler)

    async def initialize(self, api_id: int, api_hash: str, session_token: str) -> Dict[str, Any]:
        """Initialize Telegram client"""
        try:
            self.client = TelegramClient(StringSession(session_token), api_id, api_hash)
            if not self.client.is_connected():
                await self.client.start()
            return {'success': True}
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            return {'success': False, 'error': str(e)}

    async def cleanup(self):
        """Cleanup Telegram client"""
        try:
            self._is_listening = False
            if self.client and self.client.is_connected():
                await self.client.disconnect()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _run(self, channel_url: str) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, channel_url: str, api_id: int, api_hash: str, session_token: str) -> Dict[str, Any]:
        """Start listening to messages from the specified channel"""
        try:
            if not self.client:
                init_result = await self.initialize(api_id, api_hash, session_token)
                if not init_result['success']:
                    return init_result

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

            try:
                await self.client.run_until_disconnected()
            except Exception as e:
                logger.error(f"Unexpected disconnect: {e}")
                return {'success': False, 'error': str(e)}

            return {'success': True}

        except Exception as e:
            logger.error(f"Error starting listener: {e}")
            return {'success': False, 'error': str(e)}
