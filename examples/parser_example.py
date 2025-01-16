import os
import asyncio
from loguru import logger
from ..agents.parser_agent import ParserAgent
from ..agents.config import load_config


async def signal_callback(signal):
    """Callback function for received signals"""
    logger.info(f"Received signal: {signal}")

async def main():

    # Load configuration
    config = load_config()

    # Initialize parser agent
    parser = ParserAgent(
        name="signal_parser",
        api_id=config['telegram']['api_id'],
        api_hash=config['telegram']['api_hash'],
        channel_url=config['telegram']['channel_url'],
        message_callback=signal_callback
    )

    # Initialize and run agent
    if await parser.initialize():
        try:
            await parser.run()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await parser.cleanup()
    else:
        logger.error("Failed to initialize parser agent")

if __name__ == "__main__":
    asyncio.run(main())
