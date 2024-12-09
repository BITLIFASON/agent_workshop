
create_trades_table_query = """
    CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(50) NOT NULL,
        price_buy NUMERIC(19, 8),
        buy_timestamp TIMESTAMP,
        price_sell NUMERIC(19, 8),
        sell_timestamp TIMESTAMP,
        auto_profit_percentage NUMERIC(10, 2),
        manual_profit_percentage NUMERIC(5, 2)
    )
"""
create_actions_table_query = """
    CREATE TABLE IF NOT EXISTS actions (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(50) NOT NULL,
        action VARCHAR(10),
        price NUMERIC(19, 8),
        timestamp TIMESTAMP
    )
"""

active_buy_query = """
                SELECT action
                FROM actions
                WHERE symbol = :symbol
                ORDER BY timestamp DESC
                LIMIT 1
            """
insert_trade_query = """
    INSERT INTO trades (symbol, price_buy, buy_timestamp, price_sell, sell_timestamp, auto_profit_percentage, manual_profit_percentage)
    VALUES (:symbol, :price_buy, :timestamp, NULL, NULL, NULL, NULL)
"""
update_trade_query = """
    UPDATE trades
    SET
        price_sell = :price_sell,
        sell_timestamp = :timestamp,
        auto_profit_percentage = :profit_percentage,
        manual_profit_percentage = (:price_sell / price_buy - 1) * 100
    WHERE symbol = :symbol AND price_sell IS NULL
"""
insert_action_query = """
    INSERT INTO actions (symbol, action, price, timestamp)
    VALUES (:symbol, :action, :price, :timestamp)
"""

calc_profit_query = """
    SELECT
        DATE_TRUNC('month', buy_timestamp) AS month,
        SUM(auto_profit_percentage) AS sum_auto_profit_percentage,
        SUM(manual_profit_percentage) AS sum_manual_profit_percentage
    FROM trades
    WHERE auto_profit_percentage < 100 AND price_sell IS NOT NULL
    GROUP BY month
    ORDER BY month;
"""
