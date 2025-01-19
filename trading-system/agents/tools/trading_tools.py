from typing import Dict, Any
from pybit.unified_trading import HTTP
from .base_tools import BaseTool, ToolResult

class BybitTradingTool(BaseTool):
    def __init__(self, config: Dict[str, str]):
        super().__init__(
            name="bybit_trading",
            description="Tool for executing trades on Bybit"
        )
        self.client = HTTP(
            testnet=False,
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            demo=config.get('demo_mode', 'True') == 'True'
        )

    async def execute(self, operation: str, **kwargs) -> ToolResult:
        try:
            if operation == "place_order":
                result = self.client.place_order(
                    category="linear",
                    symbol=kwargs['symbol'],
                    side=kwargs['side'].capitalize(),
                    order_type="Market",
                    qty=kwargs['qty']
                )
                return ToolResult(success=True, data=result)

            elif operation == "get_wallet_balance":
                result = self.client.get_wallet_balance(
                    accountType="UNIFIED",
                    coin=kwargs.get('coin', 'USDT')
                )
                return ToolResult(success=True, data=result)

            elif operation == "get_position":
                result = self.client.get_positions(
                    category="linear",
                    symbol=kwargs['symbol']
                )
                return ToolResult(success=True, data=result)

            else:
                return ToolResult(success=False, error="Unknown operation")

        except Exception as e:
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
