from typing import Dict, Any, Optional, Callable
import asyncio
from loguru import logger
from crewai import Agent, Task, Crew
from .base_agent import BaseAgent
from .tools.balance_tools import (
    DatabaseTool,
    ManagementServiceTool,
    BybitTradingTool
)

class BalanceControlAgent(BaseAgent):
    """Agent for controlling trading balance and lot management"""

    def __init__(
        self,
        name: str,
        config: Dict[str, Dict[str, Any]],
        trading_callback: Optional[Callable] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize BalanceControlAgent"""
        super().__init__(
            name=name,
            role="Balance Controller",
            goal="Monitor and control trading balance",
            backstory="I am responsible for managing trading balances and ensuring compliance with system limits",
            llm_config=llm_config,
            **kwargs
        )

        # Initialize tools
        management_config = config.get('management_service', {})
        self.management_tool = ManagementServiceTool(
            host=management_config.get('host'),
            port=management_config.get('port'),
            token=management_config.get('token')
        )

        db_config = config.get('database', {})
        self.db_tool = DatabaseTool(
            host=db_config.get('host'),
            port=db_config.get('port'),
            user=db_config.get('user'),
            password=db_config.get('password'),
            database=db_config.get('database')
        )

        bybit_config = config.get('bybit', {})
        self.trading_tool = BybitTradingTool(
            api_key=bybit_config.get('api_key'),
            api_secret=bybit_config.get('api_secret'),
            demo_mode=bybit_config.get('demo_mode', True)
        )

        self.tools = [
            self.management_tool,
            self.db_tool,
            self.trading_tool
        ]

        self.trading_callback = trading_callback

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
            llm=self.llm_provider.get_crew_llm(temperature=0.7)
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
            llm=self.llm_provider.get_crew_llm(temperature=0.7)
        )

        self.db_manager = Agent(
            role="Database Manager",
            goal="Manage trading records and history",
            backstory="""You are responsible for maintaining accurate records of
            all trading activities, lots, and historical data.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.db_tool],
            llm=self.llm_provider.get_crew_llm(temperature=0.7)
        )

        self.crew = Crew(
            agents=[self.system_monitor, self.trade_analyzer, self.db_manager],
            tasks=[],
            verbose=True
        )

    async def process_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Process trading signal"""
        try:
            logger.info(f"Processing signal in {self.name}: {signal_data}")

            # Get system status
            status_result = await self.management_tool._arun(
                operation="get_system_status"
            )
            if status_result["status"] != "success":
                logger.error(f"Failed to get system status: {status_result}")
                return False

            # Get price limits
            limits_result = await self.management_tool._arun(
                operation="get_price_limits",
                symbol=signal_data["symbol"]
            )
            if limits_result["status"] != "success":
                logger.error(f"Failed to get price limits: {limits_result}")
                return False

            # Execute trade if conditions are met
            if self.trading_callback:
                await self.trading_callback(signal_data)
                logger.info(f"Trade executed for signal: {signal_data}")
                return True
            else:
                logger.warning("No trading callback set")
                return False

        except Exception as e:
            logger.error(f"Error processing signal in {self.name}: {e}")
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
            await self.management_tool.cleanup()
            await self.db_tool.cleanup()
            await self.trading_tool.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up {self.name}: {e}")
            raise
