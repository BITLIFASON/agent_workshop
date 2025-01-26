from typing import Any, Type, Optional, Dict, List
from pybit.unified_trading import HTTP
from .base_tools import ToolResult
import logging
from pydantic import BaseModel, Field, validator
from crewai.tools import BaseTool

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CoinInfo(BaseModel):
    """Model for coin information"""
    max_qty: float = Field(..., description="Maximum order quantity")
    min_qty: float = Field(..., description="Minimum order quantity")
    step_qty: str = Field(..., description="Step size for quantity")
    min_order_usdt: int = Field(..., description="Minimum order size in USDT")
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class FixedTradingOperationSchema(BaseModel):
    """Fixed input schema for BybitTradingTool with predefined symbol"""
    operation: str = Field(..., description="Operation to perform (get_wallet_balance, get_coin_balance, get_coin_info, etc)")
    side: Optional[str] = Field(None, description="Trading side ('buy' or 'sell')")
    qty: Optional[float] = Field(None, description="Order quantity")


class TradingOperationSchema(FixedTradingOperationSchema):
    """Input schema for BybitTradingTool"""
    symbol: Optional[str] = Field(None, description="Trading pair symbol (e.g., 'BTCUSDT')")

    @validator("symbol")
    def validate_symbol(cls, v):
        if v is not None and not v.endswith("USDT"):
            raise ValueError("Symbol must end with USDT")
        return v

    @validator("side")
    def validate_side(cls, v):
        if v is not None and v.lower() not in ["buy", "sell"]:
            raise ValueError("Side must be either 'buy' or 'sell'")
        return v

    @validator("qty")
    def validate_qty(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class OrderResult(BaseModel):
    """Model for order execution result"""
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Trading side")
    qty: float = Field(..., description="Order quantity")
    price: float = Field(..., description="Order price")
    status: str = Field(..., description="Order status")


class BybitTradingTool(BaseTool):
    """Tool for executing trades on Bybit exchange"""
    name: str = "bybit_trading"
    description: str = "Tool for executing trades on Bybit"
    args_schema: Type[BaseModel] = TradingOperationSchema
    client: Optional[HTTP] = None
    leverage: str = "1"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        demo_mode: bool = True,
        leverage: str = "1",
        symbol: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.client = HTTP(
            testnet=demo_mode,
            api_key=api_key,
            api_secret=api_secret
        )
        self.leverage = leverage

        if symbol is not None:
            self.symbol = symbol
            self.description = f"Tool for executing trades on Bybit for {symbol}"
            self.args_schema = FixedTradingOperationSchema

        self._generate_description()

    def _run(self, **kwargs: Any) -> Any:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, **kwargs: Any) -> Any:
        """Execute trading operations asynchronously"""
        operation = kwargs.get("operation")
        symbol = kwargs.get("symbol", getattr(self, "symbol", None))
        side = kwargs.get("side")
        qty = kwargs.get("qty")

        try:
            if operation == "set_leverage":
                return await self._set_leverage(symbol)
            elif operation == "get_wallet_balance":
                return await self._get_wallet_balance()
            elif operation == "get_coin_balance":
                return await self._get_coin_balance(symbol)
            elif operation == "get_coin_info":
                return await self._get_coin_info(symbol)
            elif operation == "place_order":
                return await self._place_order(symbol, side, qty)
            elif operation == "get_market_price":
                return await self._get_market_price(symbol)
            return ToolResult(success=False, error="Unknown operation")
        except Exception as e:
            logger.error(f"Trading tool error: {e}")
            return ToolResult(success=False, error=str(e))

    async def _set_leverage(self, symbol: str) -> ToolResult:
        try:
            self.client.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=self.leverage,
                sellLeverage=self.leverage
            )
            logger.info(f"Leverage set to {self.leverage} for {symbol}")
            return ToolResult(success=True)
        except Exception as e:
            if '110043' in str(e):
                logger.info(f"Leverage already set to {self.leverage} for {symbol}")
                return ToolResult(success=True)
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return ToolResult(success=False, error=str(e))

    async def _get_wallet_balance(self) -> ToolResult:
        balance_info = self.client.get_wallet_balance(
            accountType="UNIFIED",
            coin="USDT"
        )["result"]["list"][0]["coin"][0]["walletBalance"]
        balance_info = float(balance_info) if balance_info != '' else 0
        return ToolResult(success=True, data=balance_info)

    async def _get_coin_balance(self, symbol: str) -> ToolResult:
        if symbol[:-4] not in [item['coin'] for item in self.client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
            return ToolResult(success=True, data=0)
        symbol_wallet_balance = self.client.get_wallet_balance(
            accountType="UNIFIED",
            coin=symbol[:-4]
        )["result"]["list"][0]["coin"][0]["walletBalance"]
        symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
        return ToolResult(success=True, data=symbol_wallet_balance)

    async def _get_coin_info(self, symbol: str) -> ToolResult:
        symbol_qty_info = self.client.get_instruments_info(
            category="linear",
            symbol=symbol
        )["result"]["list"][0]["lotSizeFilter"]
        coin_info = CoinInfo(
            max_qty=float(symbol_qty_info.get("maxMktOrderQty")),
            min_qty=float(symbol_qty_info.get("minOrderQty")),
            step_qty=symbol_qty_info.get("qtyStep"),
            min_order_usdt=int(symbol_qty_info.get("minNotionalValue"))
        )
        return ToolResult(success=True, data=coin_info.model_dump())

    async def _place_order(self, symbol: str, side: str, qty: float) -> ToolResult:
        leverage_result = await self._set_leverage(symbol)
        if not leverage_result.success:
            return ToolResult(success=False, error=f"Failed to set leverage: {leverage_result.error}")

        try:
            result = self.client.place_order(
                category="linear",
                symbol=symbol,
                side=side.capitalize() if side else "Buy",
                orderType="Market",
                qty=qty
            )
            order_result = OrderResult(
                order_id=result["result"]["orderId"],
                symbol=result["result"]["symbol"],
                side=result["result"]["side"],
                qty=float(result["result"]["qty"]),
                price=float(result["result"]["price"]),
                status=result["result"]["orderStatus"]
            )
            logger.info(f"Order placed successfully: {order_result}")
            return ToolResult(success=True, data=order_result.model_dump())
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return ToolResult(success=False, error=str(e))

    async def _get_market_price(self, symbol: str) -> ToolResult:
        ticker = self.client.get_tickers(
            category="linear",
            symbol=symbol
        )["result"]["list"][0]
        return ToolResult(success=True, data=float(ticker["lastPrice"]))


class OrderValidatorSchema(BaseModel):
    """Input schema for OrderValidatorTool"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTCUSDT')")
    side: str = Field(..., description="Trading side ('buy' or 'sell')")
    qty: float = Field(..., description="Order quantity")

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v.endswith("USDT"):
            raise ValueError("Symbol must end with USDT")
        return v

    @validator("side")
    def validate_side(cls, v):
        if v.lower() not in ["buy", "sell"]:
            raise ValueError("Side must be either 'buy' or 'sell'")
        return v

    @validator("qty")
    def validate_qty(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class OrderValidatorTool(BaseTool):
    """Tool for validating trade orders"""
    name: str = "order_validator"
    description: str = "Tool for validating trade orders"
    args_schema: Type[BaseModel] = OrderValidatorSchema

    def _run(self, **kwargs: Any) -> Any:
        try:
            # Validation is handled by the schema
            return ToolResult(success=True, data=kwargs)
        except Exception as e:
            logger.error(f"Order validation error: {e}")
            return ToolResult(success=False, error=str(e))

    async def _arun(self, **kwargs: Any) -> Any:
        """Async version of _run"""
        return self._run(**kwargs)
