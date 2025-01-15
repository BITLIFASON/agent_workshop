import json
import os
import sys
from datetime import datetime
import functools
from loguru import logger

from utils import (
    TradingClient,
    RabbitClient,
    get_db_connection,
    initialize_active_lots_table,
    initialize_history_lots_table,
    get_system_status,
    get_symbols_active_lots,
    get_count_lots,
    get_price_limit,
    get_num_available_lots,
    create_lot,
    create_history_lot,
    delete_lot,
    get_qty_symbol,
)

MANAGEMENT_API_TOKEN = os.getenv("MANAGEMENT_API_TOKEN", "")

def process_trade(signal_str, trading_client):
    """
    Process a trade signal and execute the corresponding transaction.

    Args:
        signal_str (str): The JSON-formatted string representing the trade signal.
        trading_client (TradingClient): The Trading client instance.

    Returns:
        None
    Raises:
        Exception: If an error occurs during processing.
    """
    signal_dict = json.loads(signal_str)
    symbol = signal_dict.get("symbol")
    action = "buy" if signal_dict.get("price_buy") else "sell"
    price = float(signal_dict.get("price_buy")) if action == 'buy' else signal_dict.get("price_sell")

    if not symbol or not action:
        logger.error(f"Invalid signal: {signal_str}")
        return

    bound_actual_signal = float(os.getenv("BOUND_ACTUAL_SIGNAL", 0.5))
    delta_time = (datetime.now() - datetime.strptime(signal_dict["timestamp"], "%Y-%m-%dT%H:%M:%S")).total_seconds()
    if action == 'buy' and delta_time > bound_actual_signal * 60 * 60:
        logger.warning(f"Outdated buy signal: {signal_str}")
        return
    if action == 'sell' and delta_time > 24 * 60 * 60:
        logger.warning(f"Outdated sell signal: {signal_str}")
        return

    if price > get_price_limit(MANAGEMENT_API_TOKEN):
        logger.warning(f"High price {symbol} coin: {price}")
        return

    old_balance = trading_client.get_real_balance()

    with get_db_connection() as db_conn:
        cursor = db_conn.cursor()

        try:

            system_status = get_system_status(MANAGEMENT_API_TOKEN)
            symbols_active_lots = get_symbols_active_lots(cursor)

            if action == 'buy' and system_status == 'enable':

                num_available_lots = get_num_available_lots(MANAGEMENT_API_TOKEN)
                num_active_lots = get_count_lots(cursor)

                if num_active_lots >= num_available_lots:
                    logger.warning(f"Exceeded number of available lots: {num_active_lots}/{num_available_lots}")
                    return

                if symbol in symbols_active_lots:
                    logger.warning(f"Coin has already been bought.")
                    return

                result, qty = trading_client.make_trade({
                    "symbol": symbol,
                    "action": action,
                    "qty": None,
                    "price": price
                })
                logger.info(f"Trade executed: {result}")

                create_lot(cursor, symbol, qty, price)
                create_history_lot(cursor, action, symbol, qty, price)
                db_conn.commit()

            elif action == 'sell' and system_status in ('enable', 'sell'):

                if symbol not in symbols_active_lots:
                    logger.warning(f"Coin has not been bought.")
                    return

                qty = get_qty_symbol(cursor, symbol)

                result = trading_client.make_trade({
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "price": price
                })
                logger.info(f"Trade executed: {result}")

                delete_lot(cursor, symbol)
                create_history_lot(cursor, action, symbol, qty, price)
                db_conn.commit()

                new_balance = trading_client.get_real_balance()
                old_fake_balance = trading_client.get_fake_balance()
                delta_balance = new_balance - old_balance
                new_fake_balance = old_fake_balance + delta_balance
                trading_client.set_fake_balance(new_fake_balance)

        except Exception as e:
            logger.error(f"Error processing trade: {e}")

def on_message_callback(ch, method, properties, body, trading_client):
    """
    Callback function for handling messages from the RabbitMQ queue.

    Args:
        ch (pika.channel.Channel): The RabbitMQ channel.
        method (pika.spec.BasicDeliver): BasicDeliver frame containing delivery information.
        properties (pika.spec.BasicProperties): BasicProperties frame containing message headers and attributes.
        body (str): JSON-formatted string representing the trade signal.
        trading_client (TradingClient): The Trading client instance.

    Returns:
        None
    Raises:
        Exception: If an error occurs during processing.
    """
    try:
        signal = body.decode('utf-8')
        process_trade(signal, trading_client)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)

def main():
    """
    Main function to run the trading service.

    Returns:
        None
    Raises:
        Exception: If an error occurs during startup.
    """

    logger.info("Starting trading service...")

    try:
        rabbit_client = RabbitClient()
        rabbit_client.connect()
        logger.info("RabbitMQ client successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize RabbitMQ client: {e}")
        sys.exit(1)

    try:
        trading_client = TradingClient(MANAGEMENT_API_TOKEN)
        logger.info("Trading client Bybit successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Trading client Bybit: {e}")
        sys.exit(1)

    try:
        initialize_active_lots_table()
        initialize_history_lots_table()
        logger.info("Tables in database successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize tables in database: {e}")
        sys.exit(1)

    on_message_callback_trade = functools.partial(on_message_callback, trading_client=trading_client)
    rabbit_client.channel.basic_consume(queue=rabbit_client.queue_name,
                                        on_message_callback=on_message_callback_trade,
                                        auto_ack=False)

    logger.info("Waiting for messages...")
    rabbit_client.channel.start_consuming()

if __name__ == "__main__":
    main()
