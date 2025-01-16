import os
import asyncio
from dotenv import load_dotenv
from loguru import logger
from agents.trading_agent import TradingAgent

async def execution_callback(result):
    """Callback function for trade execution results"""
    logger.info(f"Trade execution result: {result}")

async def main():
    # Load environment variables
    load_dotenv()

    # Bybit configuration
    bybit_config = {
        "api_key": os.getenv("BYBIT_API_KEY"),
        "api_secret": os.getenv("BYBIT_API_SECRET"),
        "demo_mode": os.getenv("BYBIT_DEMO_MODE", "True")
    }

    # Initialize trading agent
    trading_agent = TradingAgent(
        name="bybit_trader",
        bybit_config=bybit_config,
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
                "price": 50000.0  # For reference only, using market orders
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
