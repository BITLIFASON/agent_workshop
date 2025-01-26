from typing import Dict, Any, Optional, Type, List, Union, Annotated
import asyncpg
from .base_tools import ToolResult
from pybit.unified_trading import HTTP
import aiohttp
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict, validator
from crewai.tools import BaseTool
from .trading_tools import CoinInfo
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration model"""
    host: str = Field(..., description="Database host")
    port: str = Field(..., description="Database port")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")
    database: str = Field(..., description="Database name")
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class FixedDatabaseOperationSchema(BaseModel):
    """Fixed input schema for DatabaseTool with predefined symbol"""
    operation: str = Field(..., description="Operation to perform (get_active_lots, create_lot, delete_lot, create_history_lot)")
    qty: Optional[float] = Field(None, description="Order quantity")
    price: Optional[float] = Field(None, description="Order price")
    action: Optional[str] = Field(None, description="Action type (for history lots)")


class DatabaseOperationSchema(FixedDatabaseOperationSchema):
    """Input schema for DatabaseTool"""
    symbol: Optional[str] = Field(None, description="Trading pair symbol")

    @validator("symbol")
    def validate_symbol(cls, v):
        if v is not None and not v.endswith("USDT"):
            raise ValueError("Symbol must end with USDT")
        return v

    @validator("qty")
    def validate_qty(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @validator("price")
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


class DatabaseTool(BaseTool):
    """Tool for database operations with active and history lots"""
    name: str = "database_tool"
    description: str = "Tool for database operations with active and history lots"
    args_schema: Type[BaseModel] = DatabaseOperationSchema
    pool: Optional[asyncpg.Pool] = None

    def __init__(
        self,
        host: str,
        port: str,
        user: str,
        password: str,
        database: str,
        symbol: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.db_config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database
        }

        if symbol is not None:
            self.symbol = symbol
            self.description = f"Tool for database operations with active and history lots for {symbol}"
            self.args_schema = FixedDatabaseOperationSchema

        self._generate_description()

    async def _create_tables(self, conn) -> bool:
        """Create necessary database tables if they don't exist"""
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS active_lots (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(50) NOT NULL,
                    qty NUMERIC(20, 8) NOT NULL,
                    price NUMERIC(20, 8) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS history_lots (
                    id SERIAL PRIMARY KEY,
                    action VARCHAR(50) NOT NULL,
                    symbol VARCHAR(50) NOT NULL,
                    qty NUMERIC(20, 8) NOT NULL,
                    price NUMERIC(20, 8) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            return True
        except Exception as e:
            return False

    async def initialize(self) -> ToolResult:
        """Initialize database connection and create tables if they don't exist"""
        try:
            self.pool = await asyncpg.create_pool(**self.db_config)
            async with self.pool.acquire() as conn:
                if not await self._create_tables(conn):
                    return ToolResult(success=False, error="Failed to create tables")
            return ToolResult(success=True)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _run(self, **kwargs: Any) -> Any:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, **kwargs: Any) -> Any:
        """Execute database operations asynchronously"""
        if not self.pool:
            return ToolResult(success=False, error="Database pool not initialized")

        operation = kwargs.get("operation")
        symbol = kwargs.get("symbol", getattr(self, "symbol", None))
        qty = kwargs.get("qty")
        price = kwargs.get("price")
        action = kwargs.get("action")

        try:
            async with self.pool.acquire() as conn:
                if operation == "get_active_lots":
                    return await self._get_active_lots(conn, symbol)
                elif operation == "create_lot":
                    return await self._create_lot(conn, symbol, qty, price)
                elif operation == "delete_lot":
                    return await self._delete_lot(conn, symbol)
                elif operation == "create_history_lot":
                    return await self._create_history_lot(conn, action, symbol, qty, price)
                return ToolResult(success=False, error="Unknown operation")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _get_active_lots(self, conn, symbol: str) -> ToolResult:
        result = await conn.fetch("""
            SELECT * FROM active_lots 
            WHERE symbol = $1
        """, symbol)
        return ToolResult(success=True, data=result)

    async def _create_lot(self, conn, symbol: str, qty: float, price: float) -> ToolResult:
        await conn.execute("""
            INSERT INTO active_lots (symbol, qty, price) 
            VALUES ($1, $2, $3)
        """, symbol, qty, price)
        return ToolResult(success=True)

    async def _delete_lot(self, conn, symbol: str) -> ToolResult:
        await conn.execute("""
            DELETE FROM active_lots 
            WHERE symbol = $1
        """, symbol)
        return ToolResult(success=True)

    async def _create_history_lot(self, conn, action: str, symbol: str, qty: float, price: float) -> ToolResult:
        await conn.execute("""
            INSERT INTO history_lots (action, symbol, qty, price) 
            VALUES ($1, $2, $3, $4)
        """, action, symbol, qty, price)
        return ToolResult(success=True)

    async def cleanup(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()


class ManagementServiceConfig(BaseModel):
    """Management service configuration model"""
    host: str = Field(..., description="Management service host")
    port: str = Field(..., description="Management service port")
    token: str = Field(..., description="Management service API token")
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class FixedManagementServiceSchema(BaseModel):
    """Fixed input schema for ManagementServiceTool"""
    operation: str = Field(..., description="Operation to perform (get_system_status, get_price_limit, get_fake_balance, get_num_available_lots)")


class ManagementServiceSchema(FixedManagementServiceSchema):
    """Input schema for ManagementServiceTool"""
    pass


class ManagementServiceTool(BaseTool):
    """Tool for interacting with management service"""
    name: str = "management_service"
    description: str = "Tool for interacting with management service"
    args_schema: Type[BaseModel] = ManagementServiceSchema

    def __init__(
        self,
        host: str,
        port: str,
        token: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.base_url = f"http://{host}:{port}"
        self.token = token
        self._generate_description()

    def _run(self, **kwargs: Any) -> Any:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, **kwargs: Any) -> Any:
        """Execute management service operations asynchronously"""
        operation = kwargs.get("operation")
        params = {"api_key": self.token}

        try:
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

    async def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> dict:
        """Make HTTP request to management service"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()


class BybitOperationParams(BaseModel):
    """Base model for Bybit operation parameters"""
    symbol: Optional[str] = Field(None, description="Trading pair symbol")


class BybitTradingInput(BaseModel):
    """Input schema for BybitTradingTool"""
    operation: str = Field(..., description="Operation to perform")
    params: BybitOperationParams = Field(default_factory=BybitOperationParams)


class BybitTradingTool(BaseTool):
    name: str = "bybit_trading"
    description: str = "Tool for executing trades on Bybit"
    args_schema: Type[BaseModel] = BybitTradingInput
    client: Optional[HTTP] = Field(default=None, description="Bybit HTTP client")
    logger: Any = Field(default=None, description="Logger instance")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, config: Dict[str, str]):
        super().__init__(name=self.name, description=self.description)
        self.client = HTTP(
            testnet=False,
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            demo=config.get('demo_mode', 'True') == 'True'
        )
        self.logger = logger

    def _run(self, operation: str, params: BybitOperationParams) -> ToolResult:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, operation: str, params: BybitOperationParams) -> ToolResult:
        try:
            if operation == "get_wallet_balance":
                balance_info = self.client.get_wallet_balance(accountType="UNIFIED",
                                                              coin="USDT")["result"]["list"][0]["coin"][0]["walletBalance"]
                balance_info = float(balance_info) if balance_info != '' else 0
                return ToolResult(success=True, data=balance_info)

            if operation == "get_coin_balance":
                symbol = params.symbol or ''
                if symbol[:-4] not in [item['coin'] for item in self.client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
                    return ToolResult(success=True, data=0)
                symbol_wallet_balance = self.client.get_wallet_balance(accountType="UNIFIED", coin=symbol[:-4])["result"]["list"][0]["coin"][0]["walletBalance"]
                symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
                return ToolResult(success=True, data=symbol_wallet_balance)

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
                return ToolResult(success=True, data=coin_info.model_dump())

            else:
                return ToolResult(success=False, error="Unknown operation")

        except Exception as e:
            logger.error(f"Trading tool error: {e}")
            return ToolResult(success=False, error=str(e))

    async def _make_request(self, method: str, endpoint: str, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}{endpoint}"
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
