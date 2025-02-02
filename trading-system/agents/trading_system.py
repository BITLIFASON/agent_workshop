import os
from typing import Dict, Any
import asyncio
from pydantic import BaseModel, Field, ConfigDict
from loguru import logger
from crewai import Crew, Process, Task
from .signal_module import create_signal_parser_agent, cleanup_signal_tools
from .trading_module import (
    create_trading_executor_agent,
    create_balance_controller_agent,
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
            self._initialize_llm()
            self._create_agents()
            self._create_crew()
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
            # Create Trading Agent first since it's used as a callback
            self.trading_agent = create_trading_executor_agent(
                name="trading_executor",
                bybit_config=self.config.bybit.model_dump(),
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

            # Create Parser Agent last since it depends on Balance Control Agent
            self.parser_agent = create_signal_parser_agent(
                name="signal_parser",
                telegram_config=self.config.telegram.model_dump(),
                message_callback=self.process_signal,
                llm=self.llm
            )

        except Exception as e:
            logger.error(f"Error creating agents: {e}")
            raise

    def _create_crew(self):
        """Create and configure the trading crew"""
        try:
            # Create tasks for each agent
            signal_monitoring_task = Task(
                description="""Monitor Telegram channels for trading signals. 
                Parse incoming messages and extract trading information.
                Validate signal format and content.""",
                expected_output="""Dict with parse signal params""",
                agent=self.parser_agent
            )

            balance_control_task = Task(
                description="""Monitor and control trading balance.
                Verify system status and price limits.
                Manage trading lots and ensure compliance with system limits.""",
                expected_output="""Dict with decision trade about symbol, side and quantity""",
                agent=self.balance_control_agent
            )

            trading_execution_task = Task(
                description="""Execute trades on the exchange.
                Place and manage orders with proper parameters.
                Monitor order execution status.""",
                expected_output="""Dict with parameters order""",
                agent=self.trading_agent
            )

            # Create crew with defined tasks
            self.crew = Crew(
                agents=[self.parser_agent, self.balance_control_agent, self.trading_agent],
                tasks=[signal_monitoring_task, balance_control_task, trading_execution_task],
                process=Process.sequential,
                verbose=True
            )

            logger.info("Trading crew created successfully")
        except Exception as e:
            logger.error(f"Error creating trading crew: {e}")
            raise

    async def process_signal(self, signal_data: dict):
        """Process trading signal through the system"""
        try:
            logger.info(f"Processing signal: {signal_data}")
            # Запускаем обработку сигнала через crew
            result = await self.crew.kickoff({
                "signal": signal_data,
                "operation": "process_trading_signal"
            })
            logger.info(f"Signal processing result: {result}")
        except Exception as e:
            logger.error(f"Error processing signal: {e}")

    async def initialize(self) -> bool:
        """Initialize the trading system"""
        try:
            logger.info("Initializing trading system...")
            # Initialize crew
            await self.crew.kickoff({
                "operation": "initialize_system"
            })
            logger.info("Trading system initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing trading system: {e}")
            return False

    async def start(self):
        """Start the trading system"""
        try:
            logger.info("Starting trading system...")
            # Start crew operations
            await self.crew.kickoff({
                "operation": "start_system"
            })
            # Run until interrupted
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
            
            # Cleanup parser agent and its tools
            if hasattr(self, 'parser_agent'):
                await cleanup_signal_tools(self.parser_agent)
                logger.info("Signal parser cleanup completed")

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
