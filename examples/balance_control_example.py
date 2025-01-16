import os
import asyncio
from dotenv import load_dotenv
from loguru import logger
from agents.balance_control_agent import BalanceControlAgent

async def trading_callback(trade_signal):
    """Callback function for trade execution"""
    logger.info(f"Executing trade: {trade_signal}")

async def main():
    # Load environment variables
    load_dotenv()

    # Database configuration
    db_config = {
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "database": os.getenv("POSTGRES_DB"),
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT")
    }

    # Management API configuration
    management_api_config = {
        "host": os.getenv("MANAGEMENT_API_HOST"),
        "port": os.getenv("MANAGEMENT_API_PORT"),
        "token": os.getenv("MANAGEMENT_API_TOKEN")
    }

    # Initialize balance control agent
    balance_control = BalanceControlAgent(
        name="balance_controller",
        db_config=db_config,
        management_api_config=management_api_config,
        trading_callback=trading_callback
    )

    # Initialize and run agent
    if await balance_control.initialize():
        try:
            # Example signal
            test_signal = {
                "symbol": "BTCUSDT",
                "action": "buy",
                "price": 50000.0
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
