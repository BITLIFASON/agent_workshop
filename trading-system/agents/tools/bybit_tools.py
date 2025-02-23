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
    - get_coin_info: Get coin trading information, need symbol (e.g. MINAUSDT)
    - skip_balance_operation: Skip balance operation
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
            if operation == "get_coin_info":
                symbol = kwargs.get("symbol")
                result = self._get_coin_info(symbol)
            elif operation == "skip_balance_operation":
                result = {"success operation": True, "data": "Balance operation skipped"}
            else:
                result = {"success operation": False, "error": "Unknown operation"}

            logger.info(f"[BybitBalanceTool] Operation result: {result}")
            # Format result for CrewAI
            if isinstance(result, dict):
                if result.get("success operation") is False:
                    return {"result": str(result.get("error", "Unknown error"))}
                return {"result": str(result.get("data", result))}
            return {"result": str(result)}

        except Exception as e:
            error_msg = f"Error in BybitBalanceTool: {e}"
            logger.error(error_msg)
            return {"result": error_msg}

    def _get_coin_info(self, symbol: str) -> Dict[str, Any]:
        """Get coin trading information"""
        try:
            symbol_qty_info = self.client.get_instruments_info(
                category="linear",
                symbol=symbol
            )["result"]["list"][0]["lotSizeFilter"]
            
            coin_info = CoinInfo(
                maxOrderQty=symbol_qty_info.get("maxMktOrderQty"),
                minOrderQty=symbol_qty_info.get("minOrderQty"),
                qtyStep=symbol_qty_info.get("qtyStep"),
                minNotionalValue=symbol_qty_info.get("minNotionalValue")
            )
            return {"success operation": True, "data": coin_info.model_dump()}
        except Exception as e:
            return {"success operation": False, "error": str(e)}

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
    - skip_trade_operation: Skip a trade operation
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
                
                # Check if all required parameters are present
                if not symbol:
                    result = {"success operation": False, "error": "Symbol is required"}
                elif not side:
                    result = {"success operation": False, "error": "Side is required"}
                elif not qty:
                    result = {"success operation": False, "error": "Quantity is required"}
                else:
                    result = self._place_order(symbol, side, qty)
            elif operation == "skip_trade_operation":
                result = {"success operation": True, "data": "Trade skipped"}
            else:
                result = {"success operation": False, "error": "Unknown operation"}

            logger.info(f"[BybitTradingTool] Operation result: {result}")
            # Format result for CrewAI
            if isinstance(result, dict):
                if result.get("success operation") is False:
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
            return {"success operation": True}
        except Exception as e:
            if '110043' in str(e):
                logger.info(f"Leverage already set to {1} for {symbol}")
                return {"success operation": True}
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return {"success operation": False, "error": str(e)}

    def _place_order(self, symbol: str, side: str, qty: float) -> Dict[str, Any]:
        """Place market order"""
        logger.info(f"[BybitTradingTool] Placing order: symbol={symbol}, side={side}, qty={qty}")
        
        leverage_result = self._set_leverage(symbol)
        if not leverage_result["success operation"]:
            error_msg = f"Failed to set leverage: {leverage_result['error']}"
            logger.error(f"[BybitTradingTool] {error_msg}")
            return {"success operation": False, "error": error_msg}

        try:
            result = self.client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=qty
            )
            
            order_result = OrderResult(
                retCode=result["retCode"],
                retMsg=result["retMsg"],
                orderId=result["result"]["orderId"],
                orderLinkId=result["result"]["orderLinkId"],
                retExtInfo=result["retExtInfo"],
                time=result["time"]
            )
            logger.info(f"[BybitTradingTool] Order placed successfully: {order_result}")
            return {"success operation": True, "data": order_result.model_dump()}
        except Exception as e:
            error_msg = f"Failed to place order: {e}"
            logger.error(f"[BybitTradingTool] {error_msg}")
            return {"success operation": False, "error": error_msg}

    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.client:
                self.client = None
            logger.info("BybitTradingTool cleanup completed")
        except Exception as e:
            logger.error(f"Error during BybitTradingTool cleanup: {e}")