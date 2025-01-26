from typing import Dict, Any, Optional, Type, List, Union, Annotated
from pybit.unified_trading import HTTP
from .base_tools import ToolResult
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool


class CoinInfo(BaseModel):
    """Model for coin information"""
    max_qty: float = Field(..., description="Maximum order quantity")
    min_qty: float = Field(..., description="Minimum order quantity")
    step_qty: str = Field(..., description="Step size for quantity")
    min_order_usdt: int = Field(..., description="Minimum order size in USDT")
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class TradingOperationParams(BaseModel):
    """Base model for trading operation parameters"""
    symbol: Optional[str] = Field(None, description="Trading pair symbol (e.g., 'BTCUSDT')")
    side: Optional[str] = Field(None, description="Trading side ('buy' or 'sell')")
    qty: Optional[float] = Field(None, description="Order quantity")
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class TradingOperationInput(BaseModel):
    """Input schema for BybitTradingTool"""
    operation: str = Field(..., description="Operation to perform")
    params: TradingOperationParams = Field(default_factory=TradingOperationParams)


class OrderResult(BaseModel):
    """Model for order execution result"""
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Trading side")
    qty: float = Field(..., description="Order quantity")
    price: float = Field(..., description="Order price")
    status: str = Field(..., description="Order status")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BybitConfig(BaseModel):
    """Configuration for Bybit trading tool"""
    api_key: str = Field(..., description="API key")
    api_secret: str = Field(..., description="API secret")
    demo_mode: str = Field(default="True", description="Demo mode flag")
    leverage: str = Field(default="1", description="Trading leverage")


class BybitTradingTool(BaseTool):
    """Tool for executing trades on Bybit exchange"""
    name: str = "bybit_trading"
    description: str = "Tool for executing trades on Bybit"
    args_schema: Type[BaseModel] = TradingOperationInput
    config: Optional[BybitConfig] = Field(default=None)
    client: Optional[HTTP] = Field(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, config: Dict[str, str]):
        super().__init__(name=self.name, description=self.description)
        self.config = BybitConfig(**config)
        self.client = HTTP(
            testnet=self.config.demo_mode == 'True',
            api_key=self.config.api_key,
            api_secret=self.config.api_secret
        )

    def _run(self, operation: str, params: TradingOperationParams) -> ToolResult:
        """Synchronous version not supported"""
        raise NotImplementedError("This tool only supports async operation")

    async def _arun(self, operation: str, params: TradingOperationParams) -> ToolResult:
        """Execute trading operations asynchronously"""
        try:
            if operation == "set_leverage":
                return await self._set_leverage(params)
            elif operation == "get_wallet_balance":
                return await self._get_wallet_balance()
            elif operation == "get_coin_balance":
                return await self._get_coin_balance(params)
            elif operation == "get_coin_info":
                return await self._get_coin_info(params)
            elif operation == "place_order":
                return await self._place_order(params)
            elif operation == "get_market_price":
                return await self._get_market_price(params)
            return ToolResult(success=False, error="Unknown operation")
        except Exception as e:
            logger.error(f"Trading tool error: {e}")
            return ToolResult(success=False, error=str(e))

    async def _set_leverage(self, params: TradingOperationParams) -> ToolResult:
        symbol = params.symbol or ''
        try:
            self.client.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=self.config.leverage,
                sellLeverage=self.config.leverage
            )
            logger.info(f"Leverage set to {self.config.leverage} for {symbol}")
            return ToolResult(success=True)
        except Exception as e:
            if '110043' in str(e):
                logger.info(f"Leverage already set to {self.config.leverage} for {symbol}")
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

    async def _get_coin_balance(self, params: TradingOperationParams) -> ToolResult:
        symbol = params.symbol or ''
        if symbol[:-4] not in [item['coin'] for item in self.client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
            return ToolResult(success=True, data=0)
        symbol_wallet_balance = self.client.get_wallet_balance(
            accountType="UNIFIED",
            coin=symbol[:-4]
        )["result"]["list"][0]["coin"][0]["walletBalance"]
        symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
        return ToolResult(success=True, data=symbol_wallet_balance)

    async def _get_coin_info(self, params: TradingOperationParams) -> ToolResult:
        symbol = params.symbol or ''
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

    async def _place_order(self, params: TradingOperationParams) -> ToolResult:
        leverage_result = await self._set_leverage(params)
        if not leverage_result.success:
            return ToolResult(success=False, error=f"Failed to set leverage: {leverage_result.error}")

        try:
            result = self.client.place_order(
                category="linear",
                symbol=params.symbol,
                side=params.side.capitalize() if params.side else "Buy",
                orderType="Market",
                qty=params.qty
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

    async def _get_market_price(self, params: TradingOperationParams) -> ToolResult:
        symbol = params.symbol or ''
        ticker = self.client.get_tickers(
            category="linear",
            symbol=symbol
        )["result"]["list"][0]
        return ToolResult(success=True, data=float(ticker["lastPrice"]))


class OrderValidatorParams(BaseModel):
    """Input parameters for OrderValidatorTool"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTCUSDT')")
    side: str = Field(..., description="Trading side ('buy' or 'sell')")
    qty: float = Field(..., description="Order quantity")


class OrderValidatorInput(BaseModel):
    """Input schema for OrderValidatorTool"""
    params: OrderValidatorParams = Field(..., description="Order validation parameters")


class OrderValidatorTool(BaseTool):
    """Tool for validating trade orders"""
    name: str = "order_validator"
    description: str = "Tool for validating trade orders"
    args_schema: Type[BaseModel] = OrderValidatorInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self):
        super().__init__(name=self.name, description=self.description)

    def _run(self, params: OrderValidatorParams) -> ToolResult:
        try:
            if not params.symbol.endswith('USDT'):
                return ToolResult(success=False, error="Invalid symbol format")

            if params.qty <= 0:
                return ToolResult(success=False, error="Invalid quantity")

            if params.side.lower() not in ['buy', 'sell']:
                return ToolResult(success=False, error="Invalid side")

            return ToolResult(success=True, data=params.model_dump())

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _arun(self, params: OrderValidatorParams) -> ToolResult:
        """Async version of _run"""
        return self._run(params)
