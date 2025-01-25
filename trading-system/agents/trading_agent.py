from typing import Dict, Any
import asyncio
from crewai import Agent, Task, Crew
from .base_agent import BaseAgent
from .tools.trading_tools import BybitTradingTool, OrderValidatorTool

class TradingAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        bybit_config: Dict[str, str],
        openai_api_key: str,
        execution_callback=None
    ):
        super().__init__(name)

        # Initialize tools
        self.trading_tool = BybitTradingTool(bybit_config)
        self.validator_tool = OrderValidatorTool()

        self.add_tool(self.trading_tool)
        self.add_tool(self.validator_tool)

        self.execution_callback = execution_callback
        self.openai_api_key = openai_api_key
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        self.market_analyst = Agent(
            role="Market Analyst",
            goal="Analyze market conditions and validate order parameters",
            backstory="""You are a market analysis expert who evaluates trading conditions
            and validates order parameters. You use order validation tools to ensure trades
            meet all requirements and market conditions are suitable for execution.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.validator_tool],
            llm_config={"api_key": self.openai_api_key}
        )

        self.order_executor = Agent(
            role="Order Executor",
            goal="Execute and manage trading orders",
            backstory="""You are responsible for executing trades with proper
            parameters, managing order status, and handling execution issues.
            You ensure orders are placed correctly and monitor their execution.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.trading_tool],
            llm_config={"api_key": self.openai_api_key}
        )

        self.crew = Crew(
            agents=[self.market_analyst, self.order_executor],
            tasks=[],
            verbose=True
        )

    async def execute_trade(self, trade_signal: Dict[str, Any]):
        """Execute a trade based on the signal"""
        try:
            if not self.state.is_active:
                self.logger.error("Agent not initialized")
                return

            # Prepare order data for validation
            order_data = {
                "symbol": trade_signal["symbol"],
                "side": trade_signal["action"],
                "qty": trade_signal["qty"]
            }

            # Get current market price
            price_check = await self.trading_tool.execute("get_market_price", symbol=trade_signal["symbol"])
            if not price_check.success:
                self.logger.error(f"Failed to get market price: {price_check.error}")
                return

            current_price = price_check.data
            signal_price = trade_signal["price"]

            # Check if price hasn't moved too much (1% tolerance)
            price_diff_percent = abs(current_price - signal_price) / signal_price * 100
            if price_diff_percent > 1:
                self.logger.warning(
                    f"Price moved too much. Signal: {signal_price}, Current: {current_price}, "
                    f"Difference: {price_diff_percent:.2f}%"
                )
                return

            # Analyze market conditions and validate order
            analysis_task = Task(
                description=f"""Analyze and validate trade order:
                Symbol: {order_data['symbol']}
                Action: {order_data['side']}
                Quantity: {order_data['qty']}
                Signal Price: {signal_price}
                Current Price: {current_price}
                
                1. Validate order parameters using OrderValidatorTool
                2. Check symbol trading status
                3. Verify quantity meets requirements
                4. Ensure price is within allowed range""",
                agent=self.market_analyst
            )
            analysis_result = await self.crew.kickoff([analysis_task])

            if not analysis_result.get("validation_passed", False):
                self.logger.warning(f"Order validation failed: {analysis_result.get('reason', 'Unknown reason')}")
                return

            # Execute order with retry mechanism
            execution_result = await self._execute_order_with_retry(order_data)
            if not execution_result.get("success"):
                self.logger.error(f"Order execution failed: {execution_result.get('error')}")
                return

            # Update state and notify
            self.state.last_action = f"Executed {order_data['side']} order for {order_data['symbol']}"
            if self.execution_callback:
                await self.execution_callback({
                    "status": "success",
                    "order": order_data,
                    "result": execution_result.get("data"),
                    "price": current_price
                })

        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            self.state.last_error = str(e)

    async def _execute_order_with_retry(self, order_data: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Execute order with retry mechanism"""
        retries = 0
        while retries < max_retries:
            try:
                result = await self.trading_tool.execute("place_order", **order_data)
                if result.success:
                    return {"success": True, "data": result.data}
                
                retries += 1
                if retries < max_retries:
                    self.logger.warning(f"Retry {retries}/{max_retries}: {result.error}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {"success": False, "error": f"Max retries reached: {result.error}"}
                    
            except Exception as e:
                retries += 1
                if retries < max_retries:
                    self.logger.warning(f"Retry {retries}/{max_retries} after error: {e}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {"success": False, "error": str(e)}

    async def initialize(self):
        """Initialize the trading agent"""
        self.logger.info("Initializing Trading Agent...")

        # Test connection by getting wallet balance
        try:
            # Verify exchange connection
            test_task = Task(
                description="""Verify exchange connection:
                1. Check API connectivity
                2. Verify trading permissions
                3. Get wallet balance""",
                agent=self.order_executor
            )
            result = await self.crew.kickoff([test_task])

            if not result.get("success"):
                self.logger.error(f"Failed to connect to exchange: {result.get('error')}")
                return False

            self.state.is_active = True
            return True

        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return False

    async def run(self):
        """Main execution loop"""
        self.logger.info("Trading Agent running...")
        while self.state.is_active:
            try:
                # Monitor trading status
                monitor_task = Task(
                    description="""Monitor trading status:
                    1. Check active orders
                    2. Verify trading system health
                    3. Monitor execution performance""",
                    agent=self.market_analyst
                )
                await self.crew.kickoff([monitor_task])
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")

            await asyncio.sleep(1)  # Prevent CPU overload

    async def cleanup(self):
        """Cleanup resources"""
        self.state.is_active = False
        self.logger.info(f"Agent {self.name} cleaned up")
