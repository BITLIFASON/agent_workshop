import os
import asyncpg
from fastapi import HTTPException
from loguru import logger

MANAGEMENT_API_TOKEN = os.getenv("MANAGEMENT_API_TOKEN", "")

def validate_token(api_key: str):
    """
    Validates the provided API token.

    Args:
        api_key (str): The API token provided in the request.

    Raises:
        HTTPException: If the API token is invalid or missing.

    Returns:
        None
    """
    if api_key != MANAGEMENT_API_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API token"
        )

async def get_pg_connection():
    """
    Creates and returns a connection to the PostgreSQL database.

    Returns:
        asyncpg.connection.Connection: A connection to the PostgreSQL database.

    Raises:
        Exception: If an error occurs during connection.
    """
    try:
        conn = await asyncpg.connect(
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB'),
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT'),
        )
        logger.info("Successfully connected to PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise

async def get_real_balance(bybit_client):
    """
    Get the real balance from Bybit.

    Args:
        bybit_client (HTTP): The Bybit client.

    Returns:
        dict: Real balance data.

    Raises:
        Exception: If an error occurs during fetching.
    """
    real_balance = float(
        bybit_client.get_wallet_balance(accountType="UNIFIED", coin="USDT")["result"]["list"][0]["coin"][0]["walletBalance"]
    )
    return {"total_real_balance": real_balance}

async def fetch_active_lots():
    """
    Fetch active lots from the PostgreSQL database.

    Returns:
        list[dict]: List of active lots.

    Raises:
        Exception: If an error occurs during fetching.
    """
    conn = await get_pg_connection()
    try:
        rows = await conn.fetch("SELECT * FROM active_lots;")
        return [{"id": row["id"], "symbol": row["symbol"], "price": row["price"], "created_at": row["created_at"]} for row in rows]
    finally:
        await conn.close()
