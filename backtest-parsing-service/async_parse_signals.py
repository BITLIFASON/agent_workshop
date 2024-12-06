import os
import re
from datetime import datetime, timedelta, timezone
from typing import Union
from telethon import TelegramClient, events
from telethon.tl.types import Message
import asyncio
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

# Загрузка переменных окружения
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
CHANNEL_URL = os.getenv('CHANNEL_URL', '')
COUNT_DAYS = int(os.getenv('COUNT_DAYS', 0))

# Настройки базы данных
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres/{POSTGRES_DB}"

# Флаг удаления таблицы
DROP_TABLE = os.getenv('DROP_TABLE', 'false').lower() == 'true'

# Создаем асинхронный движок для работы с базой данных
async_engine = create_async_engine(DATABASE_URL, echo=False)

# Запросы к базе
create_table_query = """
    CREATE TABLE IF NOT EXISTS signals (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(50) NOT NULL,
        price_buy NUMERIC(19, 8),
        buy_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        price_sell NUMERIC(19, 8),
        sell_timestamp TIMESTAMP,
        auto_profit_percentage NUMERIC(5, 2),
        manual_profit_percentage NUMERIC(5, 2)
    )
"""
active_buy_query = text("""
                SELECT * FROM signals
                WHERE symbol = :symbol AND price_sell IS NULL
            """)
insert_query = text("""
    INSERT INTO signals (symbol, price_buy, buy_timestamp, price_sell, sell_timestamp, auto_profit_percentage, manual_profit_percentage)
    VALUES (:symbol, :price_buy, :timestamp, NULL, NULL, NULL, NULL)
""")
update_query = text("""
    UPDATE signals
    SET
        price_sell = :price_sell,
        sell_timestamp = :timestamp,
        auto_profit_percentage = :profit_percentage,
        manual_profit_percentage = (:price_sell / price_buy - 1) * 100
    WHERE symbol = :symbol AND price_sell IS NULL
""")

async def init_db():
    """Инициализация схемы базы данных."""
    async with async_engine.begin() as connection:
        try:
            if DROP_TABLE:
                await connection.execute(text("DROP TABLE IF EXISTS signals"))
                logger.info("Таблица удалена.")
            await connection.execute(text(create_table_query))
            logger.info("Схема базы данных успешно инициализирована.")
        except SQLAlchemyError as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise


async def init_client() -> TelegramClient:
    """Инициализация клиента Telegram."""
    client = TelegramClient("backtesting_session",
                            api_id=API_ID,
                            api_hash=API_HASH,)
    await client.start()
    logger.info("Telegram клиент успешно инициализирован.")
    return client


def parse_signal(text: str) -> Union[dict, None]:
    """Разбор торгового сигнала из текста сообщения."""

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


async def save_signal(signal: dict):
    """Сохранение сигнала в базе данных."""

    async with async_engine.connect() as connection:
        try:
            if signal.get("price_buy") is not None:
                result = await connection.execute(active_buy_query,
                                                  {"symbol": signal["symbol"]})
                active_buy_flag = result.scalar_one_or_none()
                if active_buy_flag:
                    logger.info(f"Активная покупка для {signal['symbol']} уже существует. Пропуск нового сигнала на покупку.")
                else:
                    await connection.execute(insert_query, signal)
            elif signal.get("price_sell") is not None:
                await connection.execute(update_query, signal)
            await connection.commit()
            logger.info(f"Сигнал сохранен: {signal}")
        except SQLAlchemyError as e:
            logger.error(f"Ошибка сохранения сигнала: {e}")


async def parse_recent_signals(client: TelegramClient):
    """Парсинг сигналов из Telegram за последние N дней."""
    logger.info(f"Начинается парсинг сообщений за последние {COUNT_DAYS} дней")

    # Определяем дату начала
    timezone_offset = 3.0
    tzinfo = timezone(timedelta(hours=timezone_offset))
    from_date = datetime.now(tzinfo) - timedelta(days=COUNT_DAYS)
    logger.info(f"Парсинг сообщений начиная с: {from_date}")

    # Получаем сущность канала
    entity = await client.get_entity(CHANNEL_URL)

    # Асинхронная загрузка старых сообщений
    async for message in client.iter_messages(entity, offset_date=from_date, reverse=True):
        if isinstance(message, Message) and message.message:
            signal = parse_signal(message.message)
            if signal:
                process_signal = {
                    "symbol": signal["symbol"],
                    "price_buy": signal.get("price_buy", None),
                    "price_sell": signal.get("price_sell", None),
                    "timestamp": message.date.replace(tzinfo=None) + timedelta(hours=3),
                    "profit_percentage": signal.get("profit_percentage", None)
                }
                await save_signal(process_signal)

    logger.info("Завершен парсинг старых сообщений.")



async def main():
    """Основная функция для запуска скрипта."""
    await init_db()
    client = await init_client()
    try:
        await parse_recent_signals(client)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
