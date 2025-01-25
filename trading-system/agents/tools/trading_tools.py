from typing import Dict, Any
from pybit.unified_trading import HTTP
from .base_tools import BaseTool, ToolResult
import logging

logger = logging.getLogger(__name__)

class BybitTradingTool(BaseTool):
    def __init__(self, config: Dict[str, str]):
        super().__init__(
            name="bybit_trading",
            description="Tool for executing trades on Bybit"
        )
        self.client = HTTP(
            testnet=config.get('demo_mode', 'True') == 'True',
            api_key=config['api_key'],
            api_secret=config['api_secret']
        )
        self.leverage = str(config['leverage'])

    async def execute(self, operation: str, **kwargs) -> ToolResult:
        try:
            if operation == "set_leverage":
                symbol = kwargs.get('symbol', '')
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
                    # Error code 110043 means leverage is already set to the requested value
                    if '110043' in str(e):
                        logger.info(f"Leverage already set to {self.leverage} for {symbol}")
                        return ToolResult(success=True)
                    logger.error(f"Failed to set leverage for {symbol}: {e}")
                    return ToolResult(success=False, error=str(e))

            if operation == "get_wallet_balance":
                balance_info = self.client.get_wallet_balance(accountType="UNIFIED",
                                                              coin="USDT")["result"]["list"][0]["coin"][0]["walletBalance"]
                balance_info = float(balance_info) if balance_info != '' else 0
                return ToolResult(success=True, data=balance_info)

            if operation == "get_coin_balance":
                symbol = kwargs.get('symbol', '')
                if symbol[:-4] not in [item['coin'] for item in self.client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
                    return ToolResult(success=True, data=0)
                symbol_wallet_balance = self.client.get_wallet_balance(accountType="UNIFIED", coin=symbol[:-4])["result"]["list"][0]["coin"][0]["walletBalance"]
                symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
                return ToolResult(success=True, data=symbol_wallet_balance)

            if operation == "get_coin_info":
                symbol = kwargs.get('symbol', '')
                symbol_qty_info = self.client.get_instruments_info(category="linear",
                                                                   symbol=symbol)["result"]["list"][0]["lotSizeFilter"]
                max_qty = float(symbol_qty_info.get("maxMktOrderQty"))
                min_qty = float(symbol_qty_info.get("minOrderQty"))
                step_qty = symbol_qty_info.get("qtyStep")
                min_order_usdt = int(symbol_qty_info.get("minNotionalValue"))
                symbol_info={"max_qty":max_qty,
                             "min_qty":min_qty,
                             "step_qty":step_qty,
                             "min_order_usdt":min_order_usdt}
                return ToolResult(success=True, data=symbol_info)

            if operation == "place_order":
                # Set leverage before placing order
                leverage_result = await self.execute("set_leverage", symbol=kwargs.get('symbol'))
                if not leverage_result.success:
                    return ToolResult(success=False, error=f"Failed to set leverage: {leverage_result.error}")

                # Place the actual order
                try:
                    result = self.client.place_order(
                        category="linear",
                        symbol=kwargs['symbol'],
                        side=kwargs['side'].capitalize(),
                        orderType="Market",
                        qty=kwargs['qty']
                    )
                    logger.info(f"Order placed successfully: {result}")
                    return ToolResult(success=True, data=result)
                except Exception as e:
                    logger.error(f"Failed to place order: {e}")
                    return ToolResult(success=False, error=str(e))

            if operation == "get_market_price":
                symbol = kwargs.get('symbol', '')
                ticker = self.client.get_tickers(
                    category="linear",
                    symbol=symbol
                )["result"]["list"][0]
                return ToolResult(success=True, data=float(ticker["lastPrice"]))

            return ToolResult(success=False, error="Unknown operation")

        except Exception as e:
            logger.error(f"Trading tool error: {e}")
            return ToolResult(success=False, error=str(e))

class OrderValidatorTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="order_validator",
            description="Tool for validating trade orders"
        )

    async def execute(self, order_data: Dict[str, Any]) -> ToolResult:
        try:
            # Validate required fields
            required_fields = ['symbol', 'side', 'qty']
            if not all(field in order_data for field in required_fields):
                return ToolResult(success=False, error="Missing required fields")

            # Validate symbol format
            if not order_data['symbol'].endswith('USDT'):
                return ToolResult(success=False, error="Invalid symbol format")

            # Validate quantity
            if float(order_data['qty']) <= 0:
                return ToolResult(success=False, error="Invalid quantity")

            # Validate side
            if order_data['side'].lower() not in ['buy', 'sell']:
                return ToolResult(success=False, error="Invalid side")

            return ToolResult(success=True, data=order_data)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
