from typing import Dict, Any, Optional, Type, List, Union, Annotated
import asyncpg
from pybit.unified_trading import HTTP
import aiohttp
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool
import logging
from ..utils.models import DatabaseOperationInput, ManagementServiceInput

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
