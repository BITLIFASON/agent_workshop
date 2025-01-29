from pydantic import BaseModel, Field, ConfigDict, Dict, Any
from typing import Optional
from datetime import datetime


class SignalParserInput(BaseModel):
    """Input schema for SignalParserTool"""
    message: str = Field(str, description="Message text to parse for trading signals")

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


class BybitOperationInput(BaseModel):
    """Base input model for Bybit operations"""
    operation: str = Field(default="", description="Operation to perform")
    params: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")