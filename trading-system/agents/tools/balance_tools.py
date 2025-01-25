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

class BalanceCheckerTool(BaseTool):
    name = "balance_checker"
    description = "Check current balance and open positions on the exchange"

    def __init__(self, bybit_config: Dict[str, str]):
        super().__init__()
        self.api_key = bybit_config["api_key"]
        self.api_secret = bybit_config["api_secret"]
        self.testnet = bybit_config.get("testnet", False)

    async def get_balance(self) -> Dict[str, Any]:
        """Get current balance and open positions"""
        try:
            # Here you would implement actual Bybit API calls
            # This is a placeholder implementation
            async with aiohttp.ClientSession() as session:
                # Get wallet balance
                balance_response = await self._get_wallet_balance(session)
                
                # Get open positions
                positions_response = await self._get_positions(session)

                return {
                    "success": True,
                    "data": {
                        "balance": balance_response["result"]["USDT"]["available_balance"],
                        "positions": positions_response["result"]
                    }
                }
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {"success": False, "error": str(e)}

    async def _get_wallet_balance(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Get wallet balance from Bybit"""
        # Implement actual Bybit API call
        pass

    async def _get_positions(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Get open positions from Bybit"""
        # Implement actual Bybit API call
        pass

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, *args, **kwargs):
        return await self.get_balance()

class RiskCalculatorTool(BaseTool):
    name = "risk_calculator"
    description = "Calculate trade risk based on position size and stop loss"

    def __init__(self, max_risk_per_trade: float, max_total_risk: float):
        super().__init__()
        self.max_risk_per_trade = max_risk_per_trade
        self.max_total_risk = max_total_risk

    def calculate_risk(
        self,
        entry_price: float,
        stop_loss: Optional[float],
        position_size: float,
        account_balance: float,
        open_positions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate risk for a trade"""
        try:
            # Calculate risk if stop loss is provided
            if stop_loss:
                risk_per_unit = abs(entry_price - stop_loss)
                total_risk = risk_per_unit * position_size
                risk_percentage = total_risk / account_balance
            else:
                # Use maximum possible risk if no stop loss
                risk_percentage = self.max_risk_per_trade

            # Calculate current total risk from open positions
            current_risk = self._calculate_current_risk(open_positions, account_balance)
            total_risk_percentage = current_risk + risk_percentage

            return {
                "success": True,
                "data": {
                    "risk_amount": total_risk,
                    "risk_percentage": risk_percentage,
                    "total_risk_percentage": total_risk_percentage,
                    "within_limits": (
                        risk_percentage <= self.max_risk_per_trade and
                        total_risk_percentage <= self.max_total_risk
                    )
                }
            }
        except Exception as e:
            logger.error(f"Error calculating risk: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_current_risk(
        self,
        open_positions: Dict[str, Any],
        account_balance: float
    ) -> float:
        """Calculate current risk from open positions"""
        total_risk = 0.0
        for position in open_positions.values():
            if position.get("stop_loss"):
                risk = abs(position["entry_price"] - position["stop_loss"]) * position["size"]
                total_risk += risk / account_balance
        return total_risk

    def _run(self, *args, **kwargs):
        return self.calculate_risk(*args, **kwargs)

    async def _arun(self, *args, **kwargs):
        return self.calculate_risk(*args, **kwargs)

class PositionSizeTool(BaseTool):
    name = "position_sizer"
    description = "Calculate optimal position size based on risk parameters"

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: Optional[float],
        account_balance: float,
        max_risk_amount: float,
        symbol_limits: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate optimal position size"""
        try:
            # Get symbol trading limits
            min_qty = symbol_limits.get("min_qty", 0.001)
            max_qty = symbol_limits.get("max_qty", float("inf"))
            step_size = symbol_limits.get("step_size", 0.001)
            min_notional = symbol_limits.get("min_notional", 10.0)  # Minimum order value in USDT

            # Calculate position size based on risk
            if stop_loss:
                risk_per_unit = abs(entry_price - stop_loss)
                max_position_size = max_risk_amount / risk_per_unit
            else:
                # If no stop loss, use a conservative position size
                max_position_size = (max_risk_amount / entry_price) * account_balance

            # Adjust for symbol limits
            position_size = min(max_position_size, max_qty)
            position_size = max(position_size, min_qty)

            # Round to step size
            position_size = round(position_size / step_size) * step_size

            # Check minimum notional value
            if position_size * entry_price < min_notional:
                if min_notional / entry_price > max_position_size:
                    return {
                        "success": False,
                        "error": "Cannot satisfy minimum notional value within risk limits"
                    }
                position_size = min_notional / entry_price
                position_size = round(position_size / step_size) * step_size

            return {
                "success": True,
                "data": {
                    "position_size": position_size,
                    "notional_value": position_size * entry_price,
                    "max_position_size": max_position_size
                }
            }
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"success": False, "error": str(e)}

    def _run(self, *args, **kwargs):
        return self.calculate_position_size(*args, **kwargs)

    async def _arun(self, *args, **kwargs):
        return self.calculate_position_size(*args, **kwargs)