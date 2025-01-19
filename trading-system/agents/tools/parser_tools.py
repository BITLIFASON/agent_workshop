from typing import Optional
from datetime import datetime
import os
import re
from .base_tools import BaseTool, ToolResult
from telethon import TelegramClient
from telethon.sessions import StringSession


class TelegramListenerTool(BaseTool):
    def __init__(self, api_id: int, api_hash: str, api_session_token: str):
        super().__init__(
            name="telegram_listener",
            description="Tool for listening to Telegram channels"
        )
        self.api_id = api_id
        self.api_hash = api_hash
        self.api_session_token = api_session_token
        self.client: Optional[TelegramClient] = None

    async def initialize(self) -> ToolResult:
        try:
            self.client = TelegramClient(StringSession(self.api_session_token),
                                         self.api_id,
                                         self.api_hash,
                                         system_version='4.16.30-vxAUTO')
            await self.client.start()
            return ToolResult(success=True)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def execute(self, channel_url: str) -> ToolResult:
        try:
            if not self.client:
                return ToolResult(success=False, error="Client not initialized")

            entity = await self.client.get_entity(channel_url)
            return ToolResult(success=True, data={"entity": entity})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def cleanup(self):
        if self.client:
            await self.client.disconnect()

class SignalParserTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="signal_parser",
            description="Tool for parsing trading signals from messages"
        )
        self.buy_pattern = re.compile(r'.\s(\w+)\s+BUY LONG PRICE:\s+(\d+\.\d+)')
        self.sell_pattern = re.compile(r'.\s(\w+)\s+..\sPROFIT:\s+(.\s*\d+\.\d+)\%\sCLOSE LONG PRICE:\s+(\d+\.\d+)')

    async def execute(self, message: str) -> ToolResult:
        try:
            match_buy = self.buy_pattern.search(message)
            if match_buy:
                signal = {
                    "symbol": match_buy.group(1),
                    "action": "buy",
                    "price": float(match_buy.group(2)),
                    "timestamp": datetime.now()
                }
                return ToolResult(success=True, data=signal)

            match_sell = self.sell_pattern.search(message)
            if match_sell:
                signal = {
                    "symbol": match_sell.group(1),
                    "action": "sell",
                    "price": float(match_sell.group(3)),
                    "profit_percentage": float(match_sell.group(2).replace(' ', '')),
                    "timestamp": datetime.now()
                }
                return ToolResult(success=True, data=signal)

            return ToolResult(success=True, data=None)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
