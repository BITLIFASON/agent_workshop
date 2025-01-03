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

## Результаты тестирования

| Month   | Sum Auto Profit (%)   | Sum Manual Profit (%)     |
|---------|-----------------------|---------------------------|
| 2024-07 | -29.44                | 74.13                     |
| 2024-08 | -143.46               | -65.66                    |
| 2024-09 | 437.98                | 300.12                    |
| 2024-10 | 175.87                | 45.89                     |
| 2024-11 | 764.33                | 1176.72                   |
| 2024-12 | 609.91                | -10.21                    |
