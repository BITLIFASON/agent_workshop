# Ветка backtest воркшопа по разработке автономного агента на основе LLM

## Инструкция по запуску

Получение файла сессии Telegram:
```bash
python get_telegram_session.py
cp backtesting_session.session backtest/backtesting_session.session
```

Синхронный бэк-тест:
```bash
docker compose -f backtest/sync-backtest-docker-compose.yml build
docker compose -f backtest/sync-backtest-docker-compose.yml up
```

Асинхронный бэк-тест:
```bash
docker compose -f backtest/async-backtest-docker-compose.yml build
docker compose -f backtest/async-backtest-docker-compose.yml up
```

