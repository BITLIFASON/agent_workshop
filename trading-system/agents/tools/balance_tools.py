from typing import Dict, Any, Optional, Type, List, Union, Annotated
import asyncpg
from pybit.unified_trading import HTTP
import aiohttp
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool
from .trading_tools import CoinInfo
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseOperationInput(BaseModel):
    """Input schema for DatabaseTool"""
    operation: str = Field(
        str,
        description="Operation to perform (get_active_lots, create_lot, delete_lot, create_history_lot)"
    )
    symbol: Optional[str] = Field(None, description="Trading pair symbol")
    qty: Optional[float] = Field(None, description="Order quantity")
    price: Optional[float] = Field(None, description="Order price")
    action: Optional[str] = Field(None, description="Action type (for history lots)")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class DatabaseTool(BaseTool):
    """Tool for database operations.
    
    This tool provides functionality to interact with the database,
    including managing lots, historical data, and other trading records.
    """
    name: str = "database"
    description: str = "Tool for database operations"
    args_schema: Type[BaseModel] = DatabaseOperationInput
    pool: Optional[asyncpg.Pool] = Field(default=None, description="Database connection pool")
    host: str = Field(str, description="Database host")
    port: str = Field(str, description="Database port")
    user: str = Field(str, description="Database user")
    password: str = Field(str, description="Database password")
    database: str = Field(str, description="Database name")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        host: str,
        port: str,
        user: str,
        password: str,
        database: str,
        **kwargs
    ):
        """Initialize DatabaseTool"""
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool = None

    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, operation: str, **kwargs: Any) -> Dict[str, Any]:
        """Run database operation"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )

        try:
            if operation == "create_lot":
                return await self._create_lot(**kwargs)
            elif operation == "get_active_lots":
                return await self._get_active_lots(**kwargs)
            elif operation == "delete_lot":
                return await self._delete_lot(**kwargs)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        except Exception as e:
            logger.error(f"Error in database operation: {e}")
            return {"status": "error", "message": str(e)}

    async def _create_lot(self, symbol: str, qty: float, price: float) -> Dict[str, Any]:
        """Create new lot record"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO active_lots (symbol, qty, price, created_at)
                    VALUES ($1, $2, $3, NOW())
                    """,
                    symbol, qty, price
                )
                return {"status": "success"}
        except Exception as e:
            logger.error(f"Error creating lot: {e}")
            return {"status": "error", "message": str(e)}

    async def _get_active_lots(self, symbol: str) -> Dict[str, Any]:
        """Get active lots for symbol"""
        try:
            async with self.pool.acquire() as conn:
                lots = await conn.fetch(
                    """
                    SELECT * FROM active_lots
                    WHERE symbol = $1
                    ORDER BY created_at ASC
                    """,
                    symbol
                )
                return {"status": "success", "data": lots}
        except Exception as e:
            logger.error(f"Error getting active lots: {e}")
            return {"status": "error", "message": str(e)}

    async def _delete_lot(self, symbol: str) -> Dict[str, Any]:
        """Delete lot record"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    DELETE FROM active_lots
                    WHERE symbol = $1
                    """,
                    symbol
                )
                return {"status": "success"}
        except Exception as e:
            logger.error(f"Error deleting lot: {e}")
            return {"status": "error", "message": str(e)}

    async def cleanup(self):
        """Cleanup resources"""
        if self.pool:
            await self.pool.close()
            self.pool = None


class ManagementServiceInput(BaseModel):
    """Input schema for ManagementServiceTool"""
    operation: str = Field(
        str,
        description="Operation to perform (get_system_status, get_price_limit, get_fake_balance, get_num_available_lots)"
    )

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class ManagementServiceTool(BaseTool):
    """Tool for interacting with Management Service.
    
    This tool provides functionality to interact with the management service,
    including system status checks, price limit verification, and other
    management operations.
    """
    name: str = "management_service"
    description: str = "Tool for interacting with Management Service"
    args_schema: Type[BaseModel] = ManagementServiceInput
    session: Optional[aiohttp.ClientSession] = Field(default=None, description="HTTP session")
    host: str = Field(str, description="Management service host")
    port: str = Field(str, description="Management service port")
    token: str = Field(str, description="Management service token")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        host: str,
        port: str,
        token: str,
        **kwargs
    ):
        """Initialize ManagementServiceTool"""
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.token = token
        self.session = None

    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, operation: str, **kwargs: Any) -> Dict[str, Any]:
        """Run management service operation"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                base_url=f"http://{self.host}:{self.port}",
                headers={"Authorization": f"Bearer {self.token}"}
            )

        try:
            if operation == "get_system_status":
                return await self._get_system_status()
            elif operation == "get_price_limits":
                return await self._get_price_limits(**kwargs)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        except Exception as e:
            logger.error(f"Error in management service operation: {e}")
            return {"status": "error", "message": str(e)}

    async def _get_system_status(self) -> Dict[str, Any]:
        """Get system status from management service"""
        try:
            async with self.session.get("/api/v1/system/status") as response:
                if response.status == 200:
                    data = await response.json()
                    return {"status": "success", "data": data}
                else:
                    return {
                        "status": "error",
                        "message": f"HTTP {response.status}: {await response.text()}"
                    }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"status": "error", "message": str(e)}

    async def _get_price_limits(self, symbol: str) -> Dict[str, Any]:
        """Get price limits for symbol"""
        try:
            async with self.session.get(f"/api/v1/limits/{symbol}") as response:
                if response.status == 200:
                    data = await response.json()
                    return {"status": "success", "data": data}
                else:
                    return {
                        "status": "error",
                        "message": f"HTTP {response.status}: {await response.text()}"
                    }
        except Exception as e:
            logger.error(f"Error getting price limits: {e}")
            return {"status": "error", "message": str(e)}

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None


class BybitOperationParams(BaseModel):
    """Base model for Bybit operation parameters"""
    symbol: Optional[str] = Field(None, description="Trading pair symbol")


class BybitTradingInput(BaseModel):
    """Input schema for BybitTradingTool"""
    operation: str = Field(str, description="Operation to perform")
    params: BybitOperationParams = Field(default_factory=BybitOperationParams)


class BybitTradingTool(BaseTool):
    """Tool for executing trades on Bybit exchange"""
    name: str = "bybit_trading"
    description: str = "Tool for executing trades on Bybit"
    args_schema: Type[BaseModel] = BybitTradingInput
    client: Type[HTTP] = Field(default=None, description="Bybit HTTP client")
    logger: SkipValidation[Any] = Field(default=None, description="Logger instance")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        demo_mode: bool = True,
        **kwargs
    ):
        """Initialize BybitTradingTool"""
        super().__init__(**kwargs)
        self.client = HTTP(
            testnet=demo_mode,
            api_key=api_key,
            api_secret=api_secret
        )
        self.logger = logger

    def _run(self, operation: str, params: BybitOperationParams) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, operation: str, params: BybitOperationParams) -> Dict[str, Any]:
        try:
            if operation == "get_wallet_balance":
                balance_info = self.client.get_wallet_balance(accountType="UNIFIED",
                                                              coin="USDT")["result"]["list"][0]["coin"][0]["walletBalance"]
                balance_info = float(balance_info) if balance_info != '' else 0
                return {"success": True, "data": balance_info}

            if operation == "get_coin_balance":
                symbol = params.symbol or ''
                if symbol[:-4] not in [item['coin'] for item in self.client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
                    return {"success": True, "data": 0}
                symbol_wallet_balance = self.client.get_wallet_balance(accountType="UNIFIED", coin=symbol[:-4])["result"]["list"][0]["coin"][0]["walletBalance"]
                symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
                return {"success": True, "data": symbol_wallet_balance}

            if operation == "get_coin_info":
                symbol = params.symbol or ''
                symbol_qty_info = self.client.get_instruments_info(category="linear",
                                                                   symbol=symbol)["result"]["list"][0]["lotSizeFilter"]
                coin_info = CoinInfo(
                    max_qty=float(symbol_qty_info.get("maxMktOrderQty")),
                    min_qty=float(symbol_qty_info.get("minOrderQty")),
                    step_qty=symbol_qty_info.get("qtyStep"),
                    min_order_usdt=int(symbol_qty_info.get("minNotionalValue"))
                )
                return {"success": True, "data": coin_info.model_dump()}

            else:
                return {"success": False, "error": "Unknown operation"}

        except Exception as e:
            logger.error(f"Trading tool error: {e}")
            return {"success": False, "error": str(e)}

    async def _make_request(self, method: str, endpoint: str, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()


class BalanceOperationSchema(BaseModel):
    """Input schema for BalanceServiceTool"""
    operation: str = Field(str, description="Operation to perform (get_balance, update_balance)")
    amount: Optional[float] = Field(None, description="Amount to update balance by")


class BalanceServiceTool(BaseTool):
    """Tool for managing agent balance"""
    name: str = "balance_service"
    description: str = "Tool for managing agent balance"
    args_schema: Type[BaseModel] = BalanceOperationSchema
    balance: float = Field(default=0.0, description="Current balance")

    def __init__(
        self,
        initial_balance: float = 0.0,
        **kwargs
    ):
        """Initialize BalanceServiceTool."""
        super().__init__(**kwargs)
        self.balance = initial_balance

    def _run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        operation = kwargs.get("operation")
        amount = kwargs.get("amount")

        try:
            if operation == "get_balance":
                return {"success": True, "data": self.balance}
            elif operation == "update_balance":
                if amount is None:
                    return {"success": False, "error": "Amount is required for update_balance operation"}
                self.balance += amount
                logger.info(f"Balance updated by {amount}, new balance: {self.balance}")
                return {"success": True, "data": self.balance}
            return {"success": False, "error": "Unknown operation"}
        except Exception as e:
            logger.error(f"Balance operation error: {e}")
            return {"success": False, "error": str(e)}

    async def _arun(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Async version of _run"""
        return self._run(*args, **kwargs)
