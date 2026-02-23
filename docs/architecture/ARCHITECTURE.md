# ARCHITECTURE.md — Архитектура B2B Flower Market Platform

## 1. Обзор системы

**B2B Flower Market Platform** — data-first маркетплейс оптовых цветов для одного города.

### Ключевой актив
Нормализованная база данных рынка, а не UI. Платформа решает задачу:
- Приём разнородных прайс-листов от поставщиков (CSV/XLSX)
- Парсинг и нормализация к единому формату
- Публикация офферов для розничного поиска
- Минимальный order flow (без платежей в MVP)

### Технологический стек
- **Backend**: FastAPI (async) + SQLAlchemy (async) + Alembic
- **Database**: PostgreSQL 16
- **Frontend**: React + TypeScript + Redux Toolkit
- **Telegram Bot**: python-telegram-bot 21.x + httpx
- **AI**: DeepSeek API (OpenAI-совместимый, модель deepseek-chat)
- **PDF**: pdfplumber (таблицы) + PyMuPDF/fitz (текст)
- **Logging**: structlog (JSON)
- **Testing**: pytest

---

## 2. Структура репозитория

```
Маркетплейс/
├── apps/api/              # FastAPI backend (бизнес-логика + DB)
│   ├── main.py            # Точка входа, регистрация роутеров
│   ├── config.py          # Конфигурация из .env
│   ├── database.py        # SQLAlchemy engine + session
│   ├── models/            # ORM модели (таблицы)
│   ├── routers/           # HTTP endpoints (REST API)
│   │   └── telegram.py    # Internal API для Telegram-бота
│   ├── services/          # Бизнес-логика (оркестрация)
│   ├── auth/              # JWT аутентификация
│   ├── data/              # Seed данные (словарь)
│   └── scripts/           # CLI скрипты
│
├── apps/bot/              # Telegram-бот (тонкий клиент к API)
│   ├── main.py            # Entry point (webhook/polling)
│   ├── config.py          # Bot settings (BOT_TOKEN, API_URL)
│   ├── api_client.py      # httpx async клиент к FastAPI
│   ├── keyboards.py       # Inline/Reply клавиатуры
│   └── handlers/          # Обработчики команд
│       ├── start.py       # /start, выбор роли, onboarding
│       ├── price.py       # Приём файлов, /price
│       └── common.py      # /help, /status, /unlink, заглушки
│
├── packages/core/         # Чистые функции (БЕЗ доступа к DB)
│   ├── parsing/           # CSV/XLSX/PDF парсинг, извлечение атрибутов
│   ├── normalization/     # Детектирование, confidence scoring
│   ├── ai/                # AI-модули (DeepSeek integration)
│   │   ├── client.py      # DeepSeek API клиент
│   │   ├── prompts.py     # Системные промпты
│   │   ├── column_mapping.py  # AI-fallback маппинг колонок
│   │   ├── text_extraction.py # AI-извлечение из текста PDF
│   │   └── service.py     # AI enrichment сервис
│   └── utils/             # Утилиты (stable_key)
│
├── frontend/              # React приложение
│   ├── src/features/      # Функциональные модули
│   └── src/app/           # Redux store
│
├── infra/                 # Docker Compose, конфиги
├── alembic/               # Миграции БД
├── tests/                 # Unit + integration тесты
├── data/                  # Тестовые данные
└── docs/                  # Документация
```

---

## 3. Слои архитектуры

### 3.1 Диаграмма зависимостей

```
┌──────────────────────────┐   ┌──────────────────────────┐
│      HTTP Client         │   │     Telegram Bot          │
│  (Frontend, curl, etc.)  │   │   (apps/bot/, PTB lib)    │
└────────────┬─────────────┘   └────────────┬──────────────┘
             │                               │ httpx (X-Bot-Token)
             ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Routers (apps/api/routers/)                │
│   admin.py, offers.py, orders.py, telegram.py (internal)    │
│                 (HTTP endpoints, validation)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                Services (apps/api/services/)                 │
│   ImportService, NormalizationService, PublishService       │
│              (бизнес-логика + оркестрация)                  │
├─────────────────┬───────────────────────────────────────────┤
│                 │                                           │
│    ┌────────────▼────────────┐    ┌─────────────────────┐  │
│    │   packages/core/*       │    │   Models (ORM)      │  │
│    │   (pure functions)      │    │   (SQLAlchemy)      │  │
│    │   NO DB ACCESS          │    │                     │  │
│    └─────────────────────────┘    └──────────┬──────────┘  │
│                                               │             │
└───────────────────────────────────────────────┼─────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Правила зависимостей

| Слой | Может зависеть от | НЕ может зависеть от |
|------|-------------------|----------------------|
| Routers | Services, Models, Auth | packages/core напрямую |
| Services | packages/core, Models, DB Session | Routers |
| packages/core | Python stdlib, внешние API (DeepSeek) | DB, Services, Models |
| Models | SQLAlchemy | Всего остального |
| apps/bot | httpx (→ API), python-telegram-bot | DB, Models напрямую |

---

## 4. Основные компоненты

### 4.1 API Routers (apps/api/routers/)

| Файл | Prefix | Назначение |
|------|--------|------------|
| `health.py` | `/health` | Проверка живости |
| `auth.py` | `/auth` | Регистрация, логин, JWT |
| `admin.py` | `/admin` | Управление поставщиками, импорт CSV |
| `dictionary.py` | `/admin/dictionary` | Управление словарём нормализации |
| `skus.py` | `/admin/skus` | Управление каноническими SKU |
| `normalization.py` | `/admin/normalization` | Propose/confirm маппингов |
| `publish.py` | `/admin/publish` | Публикация офферов |
| `offers.py` | `/offers` | Поиск офферов (публичный) |
| `orders.py` | `/orders` | Заказы покупателей |
| `buyers.py` | `/admin/buyers` | Управление покупателями |
| `supplier_orders.py` | `/admin` | Заказы для поставщиков |
| `telegram.py` | `/internal/telegram` | Internal API для Telegram-бота |

### 4.2 Services (apps/api/services/)

| Сервис | Ответственность |
|--------|----------------|
| `ImportService` | CSV/XLSX/PDF → raw_rows → supplier_items → offer_candidates (+ AI fallbacks) |
| `NormalizationService` | Propose SKU mappings с confidence scoring |
| `PublishService` | offer_candidates + confirmed mappings → offers |
| `DictionaryService` | CRUD для словаря |
| `SkuService` | CRUD для NormalizedSKU |
| `OrderService` | Создание и управление заказами |

### 4.3 Core Modules (packages/core/)

**Парсинг** (`parsing/`):
- `csv_parser.py` — парсинг CSV, автоопределение headers
- `headers.py` — нормализация заголовков (русский/английский)
- `price.py` — парсинг цен (фикс/диапазон, русский формат)
- `attributes.py` — извлечение length_cm, pack_qty, country

**Нормализация** (`normalization/`):
- `detection.py` — определение product_type, variety, subtype
- `confidence.py` — расчёт confidence score
- `tokens.py` — токенизация, стоп-слова

**AI** (`ai/`):
- `client.py` — DeepSeek API клиент (OpenAI-совместимый)
- `prompts.py` — системные промпты для разных задач
- `column_mapping.py` — AI-fallback для определения колонок
- `text_extraction.py` — AI-извлечение данных из текста PDF
- `service.py` — AI enrichment сервис (атрибуты, clean_name)

### 4.4 Telegram Bot (apps/bot/)

Telegram-бот — **тонкий клиент** к FastAPI API. Не имеет прямого доступа к БД.

| Файл | Назначение |
|------|------------|
| `main.py` | Entry point: webhook (production) / polling (dev) |
| `config.py` | Pydantic Settings: BOT_TOKEN, API_URL, WEBHOOK_URL |
| `api_client.py` | httpx async клиент к Internal Telegram API |
| `keyboards.py` | Inline/Reply клавиатуры |
| `handlers/start.py` | `/start`, выбор роли, привязка по телефону, регистрация |
| `handlers/price.py` | Приём файлов (CSV/XLSX/PDF), `/price` — статус |
| `handlers/common.py` | `/help`, `/status`, `/unlink`, заглушки |

**Архитектура:**
```
Telegram → nginx (/flower/bot/webhook) → Bot (порт 8081)
                                              ↓ httpx (X-Bot-Token)
                                         FastAPI API (порт 8000/8080)
                                              ↓
                                         PostgreSQL
```

**Утилиты** (`utils/`):
- `stable_key.py` — генерация стабильных ключей для дедупликации

---

## 5. Слои данных (Database)

### 5.1 Концептуальная модель

```
┌─────────────────────────────────────────────────────────────┐
│                     RAW LAYER (immutable)                    │
│    import_batches → raw_rows → parse_runs → parse_events    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PARSED LAYER                             │
│              supplier_items → offer_candidates               │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   NORMALIZED LAYER                           │
│    dictionary_entries → normalized_skus → sku_mappings      │
│                    → normalization_tasks                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PUBLISH LAYER                             │
│                         offers                               │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORDERS LAYER                              │
│                   orders → order_items                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Ключевые таблицы

| Таблица | Слой | Назначение |
|---------|------|------------|
| `import_batches` | RAW | Одна загрузка CSV |
| `raw_rows` | RAW | Исходные строки (immutable) |
| `parse_runs` | RAW | Логирование парсинга |
| `parse_events` | RAW | Ошибки/warnings парсинга |
| `supplier_items` | PARSED | Позиция поставщика (stable_key) |
| `offer_candidates` | PARSED | Предложение с ценой |
| `dictionary_entries` | NORMALIZED | Словарь (синонимы, правила) |
| `normalized_skus` | NORMALIZED | Канонический SKU |
| `sku_mappings` | NORMALIZED | Связь supplier_item → SKU |
| `normalization_tasks` | NORMALIZED | Задачи на ручную review |
| `offers` | PUBLISH | Публичные офферы |
| `orders` | ORDERS | Заказы покупателей |
| `order_items` | ORDERS | Позиции заказа |
| `suppliers` | REFERENCE | Поставщики |
| `buyers` | REFERENCE | Покупатели |
| `cities` | REFERENCE | Города |

---

## 6. Data Flow

### 6.1 Импорт CSV

```
POST /admin/suppliers/{id}/imports/csv
         │
         ▼
┌─────────────────────────────────────┐
│       ImportService.import_csv()    │
│                                     │
│  1. Создать ImportBatch             │
│  2. parse_csv_content() [core]      │
│  3. Сохранить RawRows               │
│  4. normalize_headers() [core]      │
│  5. parse_price() [core]            │
│  6. extract_* [core]                │
│  7. generate_stable_key() [core]    │
│  8. Создать SupplierItem            │
│  9. Создать OfferCandidate          │
│ 10. Логировать ParseEvents          │
│ 11. status = "parsed"               │
└─────────────────────────────────────┘
```

### 6.2 Нормализация

```
POST /admin/normalization/propose
         │
         ▼
┌─────────────────────────────────────┐
│  NormalizationService.propose()     │
│                                     │
│  1. Загрузить Dictionary            │
│  2. detect_product_type() [core]    │
│  3. detect_variety() [core]         │
│  4. detect_subtype() [core]         │
│  5. Найти/создать NormalizedSKU     │
│  6. calculate_confidence() [core]   │
│  7. Создать SKUMapping (proposed)   │
│  8. Создать NormalizationTask       │
│     (если ambiguous)                │
└─────────────────────────────────────┘
```

### 6.3 Публикация

```
POST /admin/publish/suppliers/{id}
         │
         ▼
┌─────────────────────────────────────┐
│  PublishService.publish_offers()    │
│                                     │
│  1. Найти latest ImportBatch        │
│  2. Получить offer_candidates       │
│  3. Получить confirmed mappings     │
│  4. Деактивировать старые offers    │
│  5. Создать новые Offers            │
│  6. status = "published"            │
└─────────────────────────────────────┘
```

---

## 7. Что где живёт

### 7.1 Парсинг
- **Где**: `packages/core/parsing/`
- **Логика**: Чистые функции, без DB
- **Вызывается из**: `ImportService`

### 7.2 Нормализация
- **Где**: `packages/core/normalization/`
- **Логика**: Detection + confidence scoring, без DB
- **Вызывается из**: `NormalizationService`

### 7.3 Публикация
- **Где**: `apps/api/services/publish_service.py`
- **Логика**: Создание offers из candidates с confirmed mappings
- **Вызывается из**: `publish.py` router

### 7.4 Заказы
- **Где**: `apps/api/services/order_service.py`, `apps/api/routers/orders.py`
- **Логика**: CRUD + статусы

---

## 8. Что должно оставаться чистым

| Модуль | Требование |
|--------|------------|
| `packages/core/parsing/*` | NO DB, NO side effects |
| `packages/core/normalization/*` | NO DB, NO side effects |
| `packages/core/utils/*` | NO DB, NO side effects |

**Причина**: Эти модули должны быть:
- Легко тестируемыми (unit tests)
- Переиспользуемыми (CLI, batch scripts)
- Детерминированными

---

## 9. Что ломается при изменениях

| Изменение | Последствия |
|-----------|-------------|
| Изменение `stable_key` алгоритма | Дубликаты supplier_items |
| Изменение confidence scoring | Другие результаты нормализации |
| Изменение структуры raw_rows | Нужно перепарсить все батчи |
| Изменение Offer schema | Обновить frontend |
| Добавление полей в models | Новая миграция Alembic |

---

## 10. Конфигурация

### Environment Variables (.env)

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=flower_market
DB_USER=flower_user
DB_PASSWORD=flower_password

# Application
APP_ENV=development
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000

# Security
SECRET_KEY=change-in-production

# CORS
CORS_ORIGINS=*

# Rate Limiting
RATE_LIMIT_ENABLED=false
```

---

## 11. Миграции

Все изменения схемы БД через Alembic:

```bash
# Создать миграцию
alembic revision --autogenerate -m "description"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1
```

**Миграции**:
```
alembic/versions/
├── 20250112_initial_schema.py       # Базовая схема
├── 20250112_002_normalized_layer.py # SKU, mappings
├── 20250113_003_orders.py           # Orders
└── 20260203_004_auth_fields.py      # JWT auth
```

---

## 12. Запуск локально

```bash
# 1. Настройка
cp .env.example .env
python -m venv venv
venv\Scripts\activate

# 2. Зависимости
pip install -r requirements.txt

# 3. База данных
cd infra && docker compose up -d && cd ..

# 4. Миграции
alembic upgrade head

# 5. Запуск API
uvicorn apps.api.main:app --reload

# 6. Frontend (отдельный терминал)
cd frontend && npm install && npm run dev
```
