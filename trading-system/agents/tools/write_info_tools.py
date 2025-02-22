from typing import Dict, Any, Optional, Type, List, Union, Annotated, ContextManager
from contextlib import contextmanager
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool
import logging
from ..utils.models import WriteDatabaseOperationInput
import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class WriteDatabaseTool(BaseTool):
    """Tool for database operations."""
    name: str = "database"
    description: str = """Tool for database operations.
    Supported operations:
    - create_lot: Create new lot record with given parameters (symbol, qty, price)
    - delete_lot: Delete lot record with given parameters (symbol)
    - create_history_lot: Create history lot record with given parameters (side, symbol, qty, price)
    - skip_write_db_operation: Skip write db operation
    """
    args_schema: Type[BaseModel] = WriteDatabaseOperationInput
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
                side = kwargs.get('side')
                symbol = kwargs.get('symbol')
                qty = kwargs.get('qty')
                price = kwargs.get('price')
                result = self._create_history_lot(side, symbol, qty, price)
            elif operation == "skip_write_db_operation":
                result = {"status": "success operation", "message": "skip write db operation"}
            else:
                result = {"status": "error operation", "message": f"Unknown operation: {operation}"}

            logger.info(f"[DatabaseTool] Operation result: {result}")
            # Format result for CrewAI
            if isinstance(result, dict):
                if result.get("status") == "error operation":
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
                    return {"status": "success operation"}
        except Exception as e:
            logger.error(f"Error creating lot: {e}")
            return {"status": "error operation", "message": str(e)}

    def _create_history_lot(self, side: str, symbol: str, qty: float, price: float) -> Dict[str, Any]:
        """Create history lot record"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO history_lots (side, symbol, qty, price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (side, symbol, qty, price)
                    )
                    return {"status": "success operation"}
        except Exception as e:
            logger.error(f"Error creating history lot: {e}")
            return {"status": "error operation", "message": str(e)}

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
                    return {"status": "success operation"}
        except Exception as e:
            logger.error(f"Error deleting lot: {e}")
            return {"status": "error operation", "message": str(e)}

    def cleanup(self):
        """Cleanup resources"""
        if self.conn:
            self.conn.close()
            self.conn = None