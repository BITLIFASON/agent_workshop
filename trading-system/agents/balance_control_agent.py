from typing import Dict, Any, Callable
import asyncio
from crewai import Agent, Task, Crew
from .base_agent import BaseAgent
from .tools.balance_tools import (
    DatabaseTool,
    ManagementServiceTool,
    BybitTradingTool
)

class BalanceControlAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        trading_callback: Callable,
        llm_config: Dict[str, Any]
    ):
        """Initialize BalanceControlAgent"""
        super().__init__(name, llm_config)
        
        # Initialize tools
        self.management_tool = ManagementServiceTool(
            host=config['management_api']['host'],
            port=config['management_api']['port'],
            token=config['management_api']['token']
        )
        
        self.db_tool = DatabaseTool(
            host=config['database']['host'],
            port=config['database']['port'],
            user=config['database']['user'],
            password=config['database']['password'],
            database=config['database']['database']
        )
        
        self.trading_tool = BybitTradingTool(
            api_key=config['bybit']['api_key'],
            api_secret=config['bybit']['api_secret'],
            demo_mode=config['bybit'].get('demo_mode', True)
        )

        # Add tools to agent
        self.add_tool(self.management_tool)
        self.add_tool(self.db_tool)
        self.add_tool(self.trading_tool)

        self.trading_callback = trading_callback

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        llm = self.llm_provider.get_crew_llm(temperature=0.7)

        self.system_monitor = Agent(
            role="System Monitor",
            goal="Monitor system status and validate trading conditions",
            backstory="""You are responsible for monitoring the trading system's status,
            checking price limits, fake balance, and available lots. You ensure all
            trading conditions are met before allowing a trade.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.management_tool],
            llm=llm
        )

        self.trade_analyzer = Agent(
            role="Trade Analyzer",
            goal="Analyze trades and calculate optimal position sizes",
            backstory="""You are a trading specialist who analyzes trades and determines
            optimal position sizes based on system constraints, fake balance, and available lots.
            You use the Bybit API to get symbol information and calculate quantities.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.trading_tool],
            llm=llm
        )

        self.db_manager = Agent(
            role="Database Manager",
            goal="Manage trading records and history",
            backstory="""You are responsible for maintaining accurate records of
            all trading activities, lots, and historical data.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.db_tool],
            llm=llm
        )

        self.crew = Crew(
            agents=[self.system_monitor, self.trade_analyzer, self.db_manager],
            tasks=[],
            verbose=True
        )

    async def process_signal(self, signal: Dict[str, Any]):
        """Process incoming trading signal"""
        try:
            if not self.state.is_active:
                self.logger.error("Agent not initialized")
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
            # Check system status
            status_result = await self.management_tool._arun(operation="get_system_status")
            if not status_result["success"] or not status_result["data"]:
                self.logger.warning("Trading system is not enabled")
                return

            # Check price limit
            price_limit = await self.management_tool._arun(operation="get_price_limit")
            if not price_limit["success"] or signal["price"] > price_limit["data"]:
                self.logger.warning(f"Price {signal['price']} exceeds limit")
                return

            # Get fake balance
            balance_result = await self.management_tool._arun(operation="get_fake_balance")
            if not balance_result["success"]:
                self.logger.error("Failed to get fake balance")
                return
            fake_balance = balance_result["data"]

            # Get available lots
            lots_result = await self.management_tool._arun(operation="get_num_available_lots")
            if not lots_result["success"] or lots_result["data"] <= 0:
                self.logger.warning("No available lots")
                return

            # Get symbol trading limits
            symbol_info = await self.trading_tool._arun(
                operation="get_coin_info",
                symbol=signal["symbol"]
            )
            if not symbol_info["success"]:
                self.logger.error(f"Failed to get symbol info: {symbol_info['error']}")
                return

            limits = symbol_info["data"]
            
            # Calculate position size based on fake balance and lots
            lot_size = fake_balance / lots_result["data"]
            qty = lot_size / signal["price"]

            # Validate quantity
            if qty < float(limits["min_qty"]):
                self.logger.warning(f"Quantity {qty} is below minimum {limits['min_qty']}")
                return

            if qty > float(limits["max_qty"]):
                self.logger.warning(f"Quantity {qty} exceeds maximum {limits['max_qty']}")
                return

            # Round to step size
            step_size = float(limits["step_qty"])
            qty = round(qty / step_size) * step_size

            # Check minimum order value
            order_value = qty * signal["price"]
            if order_value < float(limits["min_order_usdt"]):
                self.logger.warning(f"Order value {order_value} USDT is below minimum {limits['min_order_usdt']} USDT")
                return

            # Execute trade
            trade_signal = {
                "symbol": signal["symbol"],
                "action": "buy",
                "qty": qty,
                "price": signal["price"]
            }
            await self.trading_callback(trade_signal)

            # Record in database
            await self.db_tool._arun(
                operation="create_lot",
                symbol=signal["symbol"],
                qty=qty,
                price=signal["price"]
            )

        except Exception as e:
            self.logger.error(f"Error processing buy signal: {e}")
            raise

    async def _process_sell_signal(self, signal: Dict[str, Any]):
        """Process sell signal"""
        try:
            # Check active lots
            lots_result = await self.db_tool._arun(
                operation="get_active_lots",
                symbol=signal["symbol"]
            )
            if not lots_result["success"] or not lots_result["data"]:
                self.logger.warning(f"No active lot found for {signal['symbol']}")
                return

            lot = lots_result["data"][0]

            # Execute trade
            trade_signal = {
                "symbol": signal["symbol"],
                "action": "sell",
                "qty": float(lot["qty"]),
                "price": signal["price"]
            }
            await self.trading_callback(trade_signal)

            # Record transaction
            await self.db_tool._arun(
                operation="delete_lot",
                symbol=signal["symbol"]
            )

            await self.db_tool._arun(
                operation="create_history_lot",
                action="sell",
                symbol=signal["symbol"],
                qty=float(lot["qty"]),
                price=signal["price"]
            )

        except Exception as e:
            self.logger.error(f"Error processing sell signal: {e}")
            raise

    async def initialize(self):
        """Initialize the balance control agent"""
        if not await super().initialize():
            return False

        self.logger.info("Initializing Balance Control Agent...")

        # Initialize database
        db_result = await self.db_tool.initialize()
        if not db_result["success"]:
            self.logger.error(f"Failed to initialize database: {db_result['error']}")
            return False

        self.state.is_active = True
        return True

    async def run(self):
        """Main execution loop"""
        self.logger.info("Balance Control Agent running...")
        while self.state.is_active:
            try:
                await asyncio.sleep(1)  # Prevent CPU overload
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        await self.db_tool.cleanup()
        self.state.is_active = False
        self.logger.info(f"Agent {self.name} cleaned up")
