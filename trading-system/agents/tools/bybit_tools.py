from typing import Any, Type, Dict
from pybit.unified_trading import HTTP
from pydantic import BaseModel, Field, ConfigDict, field_validator, SkipValidation
from crewai.tools import BaseTool
from loguru import logger
from ..utils.models import BybitBalanceInput, BybitExecutorInput, CoinInfo, OrderResult


class BybitBalanceTool(BaseTool):
    """Tool for managing balance operations on Bybit"""
    name: str = "bybit_balance"
    description: str = """Manage balance operations on Bybit exchange.
    Supported operations:
    - get_coin_balance: Get coin balance, need symbol (e.g. MINAUSDT)
    - get_coin_info: Get coin trading information, need symbol (e.g. MINAUSDT)
    """
    args_schema: Type[BaseModel] = BybitBalanceInput
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

    def _run(self, operation:str, **kwargs) -> Dict[str, Any]:
        """Execute synchronous operations"""
        try:
            logger.info(f"[BybitBalanceTool] Executing operation: {operation}")
            logger.info(f"[BybitBalanceTool] Arguments: {kwargs}")

            result = None
            if operation == "get_coin_balance":
                symbol = kwargs.get("symbol")
                result = self._get_coin_balance(symbol)
            elif operation == "get_coin_info":
                symbol = kwargs.get("symbol")
                result = self._get_coin_info(symbol)
            else:
                result = {"success": False, "error": "Unknown operation"}

            logger.info(f"[BybitBalanceTool] Operation result: {result}")
            # Форматируем результат для CrewAI
            if isinstance(result, dict):
                if result.get("success") is False:
                    return {"result": str(result.get("error", "Unknown error"))}
                return {"result": str(result.get("data", result))}
            return {"result": str(result)}

        except Exception as e:
            error_msg = f"Error in BybitBalanceTool: {e}"
            logger.error(error_msg)
            return {"result": error_msg}

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
    args_schema: Type[BaseModel] = BybitExecutorInput
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
        """Execute trading operations"""
        try:
            operation = operation
            logger.info(f"[BybitTradingTool] Executing operation: {operation}")
            logger.info(f"[BybitTradingTool] Arguments: {kwargs}")

            result = None
            if operation == "execute_trade":
                symbol = kwargs.get("symbol")
                side = kwargs.get("side")
                qty = kwargs.get("qty")
                
                # Проверяем наличие всех необходимых параметров
                if not symbol:
                    result = {"success": False, "error": "Symbol is required"}
                elif not side:
                    result = {"success": False, "error": "Side is required"}
                elif not qty:
                    result = {"success": False, "error": "Quantity is required"}
                else:
                    result = self._place_order(symbol, side, qty)
            else:
                result = {"success": False, "error": "Unknown operation"}

            logger.info(f"[BybitTradingTool] Operation result: {result}")
            # Форматируем результат для CrewAI
            if isinstance(result, dict):
                if result.get("success") is False:
                    return {"result": str(result.get("error", "Unknown error"))}
                return {"result": str(result.get("data", result))}
            return {"result": str(result)}

        except Exception as e:
            error_msg = f"Error in BybitTradingTool: {e}"
            logger.error(error_msg)
            return {"result": error_msg}

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
        logger.info(f"[BybitTradingTool] Placing order: symbol={symbol}, side={side}, qty={qty}")
        
        leverage_result = self._set_leverage(symbol)
        if not leverage_result["success"]:
            error_msg = f"Failed to set leverage: {leverage_result['error']}"
            logger.error(f"[BybitTradingTool] {error_msg}")
            return {"success": False, "error": error_msg}

        try:
            result = self.client.place_order(
                category="linear",
                symbol=symbol,ашч
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
            logger.info(f"[BybitTradingTool] Order placed successfully: {order_result}")
            return {"success": True, "data": order_result.model_dump()}
        except Exception as e:
            error_msg = f"Failed to place order: {e}"
            logger.error(f"[BybitTradingTool] {error_msg}")
            return {"success": False, "error": error_msg}

    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.client:
                self.client = None
            logger.info("BybitTradingTool cleanup completed")
        except Exception as e:
            logger.error(f"Error during BybitTradingTool cleanup: {e}")