from typing import Dict, Any, Optional
import asyncio
from loguru import logger
from crewai import Agent
from .base_agent import BaseAgent
from .tools.trading_tools import BybitTradingTool


class TradingAgent(BaseAgent):
    """Agent for executing trades on exchange"""

    def __init__(
        self,
        name: str,
        bybit_config: Dict[str, Any],
        llm_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize TradingAgent"""
        super().__init__(
            name=name,
            role="Trading Executor",
            goal="Execute trades on exchange accurately and efficiently",
            backstory="""You are a trading executor responsible for placing and managing orders
            on the Bybit exchange. You ensure trades are executed with proper parameters and
            monitor their execution status.""",
            llm_config=llm_config,
            tools=[]
        )

        # Initialize trading tool
        self.trading_tool = BybitTradingTool(
            api_key=bybit_config['api_key'],
            api_secret=bybit_config['api_secret'],
            demo_mode=bybit_config.get('demo_mode', True)
        )
        self.tools = [self.trading_tool]

        # Initialize Crew AI components
        self._setup_crew()

    def _setup_crew(self):
        """Setup Crew AI agents and tasks"""
        llm = self.llm_provider.get_crew_llm(temperature=0.7)

        self.trade_executor = Agent(
            role="Trade Executor",
            goal="Execute trades accurately and efficiently",
            backstory="""You are responsible for executing trades on the exchange.
            You ensure trades are executed with proper parameters and monitor their status.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.trading_tool],
            llm=llm
        )

    async def execute_trade(self, signal_data: Dict[str, Any]) -> bool:
        """Execute trade based on signal"""
        try:
            logger.info(f"Executing trade in {self.name}: {signal_data}")

            # Get coin info
            coin_info = await self.trading_tool._arun(
                operation="get_coin_info",
                params={"symbol": signal_data["symbol"]}
            )
            if coin_info["status"] != "success":
                logger.error(f"Failed to get coin info: {coin_info}")
                return False

            # Execute trade
            trade_result = await self.trading_tool._arun(
                operation="execute_trade",
                params={
                    "symbol": signal_data["symbol"],
                    "side": signal_data["action"],
                    "qty": signal_data["qty"],
                    "price": signal_data["price"]
                }
            )
            if trade_result["status"] != "success":
                logger.error(f"Failed to execute trade: {trade_result}")
                return False

            logger.info(f"Trade executed successfully: {trade_result}")
            return True

        except Exception as e:
            logger.error(f"Error executing trade in {self.name}: {e}")
            return False

    async def initialize(self) -> bool:
        """Initialize agent and its tools"""
        try:
            logger.info(f"Initializing {self.name}")
            return True
        except Exception as e:
            logger.error(f"Error initializing {self.name}: {e}")
            return False

    async def run(self):
        """Main execution loop"""
        try:
            logger.info(f"Starting {self.name}")
            while True:
                await asyncio.sleep(1)  # Prevent CPU overload
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            raise

    async def cleanup(self):
        """Cleanup agent resources"""
        try:
            logger.info(f"Cleaning up {self.name}")
            await self.trading_tool.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up {self.name}: {e}")
            raise
