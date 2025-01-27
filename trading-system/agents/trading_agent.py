from typing import Dict, Any, Optional, Callable
import asyncio
from crewai import Agent, Task, Crew
from .base_agent import BaseAgent
from .tools.trading_tools import BybitTradingTool, TradingOperationInput

class TradingAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        bybit_config: Dict[str, str],
        llm_config: Dict[str, Any],
        execution_callback: Optional[Callable] = None
    ):
        """Initialize TradingAgent"""
        super().__init__(name, llm_config)

        # Initialize tools
        self.trading_tool = BybitTradingTool(
            api_key=bybit_config['api_key'],
            api_secret=bybit_config['api_secret'],
            demo_mode=bybit_config.get('demo_mode', True)
        )

        # Add tools to agent
        self.add_tool(self.trading_tool)

        self.execution_callback = execution_callback
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        llm = self.llm_provider.get_crew_llm(temperature=0.7)

        self.market_analyst = Agent(
            role="Market Analyst",
            goal="Analyze market conditions and validate order parameters",
            backstory="""You are a market analysis expert who evaluates trading conditions
            and validates order parameters. You ensure trades meet all requirements and 
            market conditions are suitable for execution.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.trading_tool],
            llm=llm
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
            llm=llm
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

            # Get current market price
            price_check = await self.trading_tool._arun(
                operation="get_market_price",
                symbol=trade_signal["symbol"]
            )
            if not price_check["success"]:
                self.logger.error(f"Failed to get market price: {price_check['error']}")
                return

            current_price = price_check["data"]
            signal_price = trade_signal["price"]

            # Check if price hasn't moved too much (1% tolerance)
            price_diff_percent = abs(current_price - signal_price) / signal_price * 100
            if price_diff_percent > 1:
                self.logger.warning(
                    f"Price moved too much. Signal: {signal_price}, Current: {current_price}, "
                    f"Difference: {price_diff_percent:.2f}%"
                )
                return

            # Execute order with retry mechanism
            order_data = {
                "operation": "place_order",
                "symbol": trade_signal["symbol"],
                "side": trade_signal["action"].capitalize(),
                "qty": trade_signal["qty"]
            }
            execution_result = await self._execute_order_with_retry(order_data)
            
            if not execution_result["success"]:
                self.logger.error(f"Order execution failed: {execution_result['error']}")
                return

            # Update state and notify
            self.state.last_action = f"Executed {order_data['side']} order for {order_data['symbol']}"
            if self.execution_callback:
                await self.execution_callback({
                    "status": "success",
                    "order": order_data,
                    "result": execution_result["data"],
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
                result = await self.trading_tool._arun(**order_data)
                if result["success"]:
                    return result
                
                retries += 1
                if retries < max_retries:
                    self.logger.warning(f"Retry {retries}/{max_retries}: {result['error']}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {"success": False, "error": f"Max retries reached: {result['error']}"}
                    
            except Exception as e:
                retries += 1
                if retries < max_retries:
                    self.logger.warning(f"Retry {retries}/{max_retries} after error: {e}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {"success": False, "error": str(e)}

    async def initialize(self):
        """Initialize the trading agent"""
        if not await super().initialize():
            return False

        self.logger.info("Initializing Trading Agent...")

        try:
            # Verify exchange connection
            balance = await self.trading_tool._arun(operation="get_wallet_balance")
            if not balance["success"]:
                self.logger.error(f"Failed to connect to exchange: {balance['error']}")
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
                await asyncio.sleep(1)  # Prevent CPU overload
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")

    async def cleanup(self):
        """Cleanup resources"""
        self.state.is_active = False
        self.logger.info(f"Agent {self.name} cleaned up")
