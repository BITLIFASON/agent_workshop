from typing import Dict, Any, Callable
import asyncio
from .base_agent import BaseAgent
from .tools.balance_tools import DatabaseTool, ManagementServiceTool, BybitTradingTool

class BalanceControlAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        trading_callback: Callable
    ):
        super().__init__(name)

        # Initialize tools
        self.management_tool = ManagementServiceTool(config['management_api'])
        self.db_tool = DatabaseTool(config['database'])
        self.trading_tool = BybitTradingTool(config['bybit'])

        self.add_tool(self.management_tool)
        self.add_tool(self.db_tool)
        self.add_tool(self.trading_tool)

        self.trading_callback = trading_callback

    async def initialize(self):
        """Initialize the balance control agent"""
        self.logger.info("Initializing Balance Control Agent...")

        # Initialize database tool
        db_result = await self.db_tool.initialize()
        if not db_result.success:
            self.logger.error(f"Failed to initialize database tool: {db_result.error}")
            return False

        self.state.is_active = True
        return True

    async def process_signal(self, signal: Dict[str, Any]):
        """Process incoming trading signal"""
        try:
            if not self.state.is_active:
                self.logger.error("Agent not initialized")
                return

            # Validate signal
            if not await self._validate_signal(signal):
                return

            if signal["action"] == "buy":
                await self._process_buy_signal(signal)
            else:
                await self._process_sell_signal(signal)

        except Exception as e:
            self.logger.error(f"Error processing signal: {e}")
            self.state.last_error = str(e)

    async def _process_buy_signal(self, signal: Dict[str, Any]):
        """Process buy signal"""
        try:
            # Get system status
            status_result = await self.management_tool.execute("get_system_status")
            if not status_result.success or status_result.data != "enable":
                self.logger.warning("Trading system is not enabled")
                return

            # Check price limit
            price_limit_result = await self.management_tool.execute("get_price_limit")
            if not price_limit_result.success:
                raise Exception(f"Failed to get price limit: {price_limit_result.error}")

            if signal["price"] > price_limit_result.data:
                self.logger.warning(f"Price {signal['price']} exceeds limit {price_limit_result.data}")
                return

            # Check available lots
            num_available_lots_result = await self.management_tool.execute("get_num_available_lots")
            if not num_available_lots_result.success:
                raise Exception(f"Failed to get available lots: {num_available_lots_result.error}")
            num_available_lots = num_available_lots_result.data

            # Get fake balance
            fake_balance_result = await self.management_tool.execute("get_fake_balance")
            if not fake_balance_result.success:
                raise Exception(f"Failed to get balance: {fake_balance_result.error}")
            fake_balance = fake_balance_result.data

            # Calculate quantity
            qty = await self._calculate_quantity(
                signal["symbol"],
                fake_balance,
                signal["price"],
                num_available_lots
            )

            # Process trade
            trade_signal = {
                "symbol": signal["symbol"],
                "action": "buy",
                "qty": qty
            }

            await self.trading_callback(trade_signal)

            await self.db_tool.execute("create_lot", signal["symbol"], qty, signal["price"])
            await self.db_tool.execute("create_history_lot","buy", signal["symbol"], qty, signal["price"])

        except Exception as e:
            self.logger.error(f"Error processing buy signal: {e}")
            raise

    async def _process_sell_signal(self, signal: Dict[str, Any]):
        """Process sell signal"""
        try:
            # Check if we have this lot
            active_lots = await self.db_tool.execute("get_active_lots")
            if not active_lots.success:
                raise Exception(f"Failed to get active lots: {active_lots.error}")

            lot = next((lot for lot in active_lots.data if lot["symbol"] == signal["symbol"]), None)
            if not lot:
                self.logger.warning(f"No active lot found for {signal['symbol']}")
                return

            # Execute trade
            trade_signal = {
                "symbol": signal["symbol"],
                "action": "sell",
                "qty": lot["qty"]
            }
            await self.trading_callback(trade_signal)

            # Record transaction
            await self.db_tool.execute("delete_lot", signal["symbol"])
            await self.db_tool.execute("create_history_lot","sell",signal["symbol"],lot["qty"],signal["price"])

            # FIX add delta profit

        except Exception as e:
            self.logger.error(f"Error processing sell signal: {e}")
            raise

    async def _validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate trading signal"""
        required_fields = ["symbol", "action", "price"]
        return all(field in signal for field in required_fields)

    async def _calculate_quantity(self, symbol:str, fake_balance: float, price: float, num_available_lots: int) -> float:
        """Calculate trading quantity based on available balance"""

        result_symbol_wallet_balance = await self.trading_tool.execute(operation="get_coin_balance", symbol=symbol)
        if not result_symbol_wallet_balance.success:
            raise Exception(f"Failed to get active lots: {result_symbol_wallet_balance.error}")
        symbol_wallet_balance = result_symbol_wallet_balance.data

        result_symbol_qty_info = await self.trading_tool.execute(operation="get_coin_info", symbol=symbol)
        if not result_symbol_qty_info.success:
            raise Exception(f"Failed to get active lots: {result_symbol_qty_info.error}")
        symbol_qty_info = result_symbol_qty_info.data
        max_qty = symbol_qty_info.get("max_qty")
        min_qty = symbol_qty_info.get("min_qty")
        step_qty = symbol_qty_info.get("step_qty")
        min_order_usdt = symbol_qty_info.get("min_order_usdt")

        if len(step_qty.split('.')) == 1:
            precision_qty = 0
        else:
            precision_qty = len(step_qty.split('.')[1])

        qty = fake_balance / num_available_lots / price
        qty -= symbol_wallet_balance

        qty = round(qty, precision_qty)
        if qty * price < min_order_usdt and qty < min_qty:
            qty = 0
        elif qty > max_qty:
            qty = max_qty

        return qty

    async def cleanup(self):
        """Cleanup resources"""
        await self.db_tool.cleanup()
        await super().cleanup()

    async def run(self):
        """Main execution loop"""
        self.logger.info("Balance Control Agent running...")
        while self.state.is_active:
            await asyncio.sleep(1)  # Prevent CPU overload
