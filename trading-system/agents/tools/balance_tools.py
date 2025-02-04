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
    - create_lot: Create new lot record
    - get_active_lots: Get active lots for symbol
    - delete_lot: Delete lot record
    - create_history_lot: Create history lot record
    - get_symbols_active_lots: Get all active lot symbols
    - get_count_lots: Get count of active lots
    - get_qty_symbol: Get quantity for symbol
    """
    name: str = "database"
    description: str = "Tool for database operations"
    args_schema: Type[BaseModel] = DatabaseOperationInput
    conn: Optional[psycopg2.extensions.connection] = Field(default=None, description="Database connection")
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
            if operation == "create_lot":
                return self._create_lot(**kwargs)
            elif operation == "get_active_lots":
                return self._get_active_lots(**kwargs)
            elif operation == "delete_lot":
                return self._delete_lot(**kwargs)
            elif operation == "create_history_lot":
                return self._create_history_lot(**kwargs)
            elif operation == "get_symbols_active_lots":
                return self._get_symbols_active_lots()
            elif operation == "get_count_lots":
                return self._get_count_lots()
            elif operation == "get_qty_symbol":
                return self._get_qty_symbol(**kwargs)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        except Exception as e:
            logger.error(f"Error in database operation: {e}")
            return {"status": "error", "message": str(e)}

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
    - get_price_limit: Get price limit from management service
    - get_fake_balance: Get fake balance from management service
    - get_num_available_lots: Get number of available lots from management service
    """
    args_schema: Type[BaseModel] = ManagementServiceInput
    host: str = Field(str, description="Management service host")
    port: str = Field(str, description="Management service port")
    base_url: str = Field(str, description="Management service base URL")
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
        self.base_url = f"{self.host}:{self.port}"

    def _run(self, operation: str, **kwargs: Any) -> Dict[str, Any]:
        """Run management service operation"""
        try:
            if operation == "get_system_status":
                return self._get_system_status()
            elif operation == "get_price_limit":
                return self._get_price_limit()
            elif operation == "get_fake_balance":
                return self._get_fake_balance()
            elif operation == "get_num_available_lots":
                return self._get_num_available_lots()
            else:
                raise ValueError(f"Unknown operation: {operation}")

        except Exception as e:
            logger.error(f"Error in management service operation: {e}")
            return {"status": "error", "message": str(e)}

    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status from management service"""
        try:
            response = requests.get(
                f"{self.base_url}/get_system_status",
                params={"api_key": self.token}
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()["system_status"]}
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"status": "error", "message": str(e)}

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

    def _get_fake_balance(self) -> Dict[str, Any]:
        """Get fake balance from management service"""
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