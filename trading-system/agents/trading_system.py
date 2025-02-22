from typing import Dict, Any
import asyncio
from pydantic import BaseModel, ConfigDict
from loguru import logger
from crewai import Crew, Process, Task
from .signal_module import create_signal_parser_agent, cleanup_signal_tools
from .trading_module import (
    create_trading_executor_agent,
    create_balance_controller_agent,
    create_write_info_agent
)
from .utils.llm_providers import LLMProvider, LLMFactory
from .utils.models import (
    TelegramConfig, BybitConfig, DatabaseConfig,
    ManagementAPIConfig, LLMConfig
)


class SystemConfig(BaseModel):
    """Trading system configuration model"""
    telegram: TelegramConfig
    bybit: BybitConfig
    database: DatabaseConfig
    management_api: ManagementAPIConfig
    llm: LLMConfig

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class TradingSystem:
    def __init__(self, config: Dict[str, Any]):
        """Initialize trading system with configuration"""
        try:
            # Validate configuration
            self.config = SystemConfig(**config)
        except Exception as e:
            logger.error(f"Error initializing trading system: {e}")
            raise

    def _initialize_llm(self):
        """Initialize shared LLM instance"""
        try:
            provider_type = LLMProvider(self.config.llm.provider)
            llm_config = {
                "api_key": self.config.llm.api_key,
                "model": self.config.llm.model,
            }
            llm_provider = LLMFactory.create_provider(provider_type, llm_config)
            if not llm_provider:
                raise ValueError(f"Failed to create LLM provider: {provider_type}")
            self.llm = llm_provider.get_crew_llm()
            logger.info(f"Initialized shared LLM instance with provider {provider_type}")
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            raise

    def _create_agents(self):
        """Create agent instances"""
        try:

            # Create Parser Agent
            self.parser_agent = create_signal_parser_agent(
                name="signal_parser",
                llm=self.llm
            )

            # Create Balance Control Agent with trading callback
            self.balance_control_agent = create_balance_controller_agent(
                name="balance_controller",
                config={
                    "management_api": self.config.management_api.model_dump(),
                    "database": self.config.database.model_dump(),
                    "bybit": self.config.bybit.model_dump()
                },
                llm=self.llm
            )

            # Create Trading Agent
            self.trading_agent = create_trading_executor_agent(
                name="trading_executor",
                bybit_config=self.config.bybit.model_dump(),
                llm=self.llm
            )

            self.writer_info_agent = create_write_info_agent(
                name="balance_controller",
                config={
                    "database": self.config.database.model_dump()
                },
                llm=self.llm
            )

        except Exception as e:
            logger.error(f"Error creating agents: {e}")
            raise

    def _create_crew(self):
        """Create and configure the trading crew"""
        try:
            # Create tasks for each agent
            signal_parsing_task = Task(
                description="""Parse incoming messages and extract trading information.
                Validate signal format and content.""",
                expected_output="""Dict with parse signal params (symbol, side, price)""",
                agent=self.parser_agent
            )

            balance_control_task = Task(
                description="""Using the input data and taking into account the information from the database 
                and the management service, it is necessary to calculate the best coin quantity.""",
                expected_output="""Dict with parameters order (symbol, side, qty, price)""",
                agent=self.balance_control_agent
            )

            trading_execution_task = Task(
                description="""Execute trades on the exchange.
                Place and manage orders with proper parameters.
                Monitor order execution status.""",
                expected_output="""Result parameters of order (side, symbol, qty, price)""",
                agent=self.trading_agent
            )

            writing_info_task = Task(
                description="""Write info about order to database.
                Place and manage orders with proper parameters.
                Monitor order execution status.""",
                expected_output="""Status of database operations""",
                agent=self.writer_info_agent
            )

            # Create crew with defined tasks
            self.crew = Crew(
                agents=[self.parser_agent, self.balance_control_agent, self.trading_agent, self.writer_info_agent],
                tasks=[signal_parsing_task, balance_control_task, trading_execution_task, writing_info_task],
                process=Process.sequential,
                verbose=True
            )

            logger.info("Trading crew created successfully")
        except Exception as e:
            logger.error(f"Error creating trading crew: {e}")
            raise

    async def get_crew(self) -> Crew:
        """Getting crew"""
        try:
            return self.crew
        except Exception as e:
            logger.error(f"Error getting trading system: {e}")

    async def initialize(self) -> bool:
        """Initialize the trading system"""
        try:
            logger.info("Initializing trading system...")
            # Initialize crew
            self._initialize_llm()
            self._create_agents()
            self._create_crew()
            logger.info("Trading system initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing trading system: {e}")
            return False

    async def start(self):
        """Start the trading system"""
        try:
            logger.info("Starting trading system...")

            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error starting trading system: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Shutdown the trading system"""
        try:
            logger.info("Shutting down trading system...")
            
            # Shutdown crew
            if hasattr(self, 'crew'):
                await self.crew.kickoff({
                    "operation": "shutdown_system"
                })

            # Cleanup parser agent
            if hasattr(self, 'parser_agent'):
                if hasattr(self.parser_agent, 'tools'):
                    for tool in self.parser_agent.tools:
                        if hasattr(tool, 'cleanup'):
                            await tool.cleanup()
                logger.info("Signal parser agent cleanup completed")

            # Cleanup balance control agent
            if hasattr(self, 'balance_control_agent'):
                if hasattr(self.balance_control_agent, 'tools'):
                    for tool in self.balance_control_agent.tools:
                        if hasattr(tool, 'cleanup'):
                            await tool.cleanup()
                logger.info("Balance control agent cleanup completed")

            # Cleanup trading agent
            if hasattr(self, 'trading_agent'):
                if hasattr(self.trading_agent, 'tools'):
                    for tool in self.trading_agent.tools:
                        if hasattr(tool, 'cleanup'):
                            await tool.cleanup()
                logger.info("Trading agent cleanup completed")

            logger.info("Trading system shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
