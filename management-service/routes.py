from fastapi import APIRouter, HTTPException, Depends, Request
from loguru import logger
from utils import fetch_active_lots, validate_token

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@router.get("/get_system_status")
async def api_get_system_status(request: Request, api_key: str):
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
        return {"system_status": request.app.state.trading_state["enable_trading_system"]}
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch system status: {str(e)}")

@router.get("/set_system_status/{system_status}")
async def api_set_system_status(system_status: str, request: Request, api_key: str):
    """
    Set the current system status.

    Args:
        system_status (str): The new system status. Must be either 'enable' or 'disable'.
        api_key (str): The API token for authorization.

    Returns:
        dict: Status of the set operation.

    Raises:
        HTTPException: If system_status is invalid or if an error occurs during setting.
    """
    if system_status not in ['enable', 'disable']:
        raise HTTPException(
            status_code=400, 
            detail="Invalid system status. Must be either 'enable' or 'disable'."
        )
        
    try:
        validate_token(api_key)
        request.app.state.trading_state["enable_trading_system"] = system_status
        logger.info(f"Set system status: {system_status}")
        return {"status": "System status set", "system_status": system_status}
    except Exception as e:
        logger.error(f"Error setting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set system status: {str(e)}")

@router.get("/get_fake_balance")
async def api_get_fake_balance(request: Request, api_key: str):
    """
    Get the fake balance from the system state.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        dict: Fake balance data.
    """
    validate_token(api_key)
    return {"fake_balance": request.app.state.trading_state["fake_balance"]}

@router.post("/set_fake_balance/{fake_balance}")
async def api_set_fake_balance(fake_balance: float, request: Request, api_key: str):
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
        request.app.state.trading_state["fake_balance"] = fake_balance
        logger.info(f"Set fake balance: {fake_balance}")
        return {"status": "Fake balance set", "fake_balance": fake_balance}
    except Exception as e:
        logger.error(f"Error setting fake balance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set fake balance: {str(e)}")

@router.get("/get_price_limit")
async def api_get_price_limit(request: Request, api_key: str):
    """
    Get the price limit from the system state.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        dict: Price limit data.
    """
    validate_token(api_key)
    return {"price_limit": request.app.state.trading_state["price_limit"]}

@router.post("/set_price_limit/{price_limit}")
async def api_set_price_limit(price_limit: float, request: Request, api_key: str):
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
        request.app.state.trading_state["price_limit"] = price_limit
        logger.info(f"Set price limit: {price_limit}")
        return {"status": "Price limit set", "price_limit": price_limit}
    except Exception as e:
        logger.error(f"Error setting price limit: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set price limit: {str(e)}")

@router.get("/get_num_available_lots")
async def api_get_num_available_lots(request: Request, api_key: str):
    """
    Get the number of available lots from the system state.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        dict: Number of available lots data.
    """
    validate_token(api_key)
    return {"num_available_lots": request.app.state.trading_state["num_available_lots"]}

@router.post("/set_num_available_lots/{num_available_lots}")
async def api_set_num_available_lots(num_available_lots: int, request: Request, api_key: str):
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
        request.app.state.trading_state["num_available_lots"] = num_available_lots
        logger.info(f"Set number available_lots: {num_available_lots}")
        return {"status": "Number available lots set", "num_available_lots": num_available_lots}
    except Exception as e:
        logger.error(f"Error setting number available lots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set number available_lots: {str(e)}")

@router.get("/get_active_lots")
async def api_get_active_lots(request: Request, api_key: str):
    """
    Get the active lots from the system state.

    Args:
        request (Request): The FastAPI request object.
        api_key (str): The API token for authorization.

    Returns:
        list: List of active lots data.
    """
    try:
        validate_token(api_key)
        return await fetch_active_lots(request)
    except Exception as e:
        logger.error(f"Error fetching active lots: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch active lots: {str(e)}")

def setup_routes(app):
    """
    Setup API routes.
    """
    app.include_router(router)
