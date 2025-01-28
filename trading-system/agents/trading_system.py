import os
from typing import Dict, Any
import asyncio
from pydantic import BaseModel, Field, ConfigDict
from loguru import logger
from .parser_agent import ParserAgent
from .balance_control_agent import BalanceControlAgent
from .trading_agent import TradingAgent


class TelegramConfig(BaseModel):
    """Telegram configuration model"""
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API hash")
    session_token: str = Field(..., description="Telegram session token")
    channel_url: str = Field(..., description="Telegram channel URL")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class BybitConfig(BaseModel):
    """Bybit configuration model"""
    api_key: str = Field(..., description="Bybit API key")
    api_secret: str = Field(..., description="Bybit API secret")
    demo_mode: bool = Field(default=True, description="Whether to use testnet")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class DatabaseConfig(BaseModel):
    """Database configuration model"""
    host: str = Field(..., description="Database host")
    port: str = Field(..., description="Database port")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")
    database: str = Field(..., description="Database name")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class ManagementAPIConfig(BaseModel):
    """Management API configuration model"""
    host: str = Field(..., description="Management API host")
    port: str = Field(..., description="Management API port")
    token: str = Field(..., description="Management API token")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
    )


class LLMConfig(BaseModel):
    """LLM configuration model"""
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="LLM model name")
    api_key: str = Field(..., description="LLM API key")
    temperature: float = Field(default=0.7, description="LLM temperature")

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True
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
            self._create_agents()
        except Exception as e:
            logger.error(f"Error initializing trading system: {e}")
            raise

    def _create_agents(self):
        """Create agent instances without initialization"""
        try:
            # Create Trading Agent first since it's used as a callback
            self.trading_agent = TradingAgent(
                name="trading_executor",
                bybit_config=self.config.bybit.model_dump(),
                llm_config=self.config.llm.model_dump()
            )

            # Create Balance Control Agent with trading callback
            self.balance_control_agent = BalanceControlAgent(
                name="balance_controller",
                config={
                    "management_api": self.config.management_api.model_dump(),
                    "database": self.config.database.model_dump(),
                    "bybit": self.config.bybit.model_dump()
                },
                trading_callback=self.trading_agent.execute_trade,
                llm_config=self.config.llm.model_dump()
            )

            # Create Parser Agent last since it depends on Balance Control Agent
            self.parser_agent = ParserAgent(
                name="signal_parser",
                telegram_config=self.config.telegram.model_dump(),
                message_callback=self.process_signal,
                llm_config=self.config.llm.model_dump()
            )

        except Exception as e:
            logger.error(f"Error creating agents: {e}")
            raise

    async def process_signal(self, signal_data: dict):
        """Process trading signal through the system"""
        try:
            logger.info(f"Processing signal: {signal_data}")
            await self.balance_control_agent.process_signal(signal_data)
        except Exception as e:
            logger.error(f"Error processing signal: {e}")

    async def initialize(self) -> bool:
        """Initialize the trading system"""
        try:
            logger.info("Initializing trading system...")

            # Initialize agents in correct order
            # Trading Agent first since it's used by Balance Control Agent
            if not await self.trading_agent.initialize():
                logger.error("Failed to initialize Trading Agent")
                return False

            # Balance Control Agent next since it depends on Trading Agent
            if not await self.balance_control_agent.initialize():
                logger.error("Failed to initialize Balance Control Agent")
                return False

            # Parser Agent last since it triggers the whole chain
            if not await self.parser_agent.initialize():
                logger.error("Failed to initialize Parser Agent")
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

            # Wait for all agents to complete or fail
            await asyncio.gather(*agent_tasks)
            logger.info("Trading system started successfully")

        except Exception as e:
            logger.error(f"Error starting trading system: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Shutdown the trading system"""
        try:
            logger.info("Shutting down trading system...")
            
            # Cleanup agents in reverse order of initialization
            await self.parser_agent.cleanup()
            await self.balance_control_agent.cleanup()
            await self.trading_agent.cleanup()
            
            logger.info("Trading system shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
