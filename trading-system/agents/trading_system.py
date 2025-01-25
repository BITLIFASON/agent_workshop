import os
from typing import Dict, Any
import asyncio
from dotenv import load_dotenv
from loguru import logger
from .parser_agent import ParserAgent
from .balance_control_agent import BalanceControlAgent
from .trading_agent import TradingAgent

class TradingSystem:
    def __init__(self, config: Dict[str, Any]):
        """Initialize trading system with configuration"""
        self.config = config
        self.openai_api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")

        # Initialize agents
        self.initialize_agents()

    def initialize_agents(self):
        """Initialize all trading system agents"""
        try:
            # Initialize Trading Agent
            self.trading_agent = TradingAgent(
                name="trading_executor",
                bybit_config=self.config["bybit"],
                openai_api_key=self.openai_api_key
            )

            # Initialize Balance Control Agent
            self.balance_control_agent = BalanceControlAgent(
                name="balance_controller",
                config={
                    "management_api": self.config["management_api"],
                    "database": self.config["database"],
                    "bybit": self.config["bybit"]
                },
                trading_callback=self.trading_agent.execute_trade,
                openai_api_key=self.openai_api_key
            )

            # Initialize Parser Agent
            self.parser_agent = ParserAgent(
                name="signal_parser",
                api_id=self.config["telegram"]["api_id"],
                api_hash=self.config["telegram"]["api_hash"],
                api_session_token=self.config["telegram"]["session_token"],
                channel_url=self.config["telegram"]["channel_url"],
                message_callback=self.process_signal,
                openai_api_key=self.openai_api_key
            )

            logger.info("All agents initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            raise

    async def process_signal(self, signal_data: dict):
        """Process trading signal through the system"""
        try:
            logger.info(f"Processing signal: {signal_data}")
            
            # Validate trade through balance control
            is_valid = await self.balance_control_agent.validate_trade(signal_data)
            
            if is_valid:
                logger.info("Signal validated, proceeding with execution")
                await self.balance_control_agent.process_signal(signal_data)
            else:
                logger.warning("Signal validation failed")

        except Exception as e:
            logger.error(f"Error processing signal: {e}")

    async def initialize(self) -> bool:
        """Initialize the trading system"""
        try:
            logger.info("Initializing trading system...")

            # Initialize all agents
            initialization_tasks = [
                self.parser_agent.initialize(),
                self.balance_control_agent.initialize(),
                self.trading_agent.initialize()
            ]
            
            results = await asyncio.gather(*initialization_tasks)
            
            if not all(results):
                logger.error("Failed to initialize all agents")
                return False

            logger.info("Trading system initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing trading system: {e}")
            return False

    async def start(self):
        """Start the trading system"""
        try:
            logger.info("Starting trading system...")

            # Start agent execution loops
            agent_tasks = [
                self.parser_agent.run(),
                self.balance_control_agent.run(),
                self.trading_agent.run()
            ]

            logger.info("Trading system started successfully")
            await asyncio.gather(*agent_tasks)

        except Exception as e:
            logger.error(f"Error starting trading system: {e}")
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the trading system"""
        try:
            logger.info("Shutting down trading system...")
            
            # Cleanup all agents
            cleanup_tasks = [
                self.parser_agent.cleanup(),
                self.balance_control_agent.cleanup(),
                self.trading_agent.cleanup()
            ]
            
            await asyncio.gather(*cleanup_tasks)
            logger.info("Trading system shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
