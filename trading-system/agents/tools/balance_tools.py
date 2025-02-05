from typing import Dict, Any, Optional, Type, List, Union, Annotated, ContextManager
from contextlib import contextmanager
from pybit.unified_trading import HTTP
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool
import logging
from ..utils.models import DatabaseOperationInput, ManagementServiceInput
import requests
import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DatabaseTool(BaseTool):
    """Tool for database operations.
    
    This tool provides functionality to interact with the database,
    including managing lots, historical data, and other trading records.
    
    Supported operations:
    - create_lot: Create new lot record with given parameters (symbol, qty, price)
    - delete_lot: Delete lot record with given parameters (symbol)
    - create_history_lot: Create history lot record with given parameters (action, symbol, qty, price)
    - get_symbols_active_lots: Get all active lot symbols
    - get_count_lots: Get count of active lots
    - get_qty_symbol: Get quantity for symbol with given parameters (symbol)
    """
    name: str = "database"
    description: str = "Tool for database operations"
    args_schema: Type[BaseModel] = DatabaseOperationInput
    conn: Optional[psycopg2.extensions.connection] = Field(default=None, description="Database connection")
    host: str = Field(default='', description="Database host")
    port: str = Field(default='', description="Database port")
    user: str = Field(default='', description="Database user")
    password: str = Field(default='', description="Database password")
    database: str = Field(default='', description="Database name")

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
        self.conn = None
        self._initialize_tables()

    @contextmanager
    def get_connection(self) -> ContextManager[psycopg2.extensions.connection]:
        """Get database connection using context manager"""
        if not self.conn:
            try:
                self.conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
            except Exception as e:
                logger.error(f"Error connecting to PostgreSQL: {e}")
                raise
        try:
            yield self.conn
        except Exception as e:
            logger.error(f"Error in database operation: {e}")
            raise
        finally:
            if self.conn:
                self.conn.commit()

    def _initialize_tables(self):
        """Initialize required database tables"""
        self._initialize_active_lots_table()
        self._initialize_history_lots_table()

    def _initialize_active_lots_table(self):
        """Initialize active_lots table"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS active_lots (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(50) NOT NULL,
            qty NUMERIC(20, 8) NOT NULL,
            price NUMERIC(20, 8) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_query)

    def _initialize_history_lots_table(self):
        """Initialize history_lots table"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS history_lots (
            id SERIAL PRIMARY KEY,
            action VARCHAR(50) NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            qty NUMERIC(20, 8) NOT NULL,
            price NUMERIC(20, 8) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_query)

    def _run(self, operation: str, **kwargs: Any) -> Dict[str, Any]:
        """Run database operation"""
        try:
            logger.info(f"[DatabaseTool] Executing operation: {operation}")
            logger.info(f"[DatabaseTool] Arguments: {kwargs}")

            result = None
            if operation == "create_lot":
                symbol = kwargs.get('symbol')
                qty = kwargs.get('qty')
                price = kwargs.get('price')
                result = self._create_lot(symbol, qty, price)
            elif operation == "delete_lot":
                symbol = kwargs.get('symbol')
                result = self._delete_lot(symbol)
            elif operation == "create_history_lot":
                action = kwargs.get('action')
                symbol = kwargs.get('symbol')
                qty = kwargs.get('qty')
                price = kwargs.get('price')
                result = self._create_history_lot(action, symbol, qty, price)
            elif operation == "get_symbols_active_lots":
                result = self._get_symbols_active_lots()
            elif operation == "get_count_lots":
                result = self._get_count_lots()
            elif operation == "get_qty_symbol":
                symbol = kwargs.get('symbol')
                result = self._get_qty_symbol(symbol)
            else:
                result = {"status": "error", "message": f"Unknown operation: {operation}"}

            logger.info(f"[DatabaseTool] Operation result: {result}")
            # Форматируем результат для CrewAI
            if isinstance(result, dict):
                if result.get("status") == "error":
                    return {"result": str(result.get("message", "Unknown error"))}
                return {"result": str(result.get("data", result))}
            return {"result": str(result)}

        except Exception as e:
            error_msg = f"Error in database operation: {e}"
            logger.error(f"[DatabaseTool] {error_msg}")
            return {"result": error_msg}

    def _create_lot(self, symbol: str, qty: float, price: float) -> Dict[str, Any]:
        """Create new lot record"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO active_lots (symbol, qty, price)
                        VALUES (%s, %s, %s)
                        """,
                        (symbol, qty, price)
                    )
                    return {"status": "success"}
        except Exception as e:
            logger.error(f"Error creating lot: {e}")
            return {"status": "error", "message": str(e)}

    def _get_active_lots(self, symbol: str) -> Dict[str, Any]:
        """Get active lots for symbol"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM active_lots
                        WHERE symbol = %s
                        ORDER BY created_at ASC
                        """,
                        (symbol,)
                    )
                    lots = cur.fetchall()
                    return {"status": "success", "data": lots}
        except Exception as e:
            logger.error(f"Error getting active lots: {e}")
            return {"status": "error", "message": str(e)}

    def _delete_lot(self, symbol: str) -> Dict[str, Any]:
        """Delete lot record"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM active_lots
                        WHERE symbol = %s
                        """,
                        (symbol,)
                    )
                    return {"status": "success"}
        except Exception as e:
            logger.error(f"Error deleting lot: {e}")
            return {"status": "error", "message": str(e)}

    def _create_history_lot(self, action: str, symbol: str, qty: float, price: float) -> Dict[str, Any]:
        """Create history lot record"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO history_lots (action, symbol, qty, price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (action, symbol, qty, price)
                    )
                    return {"status": "success"}
        except Exception as e:
            logger.error(f"Error creating history lot: {e}")
            return {"status": "error", "message": str(e)}

    def _get_symbols_active_lots(self) -> Dict[str, Any]:
        """Get all active lot symbols"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT symbol FROM active_lots")
                    symbols = [row[0] for row in cur.fetchall()]
                    return {"status": "success", "data": symbols}
        except Exception as e:
            logger.error(f"Error getting active lot symbols: {e}")
            return {"status": "error", "message": str(e)}

    def _get_count_lots(self) -> Dict[str, Any]:
        """Get count of active lots"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(id) FROM active_lots")
                    count = cur.fetchone()[0]
                    return {"status": "success", "data": count}
        except Exception as e:
            logger.error(f"Error getting lot count: {e}")
            return {"status": "error", "message": str(e)}

    def _get_qty_symbol(self, symbol: str) -> Dict[str, Any]:
        """Get quantity for symbol"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT qty FROM active_lots WHERE symbol = %s",
                        (symbol,)
                    )
                    result = cur.fetchone()
                    if result:
                        return {"status": "success", "data": result[0]}
                    return {"status": "error", "message": "Symbol not found"}
        except Exception as e:
            logger.error(f"Error getting symbol quantity: {e}")
            return {"status": "error", "message": str(e)}

    def cleanup(self):
        """Cleanup resources"""
        if self.conn:
            self.conn.close()
            self.conn = None


class ManagementServiceTool(BaseTool):
    """Tool for management service operations"""
    name: str = "management"
    description: str = """Tool for management service operations.
    Supported operations:
    - get_system_status: Get system status from management service
    - get_price_limit: Get price limit for coin from management service
    - get_balance: Get available balance account from management service
    - get_num_available_lots: Get number of available lots from management service
    """
    args_schema: Type[BaseModel] = ManagementServiceInput
    host: str = Field(default='', description="Management service host")
    port: str = Field(default='', description="Management service port")
    base_url: str = Field(default='', description="Management service base URL")
    token: str = Field(default='', description="Management service token")

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
        self.base_url = f"{self.host}:{self.port}"

    def _run(self, operation: str, **kwargs: Any) -> Dict[str, Any]:
        """Run management service operation"""
        try:
            logger.info(f"[ManagementServiceTool] Executing operation: {operation}")
            logger.info(f"[ManagementServiceTool] Arguments: {kwargs}")

            result = None
            if operation == "get_system_status":
                result = self._get_system_status()
            elif operation == "get_price_limit":
                result = self._get_price_limit()
            elif operation == "get_balance":
                result = self._get_balance()
            elif operation == "get_num_available_lots":
                result = self._get_num_available_lots()
            else:
                result = {"status": "error", "message": f"Unknown operation: {operation}"}

            logger.info(f"[ManagementServiceTool] Operation result: {result}")
            # Форматируем результат для CrewAI
            if isinstance(result, dict):
                if result.get("status") == "error":
                    return {"result": str(result.get("message", "Unknown error"))}
                return {"result": str(result.get("data", result))}
            return {"result": str(result)}

        except Exception as e:
            error_msg = f"Error in management service operation: {e}"
            logger.error(f"[ManagementServiceTool] {error_msg}")
            return {"result": error_msg}

    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status from management service"""
        try:
            logger.info("[ManagementServiceTool] Getting system status")
            response = requests.get(
                f"{self.base_url}/get_system_status",
                params={"api_key": self.token}
            )
            response.raise_for_status()
            result = {"status": "success", "data": "system is " + response.json()["system_status"]}
            logger.info(f"[ManagementServiceTool] System status: {result}")
            return result
        except Exception as e:
            error_msg = f"Error getting system status: {e}"
            logger.error(f"[ManagementServiceTool] {error_msg}")
            return {"status": "error", "message": error_msg}

    def _get_price_limit(self) -> Dict[str, Any]:
        """Get price limit from management service"""
        try:
            response = requests.get(
                f"{self.base_url}/get_price_limit",
                params={"api_key": self.token}
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()["price_limit"]}
        except Exception as e:
            logger.error(f"Error getting price limit: {e}")
            return {"status": "error", "message": str(e)}

    def _get_balance(self) -> Dict[str, Any]:
        """Get balance from management service"""
        try:
            response = requests.get(
                f"{self.base_url}/get_fake_balance",
                params={"api_key": self.token}
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()["fake_balance"]}
        except Exception as e:
            logger.error(f"Error getting fake balance: {e}")
            return {"status": "error", "message": str(e)}

    def _get_num_available_lots(self) -> Dict[str, Any]:
        """Get number of available lots from management service"""
        try:
            response = requests.get(
                f"{self.base_url}/get_num_available_lots",
                params={"api_key": self.token}
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()["num_available_lots"]}
        except Exception as e:
            logger.error(f"Error getting number of available lots: {e}")
            return {"status": "error", "message": str(e)}

    def cleanup(self):
        """Cleanup resources"""
        pass