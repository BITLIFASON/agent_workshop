import asyncio
from loguru import logger
from agents.trading_system import TradingSystem
from agents.utils.config import load_config
from agents.utils.logger import setup_logging
from parser import TelegramParser

async def main():
    """Main entry point"""
    try:
        # Setup logging first
        setup_logging()

        # Load configuration
        config = load_config()

        parser = TelegramParser(config['telegram'])
        trading_system = TradingSystem(config)

        # Initialize trading system
        initialized = await trading_system.initialize()
        crew = await trading_system.get_crew()
        await parser.set_crew(crew)
        
        # Run the system
        if initialized:
            await parser.start()
            await trading_system.start()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        if 'trading_system' in locals():
            await parser.cleanup()
            await trading_system.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System shutdown requested")
    except Exception as e:
        logger.error(f"System error: {e}")
        raise
