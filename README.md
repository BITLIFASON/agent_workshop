# Воркшоп по разработке автономного агента на основе LLM

## Описание проекта 

### Концепция проекта
Торговый бот на криптовалютной бирже ByBit

### Цель проекта
Создание торгового бота для криптовалютной бирже ByBit с управлением балансом аккаунта и торгующего по сигналам из Telegram канала

### Требования проекта
Оптимальное управление балансом счёта, положительный PnL в долгосроке, 

### Критерий агентности
Автономность системы заключается в автоматическом управлении балансом и принятии решения с помощью агентов

### Стек

- Python - язык программирования
- Docker - для организации микросервисной архитектуры
- Telegram API - Telethon для чтения сообщений из Telegram канала с сигналами
- Bybit API - pybit для взаимодействия с API биржи Bybit
- База данных - PostgreSQL/Redis для хранения проведённых операций
- LLM/Agent - LangChain/Haystack/Langgraph/OpenAI API/Anthropic API/Google PaLM API
- Веб-сервис - FastAPI/Flask/Django для создания приложения
- Продуктовый мониторинг - Streamlit/Dash для создания дэша с продуктовыми метриками
- Задачи - Celery/Asyncio для создания задач на торговлю
- Технический мониторинг - Loguru/Prometheus + Grafana  для создания дэша с техническими метриками


### Архитектура

https://app.holst.so/share/b/642a2d06-d6e5-4a48-be29-e0b764b01f3b - верхнеуровневая архитектура проекта


### План работ

1) Валидация проекта (выполнено)
2) Проектирование архитектуры (выполнено)
3) Бэктестинг сигналов из канала Telegram (выполнено)
4) Реализация необходимых модулей системы с эвристическим риск-менеджментом (частично выполнено)
5) Компоновка веб-сервиса
6) Создание первичного прототипа системы с агентами
7) Интеграция агентов в веб-сервис
8) Подключение мониторинга
9) Доработка системы


### Особенности реализации

- при отсутствии доступа к API LLM не проводить новых операций на покупку, а только завершать старые по сигналам из канала


### Альтернативы

- Ручная логика управления балансом - запоминать начальный баланс в константу, ставить по 10% от константы на каждый ордер, при прибыли или убытке вычитать сумму из баланса

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

