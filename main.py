import asyncio
import signal
from dotenv import load_dotenv
from loguru import logger
from agents.trading_system import TradingSystem
from agents.config import load_config
from agents.utils.logger import setup_logging

async def main():
    # Setup logging first
    setup_logging()

    try:

        # Create trading system
        system = TradingSystem(load_config())

        # Initialize system
        if not await system.initialize():
            logger.error("Failed to initialize trading system")
            return

        # Handle shutdown signals
        def handle_shutdown():
            logger.info("Received shutdown signal")
            asyncio.create_task(system.shutdown())

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, handle_shutdown)

        # Start trading system
        logger.info("Starting trading system")
        await system.start()

    except Exception as e:
        logger.error(f"Critical error in main loop: {e}")
        raise
    finally:
        logger.info("Shutting down trading system")
        await system.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
