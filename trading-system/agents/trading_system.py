import asyncio
import aio_pika
import aiohttp
import asyncpg
from typing import Dict, Any
from loguru import logger
from .parser_agent import ParserAgent
from .balance_control_agent import BalanceControlAgent
from .trading_agent import TradingAgent

class TradingSystem:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize trading system with all agents

        Args:
            config: Configuration dictionary containing all necessary settings
        """
        self.config = config
        self.agents = {}
        self._setup_logger()
        self.max_connection_attempts = 3  # Максимальное кол-во попыток
        self.connection_retry_delay = 5    # Задержка между попытками в секундах

    def _setup_logger(self):
        """Setup system-wide logger"""
        logger.add(
            "logs/trading_system.log",
            rotation="500 MB",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        self.logger = logger.bind(system="trading_system")

    async def _wait_for_services(self):
        """Wait for dependent services to be ready"""

        # Wait for PostgreSQL
        attempt = 0
        while attempt < self.max_connection_attempts:
            try:
                conn = await asyncpg.connect(
                    user=self.config['database']['user'],
                    password=self.config['database']['password'],
                    database=self.config['database']['database'],
                    host=self.config['database']['host'],
                    port=self.config['database']['port']
                )
                await conn.close()
                self.logger.info("Successfully connected to PostgreSQL")
                break
            except Exception as e:
                attempt += 1
                if attempt >= self.max_connection_attempts:
                    raise Exception(f"Failed to connect to PostgreSQL after {self.max_connection_attempts} attempts: {e}")
                self.logger.warning(f"Waiting for PostgreSQL (attempt {attempt}/{self.max_connection_attempts}): {e}")
                await asyncio.sleep(self.connection_retry_delay)

        # Wait for Management API
        attempt = 0
        while attempt < self.max_connection_attempts:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"http://{self.config['management_api']['host']}:{self.config['management_api']['port']}/health"
                    async with session.get(url) as response:
                        if response.status == 200:
                            self.logger.info("Successfully connected to Management API")
                            break
                        else:
                            raise Exception(f"Management API returned status {response.status}")
            except Exception as e:
                attempt += 1
                if attempt >= self.max_connection_attempts:
                    raise Exception(f"Failed to connect to Management API after {self.max_connection_attempts} attempts: {e}")
                self.logger.warning(f"Waiting for Management API (attempt {attempt}/{self.max_connection_attempts}): {e}")
                await asyncio.sleep(self.connection_retry_delay)

    async def _init_database(self):
        """Initialize database tables"""
        try:
            # Create connection pool
            self.db_pool = await asyncpg.create_pool(
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                database=self.config['database']['database'],
                host=self.config['database']['host'],
                port=self.config['database']['port']
            )

            # Create tables
            async with self.db_pool.acquire() as conn:
                # Create active lots table
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS active_lots (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        qty DECIMAL NOT NULL,
                        price DECIMAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')

                # Create history lots table
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS history_lots (
                        id SERIAL PRIMARY KEY,
                        action VARCHAR(10) NOT NULL,
                        symbol VARCHAR(20) NOT NULL,
                        qty DECIMAL NOT NULL,
                        price DECIMAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')

            logger.info("Database tables initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    async def initialize(self):
        """Initialize all agents and establish connections"""
        try:

            # Verify connection to required services
            try:
                await self._wait_for_services()
            except Exception as e:
                raise Exception(f"Failed to connect to required services: {e}")

            # Initialize database
            try:
                await self._init_database()
            except Exception as e:
                raise Exception(f"Failed to initialize database: {e}")

            # Initialize Parser Agent
            self.agents['parser'] = ParserAgent(
                name="signal_parser",
                api_id=self.config['telegram']['api_id'],
                api_hash=self.config['telegram']['api_hash'],
                api_session_token=self.config['telegram']['api_session_token'],
                channel_url=self.config['telegram']['channel_url'],
                message_callback=self._handle_parsed_signal
            )

            # Initialize Balance Control Agent
            self.agents['balance_control'] = BalanceControlAgent(
                name="balance_controller",
                config=self.config,
                trading_callback=self._handle_trade_decision
            )

            # Initialize Trading Agent
            self.agents['trading'] = TradingAgent(
                name="trade_executor",
                bybit_config=self.config['bybit'],
                execution_callback=self._handle_trade_execution
            )

            # Initialize all agents
            for name, agent in self.agents.items():
                if not await agent.initialize():
                    raise Exception(f"Failed to initialize {name} agent")
                self.logger.info(f"Successfully initialized {name} agent")

            return True

        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return False

    async def _handle_parsed_signal(self, signal: Dict[str, Any]):
        """Handle signals from Parser Agent"""
        try:
            self.logger.info(f"Received trading signal: {signal}")
            await self.agents['balance_control'].process_signal(signal)
        except Exception as e:
            self.logger.error(f"Error handling parsed signal: {e}")

    async def _handle_trade_decision(self, trade_signal: Dict[str, Any]):
        """Handle trade decisions from Balance Control Agent"""
        try:
            self.logger.info(f"Received trade decision: {trade_signal}")
            await self.agents['trading'].execute_trade(trade_signal)
        except Exception as e:
            self.logger.error(f"Error handling trade decision: {e}")

    async def _handle_trade_execution(self, result: Dict[str, Any]):
        """Handle trade execution results"""
        self.logger.info(f"Trade execution result: {result}")

    async def start(self):
        """Start all agents"""
        try:
            # Create tasks for each agent
            tasks = []
            for name, agent in self.agents.items():
                tasks.append(asyncio.create_task(
                    agent.run(),
                    name=f"{name}_task"
                ))
            self.logger.info("All agents started")

            # Wait for all tasks
            await asyncio.gather(*tasks)

        except Exception as e:
            self.logger.error(f"Error in system operation: {e}")
            await self.shutdown()

    async def shutdown(self):
        """Shutdown all agents and cleanup"""
        for name, agent in self.agents.items():
            try:
                await agent.cleanup()
                self.logger.info(f"Successfully shutdown {name} agent")
            except Exception as e:
                self.logger.error(f"Error shutting down {name} agent: {e}")
