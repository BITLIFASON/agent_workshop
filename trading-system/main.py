import asyncio
from loguru import logger
from agents.trading_system import TradingSystem
from agents.utils.config import load_config
from agents.utils.logger import setup_logging

async def main():
    """Main entry point"""
    try:
        # Setup logging first
        setup_logging()

        # Load configuration
        config = load_config()
        
        # Initialize trading system
        trading_system = TradingSystem(config)
        await trading_system.initialize()
        
        # Run the system
        await trading_system.start()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        if 'trading_system' in locals():
            await trading_system.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System shutdown requested")
    except Exception as e:
        logger.error(f"System error: {e}")
        raise
