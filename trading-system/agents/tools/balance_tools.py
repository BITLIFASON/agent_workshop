from typing import Dict, Optional, Any
import asyncpg
from .base_tools import BaseTool, ToolResult
from pybit.unified_trading import HTTP
import aiohttp
from loguru import logger
from datetime import datetime
from langchain.tools import BaseTool
from pydantic import BaseModel

class DatabaseTool(BaseTool):
    def __init__(self, db_config: Dict[str, str]):
        super().__init__(
            name="database_tool",
            description="Tool for database operations with active and history lots"
        )
        self.db_config = db_config
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> ToolResult:
        """Initialize database connection and create tables if they don't exist"""
        try:
            self.pool = await asyncpg.create_pool(**self.db_config)
            logger.info("Database connection initialized successfully")
            return ToolResult(success=True)

        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            return ToolResult(success=False, error=str(e))

    async def execute(self, operation: str, *args) -> ToolResult:
        if not self.pool:
            return ToolResult(success=False, error="Database pool not initialized")

        try:
            async with self.pool.acquire() as conn:
                if operation == "get_active_lots":
                    result = await conn.fetch("SELECT * FROM active_lots")
                    return ToolResult(success=True, data=result)

                elif operation == "create_lot":
                    symbol, qty, price = args
                    await conn.execute(
                        "INSERT INTO active_lots (symbol, qty, price) VALUES ($1, $2, $3)",
                        symbol, qty, price
                    )
                    return ToolResult(success=True)

                elif operation == "delete_lot":
                    symbol = args[0]
                    await conn.execute("DELETE FROM active_lots WHERE symbol = $1", symbol)
                    return ToolResult(success=True)

                elif operation == "create_history_lot":
                    action, symbol, qty, price = args
                    await conn.execute(
                        "INSERT INTO history_lots (action, symbol, qty, price) VALUES ($1, $2, $3, $4)",
                        action, symbol, qty, price
                    )
                    return ToolResult(success=True)

            return ToolResult(success=False, error="Unknown operation")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def cleanup(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

class ManagementServiceTool(BaseTool):
    def __init__(self, config: Dict[str, str]):
        super().__init__(
            name="management_service",
            description="Tool for interacting with management service"
        )
        self.host = config['host']
        self.port = config['port']
        self.token = config['token']
        self.base_url = f"http://{self.host}:{self.port}"

    async def execute(self, operation: str, **kwargs) -> ToolResult:
        try:
            params = {"api_key": self.token}

            if operation == "get_system_status":
                response = await self._make_request("GET", "/get_system_status", params=params)
                return ToolResult(success=True, data=response["system_status"])

            elif operation == "get_price_limit":
                response = await self._make_request("GET", "/get_price_limit", params=params)
                return ToolResult(success=True, data=response["price_limit"])

            elif operation == "get_fake_balance":
                response = await self._make_request("GET", "/get_fake_balance", params=params)
                return ToolResult(success=True, data=response["fake_balance"])

            elif operation == "get_num_available_lots":
                response = await self._make_request("GET", "/get_num_available_lots", params=params)
                return ToolResult(success=True, data=response["num_available_lots"])

            else:
                return ToolResult(success=False, error="Unknown operation")

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

class BybitTradingTool(BaseTool):
    def __init__(self, config: Dict[str, str]):
        super().__init__(
            name="bybit_trading",
            description="Tool for executing trades on Bybit"
        )
        self.client = HTTP(
            testnet=False,
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            demo=config.get('demo_mode', 'True') == 'True'
        )

    async def execute(self, operation: str, **kwargs) -> ToolResult:
        try:

            if operation == "get_wallet_balance":
                balance_info = self.client.get_wallet_balance(accountType="UNIFIED",
                                                              coin="USDT")["result"]["list"][0]["coin"][0]["walletBalance"]
                balance_info = float(balance_info) if balance_info != '' else 0
                return ToolResult(success=True, data=balance_info)

            if operation == "get_coin_balance":
                symbol = kwargs.get('symbol', '')
                if symbol[:-4] not in [item['coin'] for item in self.client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
                    return ToolResult(success=True, data=0)
                symbol_wallet_balance = self.client.get_wallet_balance(accountType="UNIFIED", coin=symbol[:-4])["result"]["list"][0]["coin"][0]["walletBalance"]
                symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
                return ToolResult(success=True, data=symbol_wallet_balance)

            if operation == "get_coin_info":
                symbol = kwargs.get('symbol', '')
                symbol_qty_info = self.client.get_instruments_info(category="linear",
                                                                   symbol=symbol)["result"]["list"][0]["lotSizeFilter"]
                max_qty = float(symbol_qty_info.get("maxMktOrderQty"))
                min_qty = float(symbol_qty_info.get("minOrderQty"))
                step_qty = symbol_qty_info.get("qtyStep")
                min_order_usdt = int(symbol_qty_info.get("minNotionalValue"))
                symbol_info={"max_qty":max_qty,
                             "min_qty":min_qty,
                             "step_qty":step_qty,
                             "min_order_usdt":min_order_usdt}
                return ToolResult(success=True, data=symbol_info)

            else:
                return ToolResult(success=False, error="Unknown operation")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
