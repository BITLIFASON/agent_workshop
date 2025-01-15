import os
import sys
import re
from datetime import timedelta
from telethon import TelegramClient, events
from typing import Union
from loguru import logger
import asyncio

from utils import RabbitClient, init_telegram_client


MAX_RETRIES_TELEGRAM = os.getenv('MAX_RETRIES_TELEGRAM')


def parse_signal(text: str) -> Union[dict, None]:
    """
    Parse a trading signal from the message text.

    Args:
        text (str): The text message containing the signal.

    Returns:
        dict or None: Parsed signal data.
    Raises:
        Exception: If an error occurs during parsing.
    """
    buy_pattern = re.compile(r'.\s(\w+)\s+BUY LONG PRICE:\s+(\d+\.\d+)')
    sell_pattern = re.compile(r'.\s(\w+)\s+..\sPROFIT:\s+(.\s*\d+\.\d+)\%\sCLOSE LONG PRICE:\s+(\d+\.\d+)')

    match_buy = buy_pattern.search(text)
    if match_buy:
        symbol = match_buy.group(1)
        price = float(match_buy.group(2))
        return {"symbol": symbol,
                "action": "buy",
                "price_buy": price}


    match_sell = sell_pattern.search(text)
    if match_sell:
        symbol = match_sell.group(1)
        profit_percentage = float(match_sell.group(2).replace(' ', ''))
        price = float(match_sell.group(3))
        return {"symbol": symbol,
                "action": "sell",
                "price_sell": price,
                "profit_percentage": profit_percentage}

    return None

async def start_listening(telegram_client: TelegramClient, rabbit_client):
    """
    Start listening for new messages on the specified Telegram channel and publish them to RabbitMQ.

    Args:
        telegram_client (TelegramClient): The Telegram client.
        rabbit_client (RabbitClient): The RabbitMQ client.

    Returns:
        None
    Raises:
        Exception: If an error occurs during setup.
    """

    try:
        @telegram_client.on(events.NewMessage(chats=[os.getenv('CHANNEL_URL', '')]))
        async def new_message_handler(event):
            message = event.message
            signal = parse_signal(message.message)
            if signal:
                process_signal = {
                    "symbol": signal["symbol"],
                    "price_buy": signal.get("price_buy", None),
                    "price_sell": signal.get("price_sell", None),
                    "timestamp": message.date.replace(tzinfo=None) + timedelta(hours=3),
                    "profit_percentage": signal.get("profit_percentage", None)
                }
                await rabbit_client.publish(process_signal)

        if not telegram_client.is_connected():
            max_retries_telegram = 0
            while True:
                logger.warning("Telegram connection lost, trying to reconnect...")
                telegram_client = await init_telegram_client()
                await asyncio.sleep(10)
                if max_retries_telegram == MAX_RETRIES_TELEGRAM:
                    raise Exception("Maximum retries reached")
                max_retries_telegram += 1

        await telegram_client.run_until_disconnected()

    except Exception as e:
        logger.error(f"Error in Telegram listener: {e}")
        raise

async def main():
    """
    Main function to run the parser service.

    Returns:
        None
    Raises:
        Exception: If an error occurs during startup.
    """

    try:
        telegram_client = await init_telegram_client()
        logger.info("Telegram client successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram client: {e}")
        sys.exit(1)

    try:
        rabbit_client = RabbitClient()
        await rabbit_client.connect()
        logger.info("RabbitMQ client successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize RabbitMQ client: {e}")
        sys.exit(1)

    try:
        logger.info("Starting parser service...")
        await start_listening(telegram_client, rabbit_client)
    finally:
        await telegram_client.disconnect()
        logger.info("Telegram client disconnected.")

        await rabbit_client.close()
        logger.info("RabbitMQ client disconnected.")

        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
