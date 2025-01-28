from typing import Any, Type, Optional, Dict, List
from pybit.unified_trading import HTTP
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool

class CoinInfo(BaseModel):
    """Model for coin information"""
    max_qty: float = Field(..., description="Maximum order quantity")
    min_qty: float = Field(..., description="Minimum order quantity")
    step_qty: str = Field(..., description="Step size for quantity")
    min_order_usdt: int = Field(..., description="Minimum order size in USDT")
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )

    @field_validator("max_qty", "min_qty")
    def validate_qty(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("min_order_usdt")
    def validate_min_order(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Minimum order size must be greater than 0")
        return v


class OrderResult(BaseModel):
    """Model for order execution results"""
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Order side (Buy/Sell)")
    qty: float = Field(..., description="Order quantity")
    price: float = Field(..., description="Order price")
    status: str = Field(..., description="Order status")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )

    @field_validator("symbol")
    def validate_symbol(cls, v: str) -> str:
        if not v.endswith("USDT"):
            raise ValueError("Symbol must end with USDT")
        if len(v) < 5:
            raise ValueError("Invalid symbol length")
        return v.upper()

    @field_validator("side")
    def validate_side(cls, v: str) -> str:
        if v.lower() not in ["buy", "sell"]:
            raise ValueError("Side must be either 'Buy' or 'Sell'")
        return v.capitalize()

    @field_validator("qty", "price")
    def validate_numbers(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Value must be greater than 0")
        return v


class TradingOperationInput(BaseModel):
    """Input schema for BybitTradingTool"""
    operation: str = Field(
        ..., 
        description="Operation to perform (get_wallet_balance, get_coin_balance, get_coin_info, place_order, get_market_price)"
    )
    symbol: Optional[str] = Field(None, description="Trading pair symbol (e.g., 'BTCUSDT')")
    side: Optional[str] = Field(None, description="Trading side ('Buy' or 'Sell')")
    qty: Optional[float] = Field(None, description="Order quantity")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )

    @field_validator("operation")
    def validate_operation(cls, v: str) -> str:
        valid_operations = [
            "get_wallet_balance",
            "get_coin_balance",
            "get_coin_info",
            "place_order",
            "get_market_price"
        ]
        if v not in valid_operations:
            raise ValueError(f"Invalid operation. Must be one of: {', '.join(valid_operations)}")
        return v

    @field_validator("symbol")
    def validate_symbol(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.endswith("USDT"):
                raise ValueError("Symbol must end with USDT")
            if len(v) < 5:
                raise ValueError("Invalid symbol length")
            return v.upper()
        return v

    @field_validator("side")
    def validate_side(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if v.lower() not in ["buy", "sell"]:
                raise ValueError("Side must be either 'Buy' or 'Sell'")
            return v.capitalize()
        return v

    @field_validator("qty")
    def validate_qty(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class BybitTradingTool(BaseTool):
    """Tool for executing trades on Bybit exchange"""
    name: str = "bybit_trading"
    description: str = "Tool for executing trades on Bybit"
    client: Type[HTTP] = Field(default=None, description="Bybit HTTP client")
    logger: SkipValidation[Any] = Field(default=None, description="Logger instance")
    api_key: str = Field(..., description="Bybit API key")
    api_secret: str = Field(..., description="Bybit API secret")
    demo_mode: bool = Field(default=True, description="Whether to use testnet")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        demo_mode: bool = True,
        **kwargs
    ):
        """Initialize BybitTradingTool"""
        super().__init__(**kwargs)
        self.api_key = api_key
        self.api_secret = api_secret
        self.demo_mode = demo_mode
        self.client = HTTP(
            testnet=demo_mode,
            api_key=api_key,
            api_secret=api_secret
        )
        self.logger = logger

    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute trading operations asynchronously"""
        try:
            operation = kwargs.get("operation")
            symbol = kwargs.get("symbol")
            side = kwargs.get("side")
            qty = kwargs.get("qty")

            if not symbol and operation not in ["get_wallet_balance"]:
                return {"success": False, "error": "Symbol is required for this operation"}

            if operation == "set_leverage":
                return await self._set_leverage(symbol)
            elif operation == "get_wallet_balance":
                return await self._get_wallet_balance()
            elif operation == "get_coin_balance":
                return await self._get_coin_balance(symbol)
            elif operation == "get_coin_info":
                return await self._get_coin_info(symbol)
            elif operation == "place_order":
                if not all([side, qty]):
                    return {"success": False, "error": "Side and quantity are required for placing orders"}
                return await self._place_order(symbol, side, qty)
            elif operation == "get_market_price":
                return await self._get_market_price(symbol)
            return {"success": False, "error": "Unknown operation"}

        except Exception as e:
            logger.error(f"Trading tool error: {e}")
            return {"success": False, "error": str(e)}

    async def _set_leverage(self, symbol: str) -> Dict[str, Any]:
        """Set leverage for symbol"""
        try:
            self.client.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=self.leverage,
                sellLeverage=self.leverage
            )
            logger.info(f"Leverage set to {self.leverage} for {symbol}")
            return {"success": True}
        except Exception as e:
            if '110043' in str(e):
                logger.info(f"Leverage already set to {self.leverage} for {symbol}")
                return {"success": True}
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    async def _get_wallet_balance(self) -> Dict[str, Any]:
        """Get wallet USDT balance"""
        try:
            balance_info = self.client.get_wallet_balance(
                accountType="UNIFIED",
                coin="USDT"
            )["result"]["list"][0]["coin"][0]["walletBalance"]
            balance_info = float(balance_info) if balance_info != '' else 0
            return {"success": True, "data": balance_info}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_coin_balance(self, symbol: str) -> Dict[str, Any]:
        """Get coin balance"""
        try:
            coin = symbol[:-4]  # Remove USDT suffix
            if coin not in [item['coin'] for item in self.client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
                return {"success": True, "data": 0}
            
            symbol_wallet_balance = self.client.get_wallet_balance(
                accountType="UNIFIED",
                coin=coin
            )["result"]["list"][0]["coin"][0]["walletBalance"]
            symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
            return {"success": True, "data": symbol_wallet_balance}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_coin_info(self, symbol: str) -> Dict[str, Any]:
        """Get coin trading information"""
        try:
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
            return {"success": True, "data": coin_info.model_dump()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _place_order(self, symbol: str, side: str, qty: float) -> Dict[str, Any]:
        """Place market order"""
        leverage_result = await self._set_leverage(symbol)
        if not leverage_result["success"]:
            return {"success": False, "error": f"Failed to set leverage: {leverage_result['error']}"}

        try:
            result = self.client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
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
            return {"success": True, "data": order_result.model_dump()}
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {"success": False, "error": str(e)}

    async def _get_market_price(self, symbol: str) -> Dict[str, Any]:
        """Get current market price"""
        try:
            ticker = self.client.get_tickers(
                category="linear",
                symbol=symbol
            )["result"]["list"][0]
            return {"success": True, "data": float(ticker["lastPrice"])}
        except Exception as e:
            return {"success": False, "error": str(e)}
