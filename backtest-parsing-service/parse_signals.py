import os
import re
from datetime import datetime, timedelta
from typing import Union
from telethon.sync import TelegramClient
from telethon.tl.types import Message
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Загрузка переменных окружения
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
CHANNEL_URL = os.getenv('CHANNEL_URL', '')
COUNT_DAYS = int(os.getenv('COUNT_DAYS', 0))

# Настройки базы данных
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres/{POSTGRES_DB}"

# Флаг удаления таблицы
DROP_TABLE = os.getenv('DROP_TABLE', 'false').lower() == 'true'

# Создаем синхронный движок для работы с базой данных
engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Инициализация схемы базы данных."""
    with engine.connect() as connection:
        try:
            if DROP_TABLE:
                connection.execute(text("DROP TABLE IF EXISTS signals"))
                connection.commit()
                logger.info("Таблица удалена.")
            create_table_query = """
            CREATE TABLE IF NOT EXISTS signals (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(50) NOT NULL,
                action VARCHAR(5) NOT NULL CHECK (action IN ('buy', 'sell')),
                price NUMERIC(19, 8),
                profit_percentage NUMERIC(5, 2),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            connection.execute(text(create_table_query))
            connection.commit()
            logger.info("Схема базы данных успешно инициализирована.")
        except SQLAlchemyError as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise


def parse_signal(text: str) -> Union[dict, None]:
    """Разбор торгового сигнала из текста сообщения."""

    buy_pattern = re.compile(r'.\s(\w+)\s+BUY LONG PRICE:\s+(\d+\.\d+)')
    sell_pattern = re.compile(r'.\s(\w+)\s+..\sPROFIT:\s+(.\s*\d\.\d+)\%\sCLOSE LONG PRICE:\s+(\d+\.\d+)')

    match_buy = buy_pattern.search(text)
    if match_buy:
        symbol = match_buy.group(1)
        price = float(match_buy.group(2))
        return {"symbol": symbol,
                "action": "buy",
                "price": price}

    match_sell = sell_pattern.search(text)
    if match_sell:
        symbol = match_sell.group(1)
        profit_percentage = float(match_sell.group(2).replace(' ', ''))
        price = float(match_sell.group(3))
        return {"symbol": symbol,
                "action": "sell",
                "price": price,
                "profit_percentage": profit_percentage}

    return None


def save_signal(signal: dict, timestamp: datetime):
    """Сохранение сигнала в базе данных."""

    with engine.connect() as connection:
        try:
            insert_query = text("""
                INSERT INTO signals (symbol, action, price, profit_percentage, timestamp)
                VALUES (:symbol, :action, :price, :profit_percentage, :timestamp)
            """)
            connection.execute(
                insert_query,
                {
                    "symbol": signal["symbol"],
                    "action": signal["action"],
                    "price": signal.get("price"),
                    "profit_percentage": signal.get("profit_percentage", None),
                    "timestamp": timestamp,
                },
            )
            connection.commit()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка сохранения сигнала: {e}")


def parse_recent_signals(client: TelegramClient):
    """Парсинг сигналов из Telegram за последние N дней."""
    logger.info(f"Начинается парсинг сообщений за последние {COUNT_DAYS} дней")

    # Определяем дату начала
    from_date = datetime.now() - timedelta(days=COUNT_DAYS)
    logger.info(f"Парсинг сообщений начиная с: {from_date}")

    entity = client.get_entity(CHANNEL_URL)

    # Загрузка старых сообщений
    for message in client.iter_messages(entity, offset_date=from_date, reverse=True):
        print(message)
        if isinstance(message, Message) and message.message:
            signal = parse_signal(message.message)
            if signal:
                message.date += timedelta(hours=3)
                save_signal(signal, message.date)
                logger.info(f"Сигнал из истории сохранен: {signal} с датой: {message.date}")

    logger.info("Завершен парсинг старых сообщений.")


def main():
    """Основная функция для запуска скрипта."""
    init_db()
    client = TelegramClient("backtesting_session", API_ID, API_HASH)
    client.start()
    logger.info("Telegram клиент успешно инициализирован.")

    try:
        parse_recent_signals(client)
    finally:
        client.disconnect()
        logger.info("Клиент Telegram отключен.")


if __name__ == "__main__":
    main()
