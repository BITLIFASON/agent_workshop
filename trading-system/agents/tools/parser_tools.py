from typing import Dict, Any, Optional, List, Type, Callable
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pydantic import BaseModel, Field, ConfigDict, field_validator
from loguru import logger
from crewai.tools import BaseTool
import asyncio
from ..utils.models import SignalParserInput, SignalData


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
        self.buy_pattern = re.compile(r'⬆️\s+(\w+)\s+BUY\s+LONG\s+PRICE:\s+(\d+\.\d+)')
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

    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Clear regex patterns
            self.buy_pattern = None
            self.sell_pattern = None
            logger.info("SignalParserTool cleanup completed")
        except Exception as e:
            logger.error(f"Error during SignalParserTool cleanup: {e}")
