import os
from pybit.unified_trading import HTTP
import requests
from contextlib import contextmanager
from pika import ConnectionParameters, PlainCredentials, BlockingConnection
from loguru import logger
from typing import Tuple, Dict, Any
import psycopg2


@contextmanager
def get_db_connection():
    """
    Context manager for managing the database connection.

    Returns:
        psycopg2.connection: The database connection object.
    Raises:
        Exception: If an error occurs during connection.
    """
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', ''),
            user=os.getenv('POSTGRES_USER', ''),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432))
        )
        yield conn
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        raise
    finally:
        if conn:
            conn.close()


def initialize_active_lots_table():
    """
    Initialize the active_lots table in the database.

    Returns:
        None
    Raises:
        Exception: If an error occurs during table creation.
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS active_lots (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(50) NOT NULL,
        qty NUMERIC(20, 8) NOT NULL,
        price NUMERIC(20, 8) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        conn.commit()


def initialize_history_lots_table():
    """
    Initialize the history_lots table in the database.

    Returns:
        None
    Raises:
        Exception: If an error occurs during table creation.
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS history_lots (
        id SERIAL PRIMARY KEY,
        action VARCHAR(50) NOT NULL,
        symbol VARCHAR(50) NOT NULL,
        qty NUMERIC(20, 8) NOT NULL,
        price NUMERIC(20, 8) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_table_query)
        conn.commit()


def get_system_status(api_key: str):
    """
    Fetch the system status from management-service.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        str: System status.

    Raises:
        Exception: If an error occurs during fetch.
    """
    try:
        response = requests.get(url=f"{os.getenv('MANAGEMENT_API_HOST', 'localhost')}:{os.getenv('MANAGEMENT_API_PORT', 80)}/get_system_status",
                                params={"api_key": api_key})
        response.raise_for_status()
        return response.json()["system_status"]
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        raise


def create_lot(cursor, symbol, qty, price):
    """
    Insert a new lot into the active_lots table.

    Args:
        cursor (psycopg2.Cursor): Database cursor.
        symbol (str): Symbol of the coin.
        qty (float): Quantity of the coin.
        price (float): Price at which the coin was bought/sold.

    Returns:
        None
    Raises:
        Exception: If an error occurs during insertion.
    """
    cursor.execute("INSERT INTO active_lots (symbol, qty, price) VALUES (%s, %s, %s)", (symbol, qty, price))


def create_history_lot(cursor, action, symbol, qty, price):
    """
    Insert a new history record into the history_lots table.

    Args:
        cursor (psycopg2.Cursor): Database cursor.
        action (str): Action type (buy/sell).
        symbol (str): Symbol of the coin.
        qty (float): Quantity of the coin.
        price (float): Price at which the coin was bought/sold.

    Returns:
        None
    Raises:
        Exception: If an error occurs during insertion.
    """
    cursor.execute("INSERT INTO history_lots (action, symbol, qty, price) VALUES (%s, %s, %s, %s)", (action, symbol, qty, price))


def delete_lot(cursor, symbol):
    """
    Delete a lot from the active_lots table.

    Args:
        cursor (psycopg2.Cursor): Database cursor.
        symbol (str): Symbol of the coin to be deleted.

    Returns:
        None
    Raises:
        Exception: If an error occurs during deletion.
    """
    cursor.execute("DELETE FROM active_lots WHERE symbol = %s", (symbol,))


def get_active_lots(cursor):
    """
    Fetch all lot records from the active_lots table.

    Args:
        cursor (psycopg2.Cursor): Database cursor.

    Returns:
        list[dict]: List of active lot records.
    Raises:
        Exception: If an error occurs during fetch.
    """
    cursor.execute("SELECT * FROM active_lots")
    return cursor.fetchall()


def get_symbols_active_lots(cursor):
    """
    Fetch all symbols from the active_lots table.

    Args:
        cursor (psycopg2.Cursor): Database cursor.

    Returns:
        list[str]: List of symbols.
    Raises:
        Exception: If an error occurs during fetch.
    """
    cursor.execute("SELECT symbol FROM active_lots")
    return [row[0] for row in cursor.fetchall()]


def get_count_lots(cursor):
    """
    Get the count of lot records from the active_lots table.

    Args:
        cursor (psycopg2.Cursor): Database cursor.

    Returns:
        int: Count of lot records.
    Raises:
        Exception: If an error occurs during fetch.
    """
    cursor.execute("SELECT COUNT(id) FROM active_lots")
    return cursor.fetchone()[0]


def get_qty_symbol(cursor, symbol):
    """
    Get the quantity of a specific coin in the active lots.

    Args:
        cursor (psycopg2.Cursor): Database cursor.
        symbol (str): Symbol of the coin to query.

    Returns:
        float: Quantity of the coin.
    Raises:
        Exception: If an error occurs during fetch.
    """
    cursor.execute("SELECT qty FROM active_lots WHERE symbol = %s", (symbol,))
    return cursor.fetchone()[0]

def get_price_limit(api_key: str):
    """
    Fetch the price limit from management-service.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        float: Price limit.

    Raises:
        Exception: If an error occurs during fetch.
    """
    try:
        response = requests.get(url=f"{os.getenv('MANAGEMENT_API_HOST', 'localhost')}:{os.getenv('MANAGEMENT_API_PORT', 80)}/get_price_limit",
                                params={"api_key": api_key})
        response.raise_for_status()
        return response.json()["price_limit"]
    except Exception as e:
        logger.error(f"Error fetching price limit: {e}")
        raise

def get_num_available_lots(api_key: str):
    """
    Fetch the number of available lots from management-service.

    Args:
        api_key (str): The API token for authorization.

    Returns:
        int: Number of available lots.

    Raises:
        Exception: If an error occurs during fetch.
    """
    try:
        response = requests.get(url=f"{os.getenv('MANAGEMENT_API_HOST', 'localhost')}:{os.getenv('MANAGEMENT_API_PORT', 80)}/get_num_available_lots",
                                params={"api_key": api_key})
        response.raise_for_status()
        return response.json()["num_available_lots"]
    except Exception as e:
        logger.error(f"Error fetching number available lots: {e}")
        raise


class TradingClient:
    def __init__(self, api_key):
        """
        Initialize the Bybit client.

        Returns:
            None
        Raises:
            Exception: If an error occurs during initialization.
        """
        self.bybit_client = HTTP(
            testnet=False,
            api_key=os.getenv('BYBIT_API_KEY'),
            api_secret=os.getenv('BYBIT_API_SECRET'),
            demo = os.getenv('BYBIT_DEMO_MODE', 'True') == 'True'
        )
        self.management_host = os.getenv('MANAGEMENT_API_HOST', 'localhost')
        self.management_port = os.getenv('MANAGEMENT_API_PORT', 80)
        self.management_api_key = api_key



    def get_qty_coin_info(self, symbol) -> tuple[float, float, str, int]:
        """
        Get the quantity information for a coin.

        Args:
            symbol (str): Symbol of the coin to query.

        Returns:
            tuple: max_qty, min_qty, step_qty, min_order_usdt
        Raises:
            Exception: If an error occurs during fetching.
        """
        try:
            symbol_qty_info = self.bybit_client.get_instruments_info(category="linear",
                                                                     symbol=symbol)["result"]["list"][0]["lotSizeFilter"]
            max_qty = float(symbol_qty_info.get("maxMktOrderQty"))
            min_qty = float(symbol_qty_info.get("minOrderQty"))
            step_qty = symbol_qty_info.get("qtyStep")
            min_order_usdt = int(symbol_qty_info.get("minNotionalValue"))
            return max_qty, min_qty, step_qty, min_order_usdt
        except Exception as e:
            logger.error(f"Error fetching qty coin info: {e}")
            raise Exception(f"Failed to fetch qty coin info: {str(e)}")


    def get_coin_balance(self, symbol) -> float:
        """
        Get the current balance of a specific coin.

        Args:
            symbol (str): Symbol of the coin to query.

        Returns:
            float: Current balance.
        Raises:
            Exception: If an error occurs during fetching.
        """
        try:
            if symbol[:-4] not in [item['coin'] for item in self.bybit_client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]['coin']]:
                return 0
            symbol_wallet_balance = self.bybit_client.get_wallet_balance(accountType="UNIFIED", coin=symbol[:-4])["result"]["list"][0]["coin"][0]["walletBalance"]
            symbol_wallet_balance = float(symbol_wallet_balance) if symbol_wallet_balance != '' else 0
            return symbol_wallet_balance
        except Exception as e:
            logger.error(f"Error fetching coin balance: {e}")
            raise Exception(f"Failed to fetch coin balance: {str(e)}")

    def get_real_balance(self) -> float:
        """
        Get the current real balance of the trader.

        Returns:
            float: Current real balance.
        Raises:
            Exception: If an error occurs during fetching.
        """
        try:
            balance_info = self.bybit_client.get_wallet_balance(accountType="UNIFIED",
                                                                coin="USDT")["result"]["list"][0]["coin"][0]["walletBalance"]
            balance_info = float(balance_info) if balance_info != '' else 0
            return balance_info
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise Exception(f"Failed to fetch balance: {str(e)}")

    def get_fake_balance(self) -> float:
        """
        Get the current fake balance of the trader.

        Returns:
            float: Current fake balance.
        Raises:
            Exception: If an error occurs during fetching.
        """
        try:
            response = requests.get(self.management_host+':'+str(self.management_port)+'/'+'get_fake_balance',
                                    params={"api_key": self.management_api_key})
            response.raise_for_status()
            fake_balance = response.json()['fake_balance']
            return fake_balance

        except Exception as e:
            logger.error(f"Error fetching fake balance: {e}")
            raise Exception(f"Failed to fetch fake balance: {str(e)}")

    def set_fake_balance(self, fake_balance) -> float:
        """
        Set the new fake balance of the trader.

        Args:
            fake_balance (float): New fake balance.

        Returns:
            float: Updated fake balance.
        Raises:
            Exception: If an error occurs during setting.
        """
        try:
            response = requests.post(self.management_host+':'+str(self.management_port)+'/'+'set_fake_balance'+'/'+str(fake_balance),
                                     params={"api_key": self.management_api_key})
            response.raise_for_status()
            return fake_balance

        except Exception as e:
            logger.error(f"Error setting fake balance: {e}")
            raise Exception(f"Failed to set fake balance: {str(e)}")

    def get_num_available_lots(self) -> int:
        """
        Get the number of available lots of the trader.

        Returns:
            int: Number of available lots.
        Raises:
            Exception: If an error occurs during fetching.
        """
        try:
            response = requests.get(self.management_host+':'+str(self.management_port)+'/'+'get_num_available_lots',
                                    params={"api_key": self.management_api_key})
            response.raise_for_status()
            fake_balance = response.json()['num_available_lots']
            return fake_balance

        except Exception as e:
            logger.error(f"Error fetching number available lots: {e}")
            raise Exception(f"Failed to fetch number available lots: {str(e)}")

    def calc_qty_symbol(self, symbol, price):

        symbol_wallet_balance = self.get_coin_balance(symbol)
        max_qty, min_qty, step_qty, min_order_usdt = self.get_qty_coin_info(symbol)

        if len(step_qty.split('.')) == 1:
            precision_qty = 0
        else:
            precision_qty = len(step_qty.split('.')[1])

        fake_balance = self.get_fake_balance()
        num_available_lots = self.get_num_available_lots()

        qty = fake_balance / num_available_lots / price
        qty -= symbol_wallet_balance

        qty = round(qty, precision_qty)
        if qty * price < min_order_usdt and qty < min_qty:
            qty = 0
        elif qty > max_qty:
            qty = max_qty

        return qty

    def make_trade(self, signal: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Make a trade using the provided signal.

        Args:
            signal (dict): Signal with action, symbol, price, and qty.

        Returns:
            tuple: Trade result and quantity.
        Raises:
            Exception: If an error occurs during trading.
        """
        symbol = signal['symbol']
        action = signal['action']
        price = signal['price']
        qty = self.calc_qty_symbol(symbol, price) if signal['qty'] is None else signal['qty']

        if action not in ['buy', 'sell']:
            raise ValueError(f"Invalid action type: {action}")

        try:

            order_params = {
                "category": "linear",
                "symbol": symbol,
                "side": action.capitalize(),
                "order_type": "Market",
                "qty": qty}

            result = self.bybit_client.place_order(**order_params)
            logger.info(f"Trade executed: {order_params}")

            return result, qty

        except Exception as e:
            logger.error(f"Error making trade: {e}")
            raise Exception(f"Failed to make trade: {str(e)}")


class RabbitClient:
    def __init__(self):
        """
        Initialize the RabbitMQ client.

        Returns:
            None
        Raises:
            Exception: If an error occurs during initialization.
        """
        self.connection = None
        self.channel = None
        self.queue_name = os.getenv('QUEUE_NAME', '')

        self.rabbitmq_params = ConnectionParameters(
            host=os.getenv('RABBITMQ_HOST', ''),
            port=int(os.getenv('RABBITMQ_PORT', 5672)),
            credentials=PlainCredentials(
                os.getenv('RABBITMQ_DEFAULT_USER', 'guest'),
                os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')
            )
        )

    def connect(self):
        """
        Connect to the RabbitMQ server and create a channel.

        Returns:
            None
        Raises:
            Exception: If an error occurs during connection.
        """
        self.connection = BlockingConnection(self.rabbitmq_params)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name)

    def close(self):
        """
        Close the RabbitMQ connection.

        Returns:
            None
        Raises:
            Exception: If an error occurs during closing.
        """
        if self.connection and self.connection.is_open:
            self.connection.close()
