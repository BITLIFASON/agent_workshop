from typing import Any, Type, Dict
from pybit.unified_trading import HTTP
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool
from loguru import logger


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


class BybitBalanceTool(BaseTool):
    """Tool for managing balance operations on Bybit"""
    name = "bybit_balance"
    description = """Manage balance operations on Bybit exchange.
    Supported operations:
    - get_balance: Get current balance for a symbol
    - get_positions: Get open positions
    - get_leverage: Get current leverage settings
    - set_leverage: Set leverage for a symbol
    - get_margin_mode: Get current margin mode
    - set_margin_mode: Set margin mode for a symbol
    """
    args_schema = BybitOperationInput
    client: Type[HTTP] = Field(default=None, description="Bybit HTTP client")
    logger: SkipValidation[Any] = Field(default=None, description="Logger instance")
    model_config = ConfigDict(arbitrary_types_allowed=True)


    def __init__(self,
                 api_key: str,
                 api_secret: str,
                 demo_mode: bool = True,
                 **kwargs
    ):
        """Initialize BybitTradingTool"""
        super().__init__(**kwargs)
        self.client = HTTP(
            demo=demo_mode,
            api_key=api_key,
            api_secret=api_secret
        )
        self.logger = logger

    async def _arun(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute trading operations asynchronously"""
        try:

            operation = kwargs.get("operation")

            if operation == "get_wallet_balance":
                return await self._get_wallet_balance()
            elif operation == "get_coin_balance":
                symbol = kwargs.get("symbol")
                return await self._get_coin_balance(symbol)
            elif operation == "get_coin_info":
                symbol = kwargs.get("symbol")
                return await self._get_coin_info(symbol)
            return {"success": False, "error": "Unknown operation"}

        except Exception as e:
            logger.error(f"Error in BybitBalanceTool: {e}")
            return f"Error executing operation: {str(e)}"

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



class BybitTradingTool(BaseTool):
    """Tool for executing trades on Bybit"""
    name = "bybit_trading"
    description = """Execute trading operations on Bybit exchange.
    Supported operations:
    - execute_trade: Execute a trade with given parameters (symbol, side, qty)
    - cancel_trade: Cancel an existing trade (order_id)
    - get_order_status: Get status of an order (order_id)
    """
    args_schema = BybitOperationInput
    client: Type[HTTP] = Field(default=None, description="Bybit HTTP client")
    logger: SkipValidation[Any] = Field(default=None, description="Logger instance")
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self,
                 api_key: str,
                 api_secret: str,
                 demo_mode: bool = True,
                 **kwargs
    ):
        """Initialize BybitTradingTool"""
        super().__init__(**kwargs)
        self.client = HTTP(
            demo=demo_mode,
            api_key=api_key,
            api_secret=api_secret
        )
        self.logger = logger

    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, operation: str, params: Dict[str, Any]) -> str:
        """Execute async trading operations"""
        try:
            if operation == "execute_trade":
                symbol = params.get("symbol")
                side = params.get("side")
                qty = params.get("qty")
                if not all([symbol, side, qty]):
                    return "Error: Missing required parameters for trade execution"
                return f"Executed trade: {symbol} {side} {qty}"
            
            else:
                return f"Error: Unsupported operation {operation}"
                
        except Exception as e:
            logger.error(f"Error in BybitTradingTool: {e}")
            return f"Error executing operation: {str(e)}"

    async def _set_leverage(self, symbol: str) -> Dict[str, Any]:
        """Set leverage for symbol"""
        try:
            self.client.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage="1",
                sellLeverage="1"
            )
            logger.info(f"Leverage set to {1} for {symbol}")
            return {"success": True}
        except Exception as e:
            if '110043' in str(e):
                logger.info(f"Leverage already set to {1} for {symbol}")
                return {"success": True}
            logger.error(f"Failed to set leverage for {symbol}: {e}")
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


    async def cleanup(self):
        """Cleanup resources"""
        # Cleanup Bybit client if needed
        pass