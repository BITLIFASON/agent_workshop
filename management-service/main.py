import os
import uvicorn
from loguru import logger
from fastapi import FastAPI, HTTPException
from pybit.unified_trading import HTTP

from routes import setup_routes
from utils import validate_token

app = FastAPI()


@app.on_event("startup")
async def startup():
    """
    Sets up the app state and initializes a Bybit client.

    Returns:
        None
    Raises:
        Exception: If an error occurs during startup.
    """
    try:
        # Initialize Bybit client
        app.state.bybit_client = HTTP(
            testnet=False,
            api_key=os.getenv('BYBIT_API_KEY'),
            api_secret=os.getenv('BYBIT_API_SECRET'),
            demo=os.getenv('BYBIT_DEMO_MODE', 'True') == 'True'
        )
        logger.info("Bybit client successfully initialized")

        # Initialize system state
        app.state.trading_state = {
            "price_limit": 3.,
            "fake_balance": 0.,
            "num_available_lots": 0,
            "enable_trading_system": 'disable',
        }
        logger.info("System state initialized")

    except Exception as e:
        logger.error(f"Failed to initialize Bybit client: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    """
    Closes the connection to Bybit.
    """
    if hasattr(app.state, 'bybit_client'):
        app.state.bybit_client.session.close()

setup_routes(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("MANAGEMENT_API_PORT", 8080)))
