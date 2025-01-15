from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from utils import get_real_balance, fetch_active_lots, validate_token

router = APIRouter()

app_state = {
    "price_limit": 3.,
    "fake_balance": 0.,
    "num_available_lots": 0,
    "enable_trading_system": 'disable',
}

@router.get("/get_system_status")
async def api_get_system_status(api_key: str):
    """
    Get the current system status.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        dict: Current system status.

    Raises:
        HTTPException: If an error occurs during retrieval.
    """
    try:
        validate_token(api_key)
        return {"system_status": app_state["enable_trading_system"]}
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch system status: {str(e)}")

@router.get("/set_system_status/{system_status}")
async def api_set_system_status(system_status, api_key: str):
    """
    Set the current system status.

    Args:
        system_status (str): The new system status.
        api_key (str): The API token for authorization.

    Returns:
        dict: Status of the set operation.

    Raises:
        HTTPException: If an error occurs during setting.
    """
    try:
        validate_token(api_key)
        app_state["enable_trading_system"] = system_status
        logger.info(f"Set system status: {app_state['enable_trading_system']}")
        return {"status": "System status set", "system_status": system_status}
    except Exception as e:
        logger.error(f"Error setting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set system status: {str(e)}")

@router.get("/get_real_balance")
async def api_get_real_balance(bybit_client, api_key: str):
    """
    Get the real balance from Bybit.

    Args:
        bybit_client (HTTP): The Bybit client.
        api_key (str): The API token for authorization.

    Returns:
        dict: Real balance data.

    Raises:
        HTTPException: If an error occurs during fetching.
    """
    try:
        validate_token(api_key)
        return await get_real_balance(bybit_client)
    except Exception as e:
        logger.error(f"Error fetching real balance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch real balance: {str(e)}")

@router.get("/get_fake_balance")
async def api_get_fake_balance(api_key: str):
    """
    Get the fake balance from the system state.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        dict: Fake balance data.
    """
    validate_token(api_key)
    return {"fake_balance": app_state["fake_balance"]}

@router.post("/set_fake_balance/{fake_balance}")
async def api_set_fake_balance(fake_balance: float, api_key: str):
    """
    Set the fake balance in the system state.

    Args:
        fake_balance (float): The new fake balance.
        api_key (str): The API token for authorization.

    Returns:
        dict: Status of the set operation.
    """
    try:
        validate_token(api_key)
        app_state["fake_balance"] = fake_balance
        logger.info(f"Set fake balance: {app_state['fake_balance']}")
        return {"status": "Fake balance set", "fake_balance": fake_balance}
    except Exception as e:
        logger.error(f"Error setting fake balance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set fake balance: {str(e)}")

@router.get("/get_price_limit")
async def api_get_price_limit(api_key: str):
    """
    Get the price limit from the system state.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        dict: Price limit data.
    """
    validate_token(api_key)
    return {"price_limit": app_state["price_limit"]}

@router.post("/set_price_limit/{price_limit}")
async def api_set_price_limit(price_limit: float, api_key: str):
    """
    Set the price limit in the system state.

    Args:
        price_limit (float): The new price limit.
        api_key (str): The API token for authorization.

    Returns:
        dict: Status of the set operation.
    """
    try:
        validate_token(api_key)
        app_state["price_limit"] = price_limit
        logger.info(f"Set price limit: {app_state['price_limit']}")
        return {"status": "Price limit set", "price_limit": price_limit}
    except Exception as e:
        logger.error(f"Error setting price limit: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set price limit: {str(e)}")

@router.get("/get_num_available_lots")
async def api_get_num_available_lots(api_key: str):
    """
    Get the number of available lots from the system state.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        dict: Number of available lots data.
    """
    validate_token(api_key)
    return {"num_available_lots": app_state["num_available_lots"]}

@router.post("/set_num_available_lots/{num_available_lots}")
async def api_set_num_available_lots(num_available_lots: int, api_key: str):
    """
    Set the number of available lots in the system state.

    Args:
        num_available_lots (int): The new number of available lots.
        api_key (str): The API token for authorization.

    Returns:
        dict: Status of the set operation.
    """
    try:
        validate_token(api_key)
        app_state["num_available_lots"] = num_available_lots
        logger.info(f"Set number available_lots: {app_state['num_available_lots']}")
        return {"status": "Number available lots set", "num_available_lots": num_available_lots}
    except Exception as e:
        logger.error(f"Error setting number available lots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set number available_lots: {str(e)}")

@router.get("/get_active_lots")
async def api_get_active_lots(api_key: str):
    """
    Get the active lots from the system state.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        list: List of active lots data.
    """
    try:
        validate_token(api_key)
        return await fetch_active_lots()
    except Exception as e:
        logger.error(f"Error fetching active lots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch active lots: {str(e)}")

def setup_routes(app):
    """
    Setup API routes.
    """
    app.include_router(router)