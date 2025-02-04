from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class SignalParserInput(BaseModel):
    """Input schema for SignalParserTool"""
    message: str = Field(description="Message text to parse for trading signals")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class DatabaseOperationInput(BaseModel):
    """Input schema for DatabaseTool"""
    operation: str = Field(
        str,
        description="Operation to perform (get_active_lots, create_lot, delete_lot, create_history_lot)"
    )
    symbol: Optional[str] = Field(None, description="Trading pair symbol")
    qty: Optional[float] = Field(None, description="Order quantity")
    price: Optional[float] = Field(None, description="Order price")
    action: Optional[str] = Field(None, description="Action type [Buy, Sell] (for history lots)")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


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


class BybitOperationInput(BaseModel):
    """Input model for Bybit operations"""
    operation: str = Field(default='', description="Operation to perform")
    params: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")


class SignalData(BaseModel):
    """Model for parsed trading signals"""
    symbol: str = Field(description="Trading pair symbol (e.g., 'MINAUSDT')")
    action: str = Field(description="Trading action [Buy, Sell]")
    price: float = Field(description="Entry or exit price for the trade")
    profit_percentage: Optional[float] = Field(None, description="Profit percentage for sell signals")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class CoinInfo(BaseModel):
    """Model for coin trading information"""
    max_qty: float = Field(description="Maximum order quantity")
    min_qty: float = Field(description="Minimum order quantity")
    step_qty: str = Field(default='', description="Step size for quantity")
    min_order_usdt: int = Field(description="Minimum order size in USDT")
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class OrderResult(BaseModel):
    """Model for order execution result"""
    order_id: str = Field(default='', description="Order ID")
    symbol: str = Field(default='', description="Trading pair symbol")
    side: str = Field(default='', description="Order side (Buy/Sell)")
    qty: float = Field(description="Order quantity")
    price: float = Field(description="Order price")
    status: str = Field(default='', description="Order status")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class TelegramConfig(BaseModel):
    """Model for Telegram configuration"""
    api_id: int = Field(description="Telegram API ID")
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
    leverage: int = Field(default=1, description="Default leverage")

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