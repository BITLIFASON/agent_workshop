from typing import Dict, Any
import asyncio
from .base_agent import BaseAgent
from .tools.base_tools import ToolResult
from .tools.trading_tools import BybitTradingTool, OrderValidatorTool

class TradingAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        bybit_config: Dict[str, str],
        execution_callback=None
    ):
        super().__init__(name)

        # Initialize tools
        self.trading_tool = BybitTradingTool(bybit_config)
        self.validator_tool = OrderValidatorTool()

        self.add_tool(self.trading_tool)
        self.add_tool(self.validator_tool)

        self.execution_callback = execution_callback
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds

    async def initialize(self):
        """Initialize the trading agent"""
        self.logger.info("Initializing Trading Agent...")

        # Test connection by getting wallet balance
        result = await self.trading_tool.execute("get_wallet_balance")
        if not result.success:
            self.logger.error(f"Failed to connect to Bybit: {result.error}")
            return False

        self.state.is_active = True
        return True

    async def execute_trade(self, trade_signal: Dict[str, Any]):
        """Execute a trade based on the signal"""
        try:
            if not self.state.is_active:
                self.logger.error("Agent not initialized")
                return

            # Prepare order data
            order_data = {
                "symbol": trade_signal["symbol"],
                "side": trade_signal["action"],
                "qty": trade_signal["qty"]
            }

            # Validate order
            validation_result = await self.validator_tool.execute(order_data)
            if not validation_result.success:
                self.logger.error(f"Order validation failed: {validation_result.error}")
                return

            # Execute order with retry mechanism
            execution_result = await self._execute_order_with_retry(order_data)
            if not execution_result.success:
                self.logger.error(f"Order execution failed: {execution_result.error}")
                return

            # Update state and notify
            self.state.last_action = f"Executed {order_data['side']} order for {order_data['symbol']}"
            if self.execution_callback:
                await self.execution_callback({
                    "status": "success",
                    "order": order_data,
                    "result": execution_result.data
                })

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            self.state.last_error = str(e)

    async def _execute_order_with_retry(self, order_data: Dict[str, Any]) -> ToolResult:
        """Execute order with retry mechanism"""
        for attempt in range(self.retry_attempts):
            try:
                result = await self.trading_tool.execute(
                    "place_order",
                    **order_data
                )
                if result.success:
                    return result

                self.logger.warning(f"Attempt {attempt + 1} failed: {result.error}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)

            except Exception as e:
                self.logger.error(f"Error in attempt {attempt + 1}: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)

        return ToolResult(success=False, error=f"Failed after {self.retry_attempts} attempts")

    async def run(self):
        """Main execution loop"""
        self.logger.info("Trading Agent running...")
        while self.state.is_active:
            await asyncio.sleep(1)  # Prevent CPU overload

    async def cleanup(self):
        """Cleanup resources"""
        self.state.is_active = False
        await super().cleanup()
