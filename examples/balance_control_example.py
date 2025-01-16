import os
import asyncio
from loguru import logger
from ..agents.balance_control_agent import BalanceControlAgent
from ..agents.config import load_config


async def trading_callback(trade_signal):
    """Callback function for trade execution"""
    logger.info(f"Executing trade: {trade_signal}")

async def main():

    # Load configuration
    config = load_config()

    # Initialize balance control agent
    balance_control = BalanceControlAgent(
        name="balance_controller",
        config=config,
        trading_callback=trading_callback
    )

    # Initialize and run agent
    if await balance_control.initialize():
        try:
            # Example signal
            test_signal = {
                "symbol": "BTCUSDT",
                "action": "buy",
                "price": 100.0
            }

            await balance_control.process_signal(test_signal)
            await balance_control.run()

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await balance_control.cleanup()
    else:
        logger.error("Failed to initialize balance control agent")

if __name__ == "__main__":
    asyncio.run(main())
