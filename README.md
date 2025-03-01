# Crypto Trader Assistant

## Описание проекта 

Проект представляет собой торгового бота на основе агентов для криптовалютной биржи ByBit с управлением риск-менеджментом, разработанного для автоматизации торговли по сигналам из Telegram каналов

## 🎯 Цели проекта
- Оптимальное управление балансом счёта
- Положительный PnL в долгосроке


## 🛠 Технологии

- Основная LLM: 🧠 Qwen2.5:14b-instruct
- Инференс LLM: 🦙 Ollama
- Фреймворк:  <img src="https://i.imgur.com/0F5MqR8.png" width="15"> Crew AI
- База данных: 🐘 PostgreSQL
- API: ✉️ Telegram API, 📈 Bybit API
- Бекенд: ⚙ FastAPI

## 🗒 Архитектура проекта

<img src="https://i.imgur.com/hqNF2FD.png">

## 🤖 Схема агентов:

```mermaid
flowchart LR
    %% Говорим, что схема идёт слева направо (LR)
    
    subgraph TELEGRAM
    TP[(Telegram Parser)]:::greenBox
    startParser((initialize)):::method
    initParser((start)):::method
    TP --> initParser
    TP --> startParser
    end

    subgraph TRADING_SYSTEM
    TS[(Trading System)]:::purpleBox
    initSystem((initialize)):::method
    startSystem((start)):::method
    TS --> initSystem
    TS --> startSystem
    end

    subgraph AGENTS
    SPA[(Signal Parser Agent)]:::blueBox
    BCA[(Balance Controller Agent)]:::blueBox
    TEA[(Trading Executor Agent)]:::blueBox
    WIA[(Write Info Agent)]:::blueBox
    end

    subgraph Signal Parser Tools
    SPT[(Signal Parser Tool)]:::grayBox
    end

    subgraph Balance Controller Tools
    BCT[(Bybit Balance Tool)]:::grayBox
    RDT[(Read Database Tool)]:::grayBox
    MST[(Management Service Tool)]:::grayBox
    end

    subgraph Trading Executor Tools
    BTT[(Bybit Trading Tool)]:::grayBox
    end

    subgraph Write Info Tools
    WDT[(Write Database Tool)]:::grayBox
    end


    %% Связи между блоками
    TP --> TS

    TS --> SPA
    TS --> BCA
    TS --> TEA
    TS --> WIA

    SPA --> SPT

    BCA --> BCT
    BCA --> RDT
    BCA --> MST

    TEA --> BTT

    WIA --> WDT


    %% Опционально оформим стили
    classDef greenBox fill:#dafbe1,color:#333,stroke:#8dde98,stroke-width:2px
    classDef purpleBox fill:#fce4ff,color:#333,stroke:#fcb0ff,stroke-width:2px
    classDef blueBox fill:#d4efff,color:#333,stroke:#5dc8f4,stroke-width:2px
    classDef grayBox fill:#f4f4f4,color:#333,stroke:#ccc,stroke-width:2px
    classDef method fill:#fff,color:#333,stroke:#999,stroke-width:1px,stroke-dasharray:3 2
```

## ✨ Ключевые фишки

- Интеграция с Telegram каналами: можно подключать несколько каналов с сигналами
- Возможность устанавливать свои ограничения: детальная настройка ограничений системы
- Автономность системы: самостоятельное реагирование системы на входящие сигналы
- Сохранение истории торговли: просмотр совершённых сделок и их анализ
- Автоматический риск-менеджмент: принятие решений с помощью LLM

## ⏰ План работ

1) Валидация проекта
2) Проектирование архитектуры
3) Бэктестинг сигналов из канала Telegram
4) Подготовка прототипа системы агентов
5) Интеграция с сервисами
6) Доработка системы агентов

## 🚀 TODO
- Подключение мониторинга
- Улучшение системы
