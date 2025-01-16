import os
import asyncio

from loguru import logger
from ..agents.trading_agent import TradingAgent
from ..agents.config import load_config


async def execution_callback(result):
    """Callback function for trade execution results"""
    logger.info(f"Trade execution result: {result}")

async def main():

    # Load configuration
    config = load_config()

    # Bybit configuration
    bybit_config = {
        "api_key": os.getenv("BYBIT_API_KEY"),
        "api_secret": os.getenv("BYBIT_API_SECRET"),
        "demo_mode": os.getenv("BYBIT_DEMO_MODE", "True")
    }

    # Initialize trading agent
    trading_agent = TradingAgent(
        name="bybit_trader",
        bybit_config=config['bybit'],
        execution_callback=execution_callback
    )

    # Initialize and run agent
    if await trading_agent.initialize():
        try:
            # Example trade
            test_trade = {
                "symbol": "BTCUSDT",
                "action": "buy",
                "qty": 0.001,
                "price": 100.0
            }

            await trading_agent.execute_trade(test_trade)
            await trading_agent.run()

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await trading_agent.cleanup()
    else:
        logger.error("Failed to initialize trading agent")

if __name__ == "__main__":
    asyncio.run(main())
