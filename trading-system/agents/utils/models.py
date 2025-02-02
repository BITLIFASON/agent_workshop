from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class SignalParserInput(BaseModel):
    """Input schema for SignalParserTool"""
    message: str = Field(str, description="Message text to parse for trading signals")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )

class SourceSignalInput(BaseModel):
    """Input schema for SourceSignalInput"""
    message: str = Field(str, description="Source message text from Telegram channel")

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
    action: Optional[str] = Field(None, description="Action type (for history lots)")

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
    """Base input model for Bybit operations"""
    operation: str = Field(default="", description="Operation to perform")
    params: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")


class BybitOperationParams(BaseModel):
    """Base model for Bybit operation parameters"""
    symbol: Optional[str] = Field(None, description="Trading pair symbol")


class BybitTradingInput(BaseModel):
    """Input schema for BybitTradingTool"""
    operation: str = Field(str, description="Operation to perform")
    params: BybitOperationParams = Field(default_factory=BybitOperationParams)


class SignalData(BaseModel):
    """Model for parsed trading signals"""
    symbol: str = Field(str, description="Trading pair symbol (e.g., 'MINAUSDT')")
    action: str = Field(str, description="Trading action ('buy' or 'sell')")
    price: float = Field(float, description="Entry or exit price for the trade")
    profit_percentage: Optional[float] = Field(None, description="Profit percentage for sell signals")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class CoinInfo(BaseModel):
    """Model for coin information"""
    max_qty: float = Field(float, description="Maximum order quantity")
    min_qty: float = Field(float, description="Minimum order quantity")
    step_qty: str = Field(str, description="Step size for quantity")
    min_order_usdt: int = Field(int, description="Minimum order size in USDT")
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class OrderResult(BaseModel):
    """Model for order execution results"""
    order_id: str = Field(str, description="Order ID")
    symbol: str = Field(str, description="Trading pair symbol")
    side: str = Field(str, description="Order side (Buy/Sell)")
    qty: float = Field(float, description="Order quantity")
    price: float = Field(float, description="Order price")
    status: str = Field(str, description="Order status")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class TelegramConfig(BaseModel):
    """Telegram configuration model"""
    api_id: int = Field(int, description="Telegram API ID")
    api_hash: str = Field(str, description="Telegram API hash")
    session_token: str = Field(str, description="Telegram session token")
    channel_url: str = Field(str, description="Telegram channel URL")
    max_retries: int = Field(int, description="Maximum number of reconnection attempts")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class BybitConfig(BaseModel):
    """Bybit configuration model"""
    api_key: str = Field(str, description="Bybit API key")
    api_secret: str = Field(str, description="Bybit API secret")
    demo_mode: bool = Field(default=True, description="Whether to use testnet")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class DatabaseConfig(BaseModel):
    """Database configuration model"""
    host: str = Field(str, description="Database host")
    port: str = Field(str, description="Database port")
    user: str = Field(str, description="Database user")
    password: str = Field(str, description="Database password")
    database: str = Field(str, description="Database name")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class ManagementAPIConfig(BaseModel):
    """Management API configuration model"""
    host: str = Field(str, description="Management API host")
    port: str = Field(str, description="Management API port")
    token: str = Field(str, description="Management API token")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class LLMConfig(BaseModel):
    """LLM configuration model"""
    provider: str = Field(str, description="LLM provider name")
    model: str = Field(str, description="LLM model name")
    api_key: Optional[str] = Field(None, description="LLM API key")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )