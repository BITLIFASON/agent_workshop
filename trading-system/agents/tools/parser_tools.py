from typing import Dict, Any, Optional
from datetime import datetime
import os
import re
from .base_tools import BaseTool, ToolResult
from telethon import TelegramClient
from telethon.sessions import StringSession
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from loguru import logger


class SignalData(BaseModel):
    """Model for parsed trading signals"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')")
    action: str = Field(..., description="Trading action ('buy' or 'sell')")
    entry_price: float = Field(..., description="Entry price for the trade")
    stop_loss: float = Field(None, description="Stop loss price level")
    take_profit: float = Field(None, description="Take profit price level")
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(default=0.0, description="Signal confidence score (0-1)")
    additional_info: Dict[str, Any] = Field(default_factory=dict)

class SignalParserTool(BaseTool):
    name = "signal_parser"
    description = """Parse trading signals from text messages.
    Identify key trading information like symbol, action (buy/sell), entry price, stop loss, and take profit levels.
    Filter out noise and extract only relevant trading data."""

    def _extract_symbol(self, text: str) -> Optional[str]:
        """Extract trading pair symbol from text"""
        # Common patterns for crypto pairs
        patterns = [
            r'([A-Z]+)/([A-Z]+)',  # BTC/USDT
            r'([A-Z]+)USDT',       # BTCUSDT
            r'([A-Z]+)-([A-Z]+)',  # BTC-USDT
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.upper())
            if matches:
                if isinstance(matches[0], tuple):
                    return f"{matches[0][0]}/{matches[0][1]}"
                return matches[0]
        return None

    def _extract_prices(self, text: str) -> Dict[str, Optional[float]]:
        """Extract price levels from text"""
        prices = {
            'entry_price': None,
            'stop_loss': None,
            'take_profit': None
        }
        
        # Price patterns
        price_patterns = {
            'entry_price': [
                r'entry[:\s]+(\d+\.?\d*)',
                r'enter[:\s]+(\d+\.?\d*)',
                r'price[:\s]+(\d+\.?\d*)',
            ],
            'stop_loss': [
                r'sl[:\s]+(\d+\.?\d*)',
                r'stop[:\s\-]+loss[:\s]+(\d+\.?\d*)',
            ],
            'take_profit': [
                r'tp[:\s]+(\d+\.?\d*)',
                r'target[:\s]+(\d+\.?\d*)',
                r'take[:\s\-]+profit[:\s]+(\d+\.?\d*)',
            ]
        }

        for price_type, patterns in price_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text.lower())
                if matches:
                    try:
                        prices[price_type] = float(matches[0])
                        break
                    except ValueError:
                        continue
        
        return prices

    def _extract_action(self, text: str) -> Optional[str]:
        """Extract trading action (buy/sell) from text"""
        text = text.lower()
        
        buy_indicators = ['buy', 'long', 'bullish', 'calls', 'accumulate']
        sell_indicators = ['sell', 'short', 'bearish', 'puts', 'dump']
        
        for indicator in buy_indicators:
            if indicator in text:
                return 'buy'
        
        for indicator in sell_indicators:
            if indicator in text:
                return 'sell'
        
        return None

    def _calculate_confidence(self, signal_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on signal completeness"""
        required_fields = ['symbol', 'action', 'entry_price']
        optional_fields = ['stop_loss', 'take_profit']
        
        # Start with base confidence
        confidence = 0.5
        
        # Check required fields
        for field in required_fields:
            if signal_data.get(field):
                confidence += 0.1
            else:
                confidence -= 0.2
        
        # Check optional fields
        for field in optional_fields:
            if signal_data.get(field):
                confidence += 0.1
        
        return max(0.0, min(1.0, confidence))

    def _run(self, message: str) -> Optional[SignalData]:
        """Parse trading signal from message text"""
        try:
            # Extract basic signal components
            symbol = self._extract_symbol(message)
            action = self._extract_action(message)
            prices = self._extract_prices(message)
            
            # Validate required fields
            if not all([symbol, action, prices['entry_price']]):
                logger.warning("Missing required signal components")
                return None
            
            # Create signal data
            signal_data = {
                'symbol': symbol,
                'action': action,
                'entry_price': prices['entry_price'],
                'stop_loss': prices['stop_loss'],
                'take_profit': prices['take_profit'],
                'timestamp': datetime.now(),
            }
            
            # Calculate confidence
            signal_data['confidence'] = self._calculate_confidence(signal_data)
            
            # Create SignalData instance
            return SignalData(**signal_data)
            
        except Exception as e:
            logger.error(f"Error parsing signal: {e}")
            return None

    async def _arun(self, message: str) -> Optional[SignalData]:
        return self._run(message)

class TelegramListenerTool(BaseTool):
    name = "telegram_listener"
    description = "Listen to Telegram messages from specified channels"

    def __init__(self, api_id: int, api_hash: str, session_token: str):
        super().__init__()
        self.client = TelegramClient(session_token, api_id, api_hash)

    async def initialize(self):
        """Initialize Telegram client"""
        try:
            await self.client.start()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def cleanup(self):
        """Cleanup Telegram client"""
        if self.client:
            await self.client.disconnect()

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("This tool doesn't support direct execution")
