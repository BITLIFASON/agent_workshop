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
        openai_api_key: str
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
        self.openai_api_key = openai_api_key

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        self.system_monitor = Agent(
            role="System Monitor",
            goal="Monitor system status and validate trading conditions",
            backstory="""You are responsible for monitoring the trading system's status,
            checking price limits, fake balance, and available lots. You ensure all
            trading conditions are met before allowing a trade.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.management_tool],
            llm_config={"api_key": self.openai_api_key}
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
            llm_config={"api_key": self.openai_api_key}
        )

        self.db_manager = Agent(
            role="Database Manager",
            goal="Manage trading records and history",
            backstory="""You are responsible for maintaining accurate records of
            all trading activities, lots, and historical data.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.db_tool],
            llm_config={"api_key": self.openai_api_key}
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
        """Process buy signal using Crew AI"""
        try:
            # Check system status and constraints
            system_task = Task(
                description=f"""Check trading system status and constraints:
                Symbol: {signal['symbol']}
                Price: {signal['price']}
                
                1. Is system enabled?
                2. Check if price exceeds current limit
                3. Get fake balance
                4. Get number of available lots""",
                agent=self.system_monitor
            )
            system_result = await self.crew.kickoff([system_task])

            if not system_result.get("system_enabled", False):
                self.logger.warning("Trading system is not enabled")
                return

            if system_result.get("price_exceeded", False):
                self.logger.warning(f"Price {signal['price']} exceeds limit")
                return

            fake_balance = system_result.get("fake_balance", 0)
            available_lots = system_result.get("available_lots", 0)

            if available_lots <= 0:
                self.logger.warning("No available lots")
                return

            # Get symbol trading limits
            symbol_info = await self.trading_tool.execute("get_coin_info", symbol=signal['symbol'])
            if not symbol_info.success:
                self.logger.error(f"Failed to get symbol info: {symbol_info.error}")
                return

            limits = symbol_info.data
            
            # Calculate position size
            analysis_task = Task(
                description=f"""Analyze trade and calculate position size:
                Symbol: {signal['symbol']}
                Entry Price: {signal['price']}
                Fake Balance: {fake_balance}
                Available Lots: {available_lots}
                Min Order Size: {limits['min_order_usdt']} USDT
                Min Quantity: {limits['min_qty']}
                Max Quantity: {limits['max_qty']}
                Step Size: {limits['step_qty']}
                
                1. Calculate optimal quantity based on fake balance and lots
                2. Ensure quantity meets min/max limits
                3. Round quantity to step size
                4. Verify total value >= min order size""",
                agent=self.trade_analyzer
            )
            analysis_result = await self.crew.kickoff([analysis_task])

            qty = analysis_result.get("position_size")
            if not qty:
                self.logger.warning("Failed to calculate position size")
                return

            # Validate quantity
            if qty < float(limits['min_qty']):
                self.logger.warning(f"Quantity {qty} is below minimum {limits['min_qty']}")
                return

            if qty > float(limits['max_qty']):
                self.logger.warning(f"Quantity {qty} exceeds maximum {limits['max_qty']}")
                return

            # Round to step size
            step_size = float(limits['step_qty'])
            qty = round(qty / step_size) * step_size

            # Check minimum order value
            order_value = qty * signal['price']
            if order_value < float(limits['min_order_usdt']):
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
            db_task = Task(
                description=f"""Record buy transaction:
                Symbol: {signal['symbol']}
                Quantity: {qty}
                Price: {signal['price']}
                
                1. Create new lot record
                2. Create history record""",
                agent=self.db_manager
            )
            await self.crew.kickoff([db_task])

        except Exception as e:
            self.logger.error(f"Error processing buy signal: {e}")
            raise

    async def _process_sell_signal(self, signal: Dict[str, Any]):
        """Process sell signal using Crew AI"""
        try:
            # Check active lots
            db_task = Task(
                description=f"""Check active lots for {signal['symbol']}:
                1. Get active lot information
                2. Verify lot exists""",
                agent=self.db_manager
            )
            result = await self.crew.kickoff([db_task])

            lot = result.get("active_lot")
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
            record_task = Task(
                description=f"""Record sell transaction:
                Symbol: {signal['symbol']}
                Quantity: {lot['qty']}
                Price: {signal['price']}
                
                1. Delete active lot
                2. Create history record""",
                agent=self.db_manager
            )
            await self.crew.kickoff([record_task])

        except Exception as e:
            self.logger.error(f"Error processing sell signal: {e}")
            raise

    async def _validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate trading signal"""
        required_fields = ["symbol", "action", "price"]
        if not all(field in signal for field in required_fields):
            self.logger.warning(f"Missing required fields in signal: {signal}")
            return False
            
        try:
            # Validate symbol format
            if not signal["symbol"].endswith('USDT'):
                self.logger.warning(f"Invalid symbol format: {signal['symbol']}")
                return False
                
            # Validate price
            if not isinstance(signal["price"], (int, float)) or signal["price"] <= 0:
                self.logger.warning(f"Invalid price: {signal['price']}")
                return False
                
            # Validate action
            if signal["action"] not in ["buy", "sell"]:
                self.logger.warning(f"Invalid action: {signal['action']}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating signal: {e}")
            return False

    async def initialize(self):
        """Initialize the balance control agent"""
        try:
            self.logger.info("Initializing Balance Control Agent...")
            
            # Initialize tools
            db_init = await self.db_tool.initialize()
            if not db_init.success:
                self.logger.error(f"Failed to initialize database tool: {db_init.error}")
                return False

            # Test management service connection
            status = await self.management_tool.execute("get_system_status")
            if not status.success:
                self.logger.error(f"Failed to connect to management service: {status.error}")
                return False

            # Test trading tool connection
            balance = await self.trading_tool.execute("get_wallet_balance")
            if not balance.success:
                self.logger.error(f"Failed to connect to trading service: {balance.error}")
                return False

            self.state.is_active = True
            self.logger.info("Balance Control Agent initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Balance Control Agent: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self.db_tool, 'cleanup'):
                await self.db_tool.cleanup()
            if hasattr(self.trading_tool, 'cleanup'):
                await self.trading_tool.cleanup()
            await super().cleanup()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def run(self):
        """Main execution loop"""
        self.logger.info("Balance Control Agent running...")
        while self.state.is_active:
            try:
                # Monitor system status
                status_task = Task(
                    description="""Monitor system parameters:
                    1. Check system status
                    2. Verify price limits
                    3. Monitor fake balance
                    4. Track available lots""",
                    agent=self.system_monitor
                )
                await self.crew.kickoff([status_task])
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
            
            await asyncio.sleep(60)  # Check every minute
