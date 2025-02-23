from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class SignalParserInput(BaseModel):
    """Input schema for SignalParserTool"""
    text_message: str = Field(default='', description="Message text to parse for trading signals")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class ManagementServiceInput(BaseModel):
    """Input schema for ManagementServiceTool"""
    operation: str = Field(
        default='',
        description="Operation to perform (get_system_status, get_balance, get_max_num_available_lots)"
    )

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class ReadDatabaseOperationInput(BaseModel):
    """Input schema for ReadDatabaseTool"""
    operation: str = Field(
        default='',
        description="Operation to perform (get_symbols_active_lots, get_count_active_lots, get_qty_symbol_active_lot)"
    )
    symbol: Optional[str] = Field('', description="Trading pair symbol")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class WriteDatabaseOperationInput(BaseModel):
    """Input schema for WriteDatabaseTool"""
    operation: str = Field(
        default='',
        description="Operation to perform (create_lot, delete_lot, create_history_lot, skip_write_db_operation)"
    )
    side: Optional[str] = Field('', description="Side type [Buy, Sell] (for history lots)")
    symbol: Optional[str] = Field('', description="Trading pair symbol")
    qty: Optional[float] = Field(0., description="Order quantity")
    price: Optional[float] = Field(0., description="Order price")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class BybitBalanceInput(BaseModel):
    """Input model for Bybit balance operations"""
    operation: str = Field(default='', description="Operation to perform (get_coin_info, skip_balance_operation)")
    symbol: Optional[str] = Field(default='', description="Trading pair symbol")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class BybitExecutorInput(BaseModel):
    """Input model for Bybit operations"""
    operation: str = Field(default='', description="Operation to perform (execute_trade, skip_trade_operation)")
    symbol: Optional[str] = Field(default='', description="Trading pair symbol")
    side: Optional[str] = Field(default='', description="Order side [Buy, Sell]")
    qty: Optional[float] = Field(default=0., description="Order quantity")
    price: Optional[float] = Field(default=0., description="Order coin price")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class SignalData(BaseModel):
    """Model for parsed trading signals"""
    symbol: str = Field(default='', description="Trading pair symbol (e.g., 'MINAUSDT')")
    side: str = Field(default='', description="Trading side [Buy, Sell]")
    price: float = Field(default=0., description="Entry or exit price for the trade")
    profit_percentage: Optional[float] = Field(0., description="Profit percentage for sell signals")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class CoinInfo(BaseModel):
    """Model for coin trading information"""
    maxOrderQty: str = Field(default='1', description="Maximum order coin quantity")
    minOrderQty: str = Field(default='1', description="Minimum order coin quantity")
    qtyStep: str = Field(default='1', description="Accuracy of quantity coin")
    minNotionalValue: str = Field(default='5', description="Minimum order size in USDT")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class OrderResult(BaseModel):
    """Model for order execution result"""
    retCode: int = Field(default=0, description="Return code")
    retMsg: str = Field(default='', description="Return message")
    orderId: str = Field(default='', description="Order ID")
    orderLinkId: str = Field(default='', description="User customised order ID")
    retExtInfo: Dict = Field(default={}, description="Return extended information")
    time: int = Field(default=0, description="Time")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class TelegramConfig(BaseModel):
    """Model for Telegram configuration"""
    api_id: int = Field(default=0, description="Telegram API ID")
    api_hash: str = Field(default='', description="Telegram API hash")
    session_token: str = Field(default='', description="Telegram session token")
    channel_url: str = Field(default='', description="Telegram channel URL")
    max_retries: int = Field(default=3, description="Maximum number of retries")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class BybitConfig(BaseModel):
    """Model for Bybit configuration"""
    api_key: str = Field(default='', description="Bybit API key")
    api_secret: str = Field(default='', description="Bybit API secret")
    demo_mode: bool = Field(default=True, description="Whether to use demo mode")
    leverage: str = Field(default='1', description="Leverage order value in string format")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class DatabaseConfig(BaseModel):
    """Model for database configuration"""
    host: str = Field(default='', description="Database host")
    port: str = Field(default='', description="Database port")
    user: str = Field(default='', description="Database user")
    password: str = Field(default='', description="Database password")
    database: str = Field(default='', description="Database name")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class ManagementAPIConfig(BaseModel):
    """Model for management API configuration"""
    host: str = Field(default='', description="Management API host")
    port: str = Field(default='', description="Management API port")
    token: str = Field(default='', description="Management API token")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class LLMConfig(BaseModel):
    """Model for LLM configuration"""
    provider: str = Field(default='', description="LLM provider name")
    model: str = Field(default='', description="LLM model name")
    api_key: str = Field(default='', description="LLM API key")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )