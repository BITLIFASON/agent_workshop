import os
import asyncio
from dotenv import load_dotenv
from loguru import logger
from agents.parser_agent import ParserAgent

async def signal_callback(signal):
    """Callback function for received signals"""
    logger.info(f"Received signal: {signal}")

async def main():
    # Load environment variables
    load_dotenv()

    # Initialize parser agent
    parser = ParserAgent(
        name="trading_parser",
        api_id=int(os.getenv("API_ID")),
        api_hash=os.getenv("API_HASH"),
        channel_url=os.getenv("CHANNEL_URL"),
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
