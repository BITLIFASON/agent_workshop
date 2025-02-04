from typing import Any, Type, Dict
from pybit.unified_trading import HTTP
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool
from loguru import logger
from ..utils.models import BybitOperationInput, CoinInfo, OrderResult


class BybitBalanceTool(BaseTool):
    """Tool for managing balance operations on Bybit"""
    name: str = "bybit_balance"
    description: str = """Manage balance operations on Bybit exchange.
    Supported operations:
    - get_balance: Get current balance for a symbol
    - get_positions: Get open positions
    - get_leverage: Get current leverage settings
    - set_leverage: Set leverage for a symbol
    - get_margin_mode: Get current margin mode
    - set_margin_mode: Set margin mode for a symbol
    """
    args_schema: Type[BaseModel] = BybitOperationInput
    client: Type[HTTP] | None = Field(default=None, description="Bybit HTTP client")
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

    def _run(self, operation: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute synchronous operations"""
        try:
            if operation == "get_wallet_balance":
                return self._get_wallet_balance()
            elif operation == "get_coin_balance":
                symbol = kwargs.get("symbol")
                return self._get_coin_balance(symbol)
            elif operation == "get_coin_info":
                symbol = kwargs.get("symbol")
                return self._get_coin_info(symbol)
            return {"success": False, "error": "Unknown operation"}

        except Exception as e:
            logger.error(f"Error in BybitBalanceTool: {e}")
            return f"Error executing operation: {str(e)}"

    def _get_wallet_balance(self) -> Dict[str, Any]:
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

    def _get_coin_balance(self, symbol: str) -> Dict[str, Any]:
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

    def _get_coin_info(self, symbol: str) -> Dict[str, Any]:
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

    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.client:
                self.client = None
            logger.info("BybitBalanceTool cleanup completed")
        except Exception as e:
            logger.error(f"Error during BybitBalanceTool cleanup: {e}")


class BybitTradingTool(BaseTool):
    """Tool for executing trades on Bybit"""
    name: str = "bybit_trading"
    description: str = """Execute trading operations on Bybit exchange.
    Supported operations:
    - execute_trade: Execute a trade with given parameters (symbol, side, qty)
    """
    args_schema: Type[BaseModel] = BybitOperationInput
    client: Type[HTTP] | None = Field(default=None, description="Bybit HTTP client")
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
        """Execute trading operations"""
        try:
            operation = kwargs.get("operation")

            if operation == "execute_trade":
                symbol = kwargs.get("symbol")
                side = kwargs.get("side")
                qty = kwargs.get("qty")
                
                # Проверяем наличие всех необходимых параметров
                if not symbol:
                    return {"success": False, "error": "Symbol is required"}
                if not side:
                    return {"success": False, "error": "Side is required"}
                if not qty:
                    return {"success": False, "error": "Quantity is required"}
                
                return self._place_order(symbol, side, qty)
            return {"success": False, "error": "Unknown operation"}

        except Exception as e:
            logger.error(f"Error in BybitTradingTool: {e}")
            return {"success": False, "error": str(e)}

    def _set_leverage(self, symbol: str) -> Dict[str, Any]:
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

    def _place_order(self, symbol: str, side: str, qty: float) -> Dict[str, Any]:
        """Place market order"""
        leverage_result = self._set_leverage(symbol)
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

    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.client:
                self.client = None
            logger.info("BybitTradingTool cleanup completed")
        except Exception as e:
            logger.error(f"Error during BybitTradingTool cleanup: {e}")