# Backend API Reference

## Обзор

Полная документация REST API для B2B Flower Market Platform.

API обеспечивает:
- Аутентификация и авторизация (JWT)
- Управление поставщиками и импортом
- Словарная нормализация
- Управление каноническими SKU
- Workflow ручного review (propose → review → confirm)
- Публикация офферов
- Управление заказами

---

## Содержание

1. [Аутентификация](#authentication)
2. [Health](#health)
3. [Suppliers](#suppliers)
4. [Imports](#imports)
5. [Dictionary](#dictionary-management)
6. [Flower Catalog](#flower-catalog) ← **NEW**
7. [SKUs](#normalized-skus)
8. [Normalization](#normalization)
9. [Publishing](#publishing)
10. [Offers (Retail)](#retail-read-only)
11. [Buyers](#buyers-admin)
12. [Orders](#orders-retail)
13. [Supplier Orders](#supplier-orders-admin)
14. [Error Handling](#error-responses)

---

## Base URL

Local development: `http://localhost:8000`

## API Conventions

- All timestamps in UTC (ISO 8601 format)
- All IDs are UUIDs
- Currency: RUB (Russian Ruble) by default
- Pagination: `limit` and `offset` query parameters

---

## Authentication

Система использует JWT (JSON Web Tokens) для аутентификации.

### Token Types

| Тип | TTL | Назначение |
|-----|-----|------------|
| Access Token | 15 минут | Авторизация API запросов |
| Refresh Token | 7 дней | Обновление access token |

### Использование токенов

Все защищённые endpoints требуют заголовок `Authorization`:

```http
Authorization: Bearer <access_token>
```

### Роли

| Роль | Описание | Доступ |
|------|----------|--------|
| `buyer` | Покупатель | /orders, /offers, /auth/me |
| `supplier` | Поставщик | /admin/suppliers/{id}/*, /auth/me |
| `admin` | Администратор | Все /admin/* endpoints |

---

### Login

**Endpoint**: `POST /auth/login`

**Description**: Аутентификация пользователя (buyer или supplier).

**Request body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "role": "buyer"
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `email` | string | Да | Email пользователя |
| `password` | string | Да | Пароль |
| `role` | string | Да | `buyer` или `supplier` |

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `access_token` | string | JWT access token |
| `refresh_token` | string | JWT refresh token |
| `expires_in` | integer | Время жизни access token (секунды) |

**Example**:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "buyer@example.com",
    "password": "password123",
    "role": "buyer"
  }'
```

**Status codes**:
- 200: Успешная аутентификация
- 400: Невалидная роль
- 401: Неверный email или пароль
- 403: Аккаунт не активен

---

### Register Buyer

**Endpoint**: `POST /auth/register/buyer`

**Description**: Регистрация нового покупателя.

**Request body**:
```json
{
  "name": "Цветочный магазин",
  "email": "shop@flowers.ru",
  "phone": "+79001234567",
  "password": "securepassword123",
  "address": "ул. Цветочная, 1",
  "city_id": "uuid-of-city"
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `name` | string | Да | Название компании/магазина |
| `email` | string | Да | Email (уникальный) |
| `phone` | string | Да | Телефон |
| `password` | string | Да | Пароль (min 8 символов) |
| `address` | string | Нет | Адрес доставки |
| `city_id` | string | Да | UUID города |

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/auth/register/buyer \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Flower Shop",
    "email": "shop@flowers.ru",
    "phone": "+79001234567",
    "password": "password123",
    "address": "123 Main St",
    "city_id": "uuid-here"
  }'
```

**Status codes**:
- 201: Успешная регистрация
- 400: Email уже зарегистрирован / Невалидный city_id

---

### Register Supplier

**Endpoint**: `POST /auth/register/supplier`

**Description**: Регистрация нового поставщика.

**Request body**:
```json
{
  "name": "Оптовая база цветов",
  "email": "info@wholesale.ru",
  "phone": "+79001234567",
  "password": "securepassword123",
  "city_id": "uuid-of-city"
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `name` | string | Да | Название компании (уникальное) |
| `email` | string | Да | Email (уникальный) |
| `phone` | string | Да | Телефон |
| `password` | string | Да | Пароль (min 8 символов) |
| `city_id` | string | Нет | UUID города |

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/auth/register/supplier \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wholesale Flowers",
    "email": "info@wholesale.ru",
    "phone": "+79001234567",
    "password": "password123"
  }'
```

**Status codes**:
- 201: Успешная регистрация
- 400: Email или название компании уже зарегистрированы

**Notes**:
- В MVP поставщик активируется автоматически
- В production: статус `pending`, требуется одобрение админа

---

### Refresh Token

**Endpoint**: `POST /auth/refresh`

**Description**: Обновление access token с помощью refresh token.

**Request body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'
```

**Status codes**:
- 200: Токены обновлены
- 401: Невалидный или истёкший refresh token

---

### Get Current User

**Endpoint**: `GET /auth/me`

**Description**: Получение информации о текущем пользователе.

**Headers**:
```http
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Цветочный магазин",
  "email": "shop@flowers.ru",
  "phone": "+79001234567",
  "role": "buyer",
  "status": "active"
}
```

**Example**:
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Status codes**:
- 200: Успех
- 401: Не авторизован
- 404: Пользователь не найден

---

### Logout

**Endpoint**: `POST /auth/logout`

**Description**: Выход из системы.

**Headers**:
```http
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Successfully logged out"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Notes**:
- JWT токены stateless, сервер не хранит сессии
- Клиент должен удалить токены из хранилища
- В production: реализовать blacklist токенов в Redis

---

## Health

### Check API Health

**Endpoint**: `GET /health`

**Description**: Health check with database connectivity test.

**Response**:
```json
{
  "status": "ok",
  "database": "connected"
}
```

**Status codes**:
- 200: Healthy
- 503: Database unavailable

---

## Suppliers

### Create Supplier

**Endpoint**: `POST /admin/suppliers`

**Description**: Create a new supplier.

**Request body**:
```json
{
  "name": "Flower Base Moscow",
  "city_id": "uuid",
  "contact_name": "Ivan Ivanov",
  "phone": "+79001234567",
  "email": "info@flowerbase.ru",
  "tier": "standard",
  "status": "active"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Flower Base Moscow",
  "city_id": "uuid",
  "contact_name": "Ivan Ivanov",
  "phone": "+79001234567",
  "email": "info@flowerbase.ru",
  "tier": "standard",
  "status": "active",
  "created_at": "2025-01-12T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/suppliers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Flower Base Moscow",
    "city_id": "uuid-here",
    "contact_name": "Ivan Ivanov",
    "phone": "+79001234567",
    "email": "info@flowerbase.ru",
    "tier": "standard",
    "status": "active"
  }'
```

---

### List Suppliers

**Endpoint**: `GET /admin/suppliers`

**Description**: List all suppliers with filters.

**Query parameters**:
- `status` (optional): Filter by status (active, blocked, pending)
- `city_id` (optional): Filter by city
- `limit` (optional, default 50): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "suppliers": [
    {
      "id": "uuid",
      "name": "Flower Base Moscow",
      "tier": "key",
      "status": "active"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Example**:
```bash
curl "http://localhost:8000/admin/suppliers?status=active&limit=10"
```

---

## Imports

### Upload CSV

**Endpoint**: `POST /admin/suppliers/{supplier_id}/imports/csv`

**Description**: Upload and parse a CSV price list for a supplier.

**Request**: Multipart form-data with file upload

**Query parameters**:
- `description` (optional): Import description

**Response** (200 OK):
```json
{
  "batch_id": "uuid",
  "supplier_id": "uuid",
  "status": "parsed",
  "total_rows": 150,
  "success_rows": 145,
  "error_rows": 5,
  "imported_at": "2025-01-12T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/suppliers/{uuid}/imports/csv \
  -F "file=@data/samples/price_list.csv" \
  -F "description=Weekly update"
```

**Status codes**:
- 200: Successfully imported
- 400: Invalid file format
- 404: Supplier not found
- 500: Import failed

**Notes**:
- Supported formats: CSV (UTF-8, CP1251, Latin-1)
- Max file size: Configured in server settings
- Creates `import_batch`, `raw_rows`, `supplier_items`, `offer_candidates`
- Status will be "parsed" on success, "failed" on error

---

### Get Import Summary

**Endpoint**: `GET /admin/imports/{import_batch_id}`

**Description**: Get import batch details and summary.

**Response** (200 OK):
```json
{
  "id": "uuid",
  "supplier_id": "uuid",
  "status": "parsed",
  "total_rows": 150,
  "imported_at": "2025-01-12T10:00:00Z",
  "description": "Weekly update"
}
```

**Example**:
```bash
curl http://localhost:8000/admin/imports/{uuid}
```

---

### List Supplier Imports

**Endpoint**: `GET /admin/suppliers/{supplier_id}/imports`

**Description**: List import batches for a supplier with pagination and statistics.

**Query parameters**:
- `page` (optional, default 1): Page number
- `per_page` (optional, default 10): Results per page

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "uuid",
      "source_filename": "price_list.xlsx",
      "status": "published",
      "imported_at": "2026-02-06T08:47:00Z",
      "raw_rows_count": 161,
      "supplier_items_count": 154,
      "offer_candidates_count": 154,
      "parse_errors_count": 7
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 10
}
```

**Example**:
```bash
curl "http://localhost:8000/admin/suppliers/{uuid}/imports?page=1&per_page=10"
```

**Status codes**:
- 200: Success
- 404: Supplier not found

---

### Get Parse Events

**Endpoint**: `GET /admin/imports/{import_batch_id}/parse-events`

**Description**: Get parsing errors and warnings for an import batch.

**Query parameters**:
- `severity` (optional): Filter by severity (error, warning, info)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": "uuid",
      "severity": "error",
      "code": "INVALID_PRICE",
      "message": "Invalid price: Empty price",
      "row_ref": "row_15",
      "created_at": "2026-02-06T08:47:00Z"
    }
  ],
  "total": 7
}
```

**Example**:
```bash
curl "http://localhost:8000/admin/imports/{uuid}/parse-events?severity=error"
```

**Status codes**:
- 200: Success
- 404: Import batch not found

**Notes**:
- `row_ref`: Reference to the original row (e.g., "row_15")
- `code`: Error code for programmatic handling (INVALID_PRICE, BUNDLE_LIST_DETECTED, etc.)
- Events are ordered by created_at ASC

---

### Delete Import Batch

**Endpoint**: `DELETE /admin/imports/{import_batch_id}`

**Description**: Delete an import batch and all related data (raw_rows, offer_candidates, parse_events).

**Response** (200 OK):
```json
{
  "id": "uuid",
  "message": "Import batch deleted successfully",
  "deleted_counts": {
    "raw_rows": 161,
    "offer_candidates": 154,
    "parse_events": 7
  }
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8000/admin/imports/{uuid}
```

**Status codes**:
- 200: Successfully deleted
- 404: Import batch not found

**Notes**:
- **Important**: Does NOT delete `supplier_items` — they may be linked to other imports
- Deletes: `raw_rows`, `offer_candidates`, `parse_events`, `parse_runs`
- This action is **irreversible**

---

### Reparse Import Batch

**Endpoint**: `POST /admin/imports/{import_batch_id}/reparse`

**Description**: Re-run parsing on existing raw_rows to regenerate offer_candidates.

**Response** (200 OK):
```json
{
  "batch_id": "uuid",
  "status": "parsed",
  "raw_rows_count": 161,
  "supplier_items_count": 154,
  "offer_candidates_count": 154,
  "parse_events_count": 7
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/imports/{uuid}/reparse
```

**Status codes**:
- 200: Successfully reparsed
- 404: Import batch not found
- 500: Reparse failed

**Notes**:
- Deletes old `offer_candidates` and `parse_events` before reparsing
- Useful after updating parsing rules or fixing dictionary entries
- Does not touch `raw_rows` (they are immutable)
- Updates the batch status based on parsing result

---

## Dictionary Management

### Bootstrap Dictionary

**Endpoint**: `POST /admin/dictionary/bootstrap`

**Description**: Bootstrap dictionary with seed data (idempotent).

Creates entries for:
- Product types (rose, carnation, etc.)
- Countries (Ecuador, Netherlands, etc.)
- Pack types (bunch, box, etc.)
- Stopwords (см, цветы, etc.)
- Regex rules (spray, bush patterns)
- Variety aliases (mondial, explorer, etc.)

**Response** (200 OK):
```json
{
  "created": 35,
  "updated": 0
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/dictionary/bootstrap
```

**Notes**:
- Idempotent: safe to run multiple times
- Uses `INSERT ... ON CONFLICT DO UPDATE`
- Returns counts of created/updated entries

---

### List Dictionary Entries

**Endpoint**: `GET /admin/dictionary`

**Description**: List dictionary entries with filters.

**Query parameters**:
- `dict_type` (optional): Filter by type (product_type, country, stopword, etc.)
- `status` (optional): Filter by status (active, inactive)
- `limit` (optional, default 100): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "entries": [
    {
      "id": "uuid",
      "dict_type": "product_type",
      "key": "rose",
      "value": "rose",
      "synonyms": ["роза", "розы", "roses"],
      "status": "active",
      "meta": {}
    }
  ],
  "total": 35,
  "limit": 100,
  "offset": 0
}
```

**Example**:
```bash
curl "http://localhost:8000/admin/dictionary?dict_type=product_type"
```

---

### Create Dictionary Entry

**Endpoint**: `POST /admin/dictionary`

**Description**: Create a new dictionary entry.

**Request body**:
```json
{
  "dict_type": "product_type",
  "key": "tulip",
  "value": "tulip",
  "synonyms": ["тюльпан", "тюльпаны"],
  "status": "active",
  "meta": {}
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "dict_type": "product_type",
  "key": "tulip",
  "value": "tulip",
  "synonyms": ["тюльпан", "тюльпаны"],
  "status": "active",
  "created_at": "2025-01-12T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/dictionary \
  -H "Content-Type: application/json" \
  -d '{
    "dict_type": "product_type",
    "key": "tulip",
    "value": "tulip",
    "synonyms": ["тюльпан"],
    "status": "active"
  }'
```

---

### Update Dictionary Entry

**Endpoint**: `PATCH /admin/dictionary/{entry_id}`

**Description**: Update an existing dictionary entry.

**Request body** (partial update):
```json
{
  "synonyms": ["тюльпан", "тюльпаны", "tulips"],
  "status": "active"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "dict_type": "product_type",
  "key": "tulip",
  "value": "tulip",
  "synonyms": ["тюльпан", "тюльпаны", "tulips"],
  "status": "active",
  "updated_at": "2025-01-12T11:00:00Z"
}
```

**Example**:
```bash
curl -X PATCH http://localhost:8000/admin/dictionary/{uuid} \
  -H "Content-Type: application/json" \
  -d '{"status": "inactive"}'
```

---

## Flower Catalog

Иерархический справочник цветов: категории → типы → субтипы → сорта.

### Структура каталога

```
flower_categories (опционально)
    └── flower_types (Роза, Хризантема, Эвкалипт)
          ├── flower_subtypes (Кустовая, Спрей, Пионовидная)
          │     └── subtype_synonyms
          ├── type_synonyms (роза, розы, rose → Роза)
          └── flower_varieties (Explorer, Freedom, Red Naomi)
                └── variety_synonyms (эксплорер → Explorer)
```

---

### List Categories

**Endpoint**: `GET /admin/catalog/categories`

**Description**: Список категорий верхнего уровня.

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "name": "Срезанные цветы",
    "slug": "cut-flowers",
    "sort_order": 1,
    "created_at": "2026-02-05T10:00:00Z",
    "types_count": 25
  }
]
```

**Example**:
```bash
curl http://localhost:8000/admin/catalog/categories
```

---

### Create Category

**Endpoint**: `POST /admin/catalog/categories`

**Description**: Создать новую категорию.

**Request body**:
```json
{
  "name": "Сухоцветы",
  "slug": "dried-flowers",
  "sort_order": 3
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "name": "Сухоцветы",
  "slug": "dried-flowers",
  "sort_order": 3,
  "created_at": "2026-02-05T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/catalog/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "Сухоцветы", "slug": "dried-flowers", "sort_order": 3}'
```

---

### List Flower Types

**Endpoint**: `GET /admin/catalog/types`

**Description**: Список типов цветов с синонимами и субтипами.

**Query parameters**:
- `category_id` (optional): Фильтр по категории
- `is_active` (optional, default true): Фильтр по активности

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "canonical_name": "Роза",
    "slug": "rosa",
    "category_id": "uuid",
    "meta": {"avg_length_min": 40, "avg_length_max": 80},
    "is_active": true,
    "created_at": "2026-02-05T10:00:00Z",
    "synonyms": ["роза", "розы", "розу", "rose", "roses"],
    "subtypes": [
      {"id": "uuid", "name": "Кустовая", "slug": "shrub"},
      {"id": "uuid", "name": "Спрей", "slug": "spray"}
    ]
  }
]
```

**Example**:
```bash
curl "http://localhost:8000/admin/catalog/types?is_active=true"
```

---

### Create Flower Type

**Endpoint**: `POST /admin/catalog/types`

**Description**: Создать новый тип цветка с синонимами.

**Request body**:
```json
{
  "canonical_name": "Пион",
  "slug": "peony",
  "category_id": "uuid",
  "meta": {"seasonal": true},
  "is_active": true,
  "synonyms": ["пион", "пионы", "peony", "peonies"]
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "canonical_name": "Пион",
  "slug": "peony",
  "category_id": "uuid",
  "meta": {"seasonal": true},
  "is_active": true,
  "created_at": "2026-02-05T10:00:00Z",
  "synonyms": ["пион", "пионы", "peony", "peonies"],
  "subtypes": []
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/catalog/types \
  -H "Content-Type: application/json" \
  -d '{
    "canonical_name": "Пион",
    "slug": "peony",
    "synonyms": ["пион", "пионы"]
  }'
```

**Status codes**:
- 201: Успешно создано
- 400: Slug уже существует

---

### Update Flower Type

**Endpoint**: `PATCH /admin/catalog/types/{type_id}`

**Description**: Обновить тип цветка.

**Request body** (partial update):
```json
{
  "canonical_name": "Пион садовый",
  "is_active": false
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "canonical_name": "Пион садовый",
  "slug": "peony",
  "is_active": false,
  "updated_at": "2026-02-05T11:00:00Z"
}
```

**Example**:
```bash
curl -X PATCH http://localhost:8000/admin/catalog/types/{uuid} \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

### Add Type Synonym

**Endpoint**: `POST /admin/catalog/types/{type_id}/synonyms`

**Description**: Добавить синоним к типу цветка.

**Request body**:
```json
{
  "synonym": "пионов",
  "priority": 50
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "type_id": "uuid",
  "synonym": "пионов",
  "priority": 50
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/catalog/types/{uuid}/synonyms \
  -H "Content-Type: application/json" \
  -d '{"synonym": "пионов"}'
```

**Notes**:
- Синонимы автоматически приводятся к lowercase
- Один синоним может указывать только на один тип (UNIQUE constraint)

---

### List Subtypes

**Endpoint**: `GET /admin/catalog/subtypes`

**Description**: Список субтипов цветков.

**Query parameters**:
- `type_id` (optional): Фильтр по типу цветка

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "type_id": "uuid",
    "name": "Кустовая",
    "slug": "shrub",
    "meta": {},
    "is_active": true,
    "created_at": "2026-02-05T10:00:00Z",
    "synonyms": ["кустовая", "кустовые", "куст", "shrub", "spray"],
    "type_name": "Роза"
  }
]
```

**Example**:
```bash
curl "http://localhost:8000/admin/catalog/subtypes?type_id={uuid}"
```

---

### Create Subtype

**Endpoint**: `POST /admin/catalog/subtypes`

**Description**: Создать субтип цветка.

**Request body**:
```json
{
  "type_id": "uuid",
  "name": "Пионовидная",
  "slug": "peony-type",
  "synonyms": ["пионовидная", "пионовидные", "garden"]
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "type_id": "uuid",
  "name": "Пионовидная",
  "slug": "peony-type",
  "is_active": true,
  "created_at": "2026-02-05T10:00:00Z",
  "synonyms": ["пионовидная", "пионовидные", "garden"]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/catalog/subtypes \
  -H "Content-Type: application/json" \
  -d '{
    "type_id": "uuid-here",
    "name": "Пионовидная",
    "slug": "peony-type",
    "synonyms": ["пионовидная"]
  }'
```

---

### List Varieties

**Endpoint**: `GET /admin/catalog/varieties`

**Description**: Список сортов цветков с поиском.

**Query parameters**:
- `type_id` (optional): Фильтр по типу цветка
- `subtype_id` (optional): Фильтр по субтипу
- `search` (optional): Поиск по названию (fuzzy search с триграммами)
- `verified_only` (optional, default false): Только проверенные сорта
- `limit` (optional, default 100): Макс. результатов
- `offset` (optional, default 0): Пагинация

**Response** (200 OK):
```json
{
  "varieties": [
    {
      "id": "uuid",
      "type_id": "uuid",
      "subtype_id": null,
      "name": "Explorer",
      "slug": "explorer",
      "official_colors": ["красный"],
      "typical_length_min": 40,
      "typical_length_max": 70,
      "meta": {},
      "is_verified": true,
      "is_active": true,
      "created_at": "2026-02-05T10:00:00Z",
      "synonyms": ["эксплорер", "eksplorer"],
      "type_name": "Роза",
      "subtype_name": null
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

**Example**:
```bash
# Поиск сорта
curl "http://localhost:8000/admin/catalog/varieties?search=explorer"

# Фильтр по типу
curl "http://localhost:8000/admin/catalog/varieties?type_id={uuid}&verified_only=true"
```

---

### Create Variety

**Endpoint**: `POST /admin/catalog/varieties`

**Description**: Создать новый сорт цветка.

**Request body**:
```json
{
  "type_id": "uuid",
  "subtype_id": null,
  "name": "Red Naomi",
  "slug": "red-naomi",
  "official_colors": ["красный", "бордовый"],
  "typical_length_min": 50,
  "typical_length_max": 80,
  "meta": {"premium": true},
  "is_verified": false,
  "synonyms": ["ред наоми", "наоми"]
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "type_id": "uuid",
  "name": "Red Naomi",
  "slug": "red-naomi",
  "official_colors": ["красный", "бордовый"],
  "typical_length_min": 50,
  "typical_length_max": 80,
  "is_verified": false,
  "is_active": true,
  "created_at": "2026-02-05T10:00:00Z",
  "synonyms": ["ред наоми", "наоми"]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/catalog/varieties \
  -H "Content-Type: application/json" \
  -d '{
    "type_id": "uuid-here",
    "name": "Red Naomi",
    "slug": "red-naomi",
    "official_colors": ["красный"],
    "synonyms": ["ред наоми"]
  }'
```

---

### Update Variety

**Endpoint**: `PATCH /admin/catalog/varieties/{variety_id}`

**Description**: Обновить сорт цветка.

**Request body** (partial update):
```json
{
  "is_verified": true,
  "official_colors": ["красный", "бордовый", "тёмно-красный"]
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Red Naomi",
  "is_verified": true,
  "official_colors": ["красный", "бордовый", "тёмно-красный"],
  "updated_at": "2026-02-05T11:00:00Z"
}
```

**Example**:
```bash
curl -X PATCH http://localhost:8000/admin/catalog/varieties/{uuid} \
  -H "Content-Type: application/json" \
  -d '{"is_verified": true}'
```

---

### Verify Variety

**Endpoint**: `PUT /admin/catalog/varieties/{variety_id}/verify`

**Description**: Отметить сорт как проверенный экспертом.

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Red Naomi",
  "is_verified": true,
  "updated_at": "2026-02-05T11:00:00Z"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/admin/catalog/varieties/{uuid}/verify
```

---

### Catalog Lookup (for Parser)

**Endpoint**: `GET /admin/catalog/lookup`

**Description**: Получить все данные каталога для использования парсером (с кэшированием).

**Response** (200 OK):
```json
{
  "types": {
    "роза": "Роза",
    "розы": "Роза",
    "rose": "Роза",
    "хризантема": "Хризантема"
  },
  "subtypes": {
    "Роза": {
      "кустовая": "Кустовая",
      "спрей": "Спрей"
    },
    "Хризантема": {
      "кустовая": "Кустовая",
      "одноголовая": "Одноголовая"
    }
  },
  "varieties": {
    "Роза": {
      "эксплорер": "Explorer",
      "explorer": "Explorer",
      "фридом": "Freedom"
    }
  },
  "cached_at": "2026-02-05T10:00:00Z"
}
```

**Example**:
```bash
curl http://localhost:8000/admin/catalog/lookup
```

**Notes**:
- Данные кэшируются на 5 минут (TTL=300s)
- Используется парсером для извлечения атрибутов из названий
- Возвращает маппинг: синоним → каноническое название

---

### Seed Catalog

**Endpoint**: `POST /admin/catalog/seed`

**Description**: Заполнить каталог начальными данными (идемпотентно).

**Response** (200 OK):
```json
{
  "categories_created": 3,
  "types_created": 35,
  "subtypes_created": 12,
  "synonyms_created": 150,
  "message": "Catalog seeded successfully"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/catalog/seed
```

**Notes**:
- Идемпотентная операция — безопасно вызывать повторно
- Создаёт 35+ типов цветов с синонимами на русском и английском
- Создаёт субтипы (кустовая, спрей, одноголовая и т.д.)
- Не перезаписывает существующие записи

---

## Normalized SKUs

### Create SKU

**Endpoint**: `POST /admin/skus`

**Description**: Create a normalized SKU (canonical product card).

**Request body**:
```json
{
  "product_type": "rose",
  "variety": "Explorer",
  "color": null,
  "title": "Rose Explorer",
  "meta": {
    "origin_default": "Ecuador",
    "subtype": "standard"
  }
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "product_type": "rose",
  "variety": "Explorer",
  "color": null,
  "title": "Rose Explorer",
  "meta": {
    "origin_default": "Ecuador"
  },
  "created_at": "2025-01-12T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/skus \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "rose",
    "variety": "Explorer",
    "title": "Rose Explorer"
  }'
```

---

### List SKUs

**Endpoint**: `GET /admin/skus`

**Description**: List normalized SKUs with search and filters.

**Query parameters**:
- `q` (optional): Search query (matches title, variety)
- `product_type` (optional): Filter by product type
- `limit` (optional, default 50): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "skus": [
    {
      "id": "uuid",
      "product_type": "rose",
      "variety": "Explorer",
      "title": "Rose Explorer"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

**Example**:
```bash
curl "http://localhost:8000/admin/skus?q=explorer&product_type=rose"
```

---

### Get SKU

**Endpoint**: `GET /admin/skus/{sku_id}`

**Description**: Get a specific normalized SKU by ID.

**Response** (200 OK):
```json
{
  "id": "uuid",
  "product_type": "rose",
  "variety": "Explorer",
  "color": null,
  "title": "Rose Explorer",
  "meta": {},
  "created_at": "2025-01-12T10:00:00Z"
}
```

**Example**:
```bash
curl http://localhost:8000/admin/skus/{uuid}
```

---

## Normalization

### Propose Mappings

**Endpoint**: `POST /admin/normalization/propose`

**Description**: Run normalization to propose SKU mappings and create review tasks.

Uses dictionary-driven algorithm with confidence scoring.

**Request body**:
```json
{
  "supplier_id": "uuid",
  "import_batch_id": null,
  "limit": 1000
}
```

**Response** (200 OK):
```json
{
  "processed_items": 150,
  "proposed_mappings": 450,
  "tasks_created": 25
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/normalization/propose \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": "uuid-here",
    "limit": 1000
  }'
```

**Status codes**:
- 200: Success
- 400: Invalid request (no filters provided)
- 404: Supplier or batch not found
- 500: Normalization failed

**Notes**:
- At least one of `supplier_id` or `import_batch_id` required
- Creates `sku_mappings` (status=proposed)
- Creates `normalization_tasks` for low confidence (<0.70)
- Idempotent: safe to run multiple times
- Returns summary with counts

**Algorithm**:
1. Extract attributes (product_type, variety, subtype, country)
2. Search candidate SKUs (exact → generic → similarity)
3. Calculate confidence for each candidate (multi-signal scoring)
4. Create top 5 mappings (confidence > 0.10)
5. Create task if confidence < 0.70 or ambiguous

---

### List Tasks

**Endpoint**: `GET /admin/normalization/tasks`

**Description**: List normalization tasks for manual review (enriched with context).

**Query parameters**:
- `status` (optional): Filter by status (open, in_progress, done)
- `supplier_id` (optional): Filter by supplier
- `limit` (optional, default 50, max 500): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "tasks": [
    {
      "id": "uuid",
      "supplier_item_id": "uuid",
      "reason": "Low confidence: 0.45",
      "priority": 150,
      "status": "open",
      "assigned_to": null,
      "created_at": "2025-01-12T10:00:00Z",
      "supplier_item": {
        "id": "uuid",
        "raw_name": "Роза неизвестная 60см",
        "raw_group": null,
        "name_norm": "роза неизвестная 60",
        "attributes": {
          "length_cm": 60
        }
      },
      "proposed_mappings": [
        {
          "id": "uuid",
          "normalized_sku_id": "uuid",
          "confidence": 0.45,
          "sku_title": "Rose Standard",
          "sku_variety": null
        }
      ],
      "sample_raw_rows": [
        {
          "raw_text": "Роза неизвестная 60см | 120"
        }
      ]
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

**Example**:
```bash
curl "http://localhost:8000/admin/normalization/tasks?status=open&limit=10"
```

**Notes**:
- Tasks ordered by priority DESC, created_at ASC
- Enriched with supplier_item details, proposed mappings, and sample raw rows
- `proposed_mappings`: Top 5 candidates with confidence scores
- `sample_raw_rows`: Up to 3 raw CSV rows for context

---

### Confirm Mapping

**Endpoint**: `POST /admin/normalization/confirm`

**Description**: Confirm a SKU mapping (manual decision). **TRANSACTIONAL**.

**Request body**:
```json
{
  "supplier_item_id": "uuid",
  "normalized_sku_id": "uuid",
  "notes": "Confirmed after manual review"
}
```

**Response** (200 OK):
```json
{
  "mapping": {
    "id": "uuid",
    "supplier_item_id": "uuid",
    "normalized_sku_id": "uuid",
    "status": "confirmed",
    "confidence": 1.0,
    "method": "manual",
    "decided_at": "2025-01-12T11:00:00Z",
    "notes": "Confirmed after manual review"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/normalization/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_item_id": "uuid-here",
    "normalized_sku_id": "uuid-here",
    "notes": "Looks correct"
  }'
```

**Status codes**:
- 200: Success
- 400: Invalid request
- 404: Supplier item or SKU not found
- 500: Confirm failed

**Notes**:
- **CRITICAL**: Only ONE confirmed mapping per supplier_item (DB constraint)
- Transaction: Reject all existing mappings → Upsert confirmed → Mark tasks done
- Sets confidence = 1.0, method = "manual"
- Marks related normalization_task(s) as status='done'

---

## Publishing

### Publish Offers

**Endpoint**: `POST /admin/publish/suppliers/{supplier_id}`

**Description**: Publish offers for supplier from latest import batch.

**Response** (200 OK):
```json
{
  "supplier_id": "uuid",
  "import_batch_id": "uuid",
  "offers_deactivated": 150,
  "offers_created": 145,
  "skipped_unmapped": 5
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/publish/suppliers/{uuid}
```

**Status codes**:
- 200: Success
- 404: Supplier not found OR no parsed imports found
- 500: Publish failed

**Notes**:
- **Replace-all strategy**: Deactivate old offers, create new ones
- Only publishes offer_candidates with **confirmed** mappings
- Skips candidates without confirmed mapping (tracked in `skipped_unmapped`)
- Updates import_batch status to 'published'
- Old offers: is_active = false (history preserved)
- New offers: is_active = true

**Algorithm**:
1. Validate supplier exists and is active
2. Find latest parsed import_batch
3. Fetch offer_candidates (validation='ok'/'warn')
4. Fetch confirmed mappings for those candidates
5. Deactivate all old offers (is_active=false)
6. Create new offers for candidates with confirmed mappings
7. Update batch status to 'published'

---

## Retail (Read-only)

### List Offers

**Endpoint**: `GET /offers`

**Description**: Search published offers with comprehensive filters (public/retail endpoint).

**Query parameters**:
- `q` (optional): Full text search (title, variety, product_type)
- `product_type` (optional): Filter by product type
- `length_cm` (optional): Filter by exact length
- `length_min` / `length_max` (optional): Filter by length range
- `price_min` / `price_max` (optional): Filter by price range
- `supplier_id` (optional): Filter by supplier
- `is_active` (optional, default true): Filter by active status
- `limit` (optional, default 100, max 500): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "offers": [
    {
      "id": "uuid",
      "supplier": {
        "id": "uuid",
        "name": "Flower Base Moscow"
      },
      "sku": {
        "id": "uuid",
        "product_type": "rose",
        "variety": "Explorer",
        "title": "Rose Explorer"
      },
      "length_cm": 60,
      "pack_type": null,
      "pack_qty": 10,
      "price_type": "fixed",
      "price_min": 120.00,
      "price_max": null,
      "currency": "RUB",
      "tier_min_qty": null,
      "tier_max_qty": null,
      "availability": "unknown",
      "stock_qty": null,
      "published_at": "2025-01-12T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

**Example**:
```bash
# Search for roses
curl "http://localhost:8000/offers?product_type=rose&limit=10"

# Full text search
curl "http://localhost:8000/offers?q=explorer"

# Filter by price and length
curl "http://localhost:8000/offers?price_max=150&length_cm=60"

# Pagination
curl "http://localhost:8000/offers?limit=20&offset=40"
```

**Notes**:
- Default filter: `is_active=true` (only current offers)
- Ordering: `published_at DESC, price_min ASC` (newest and cheapest first)
- Joined data: Includes supplier and SKU details (no additional requests needed)
- Text search: Case-insensitive substring match on title/variety/product_type
- All filters are combinable

---

## Buyers (Admin)

### Create Buyer

**Endpoint**: `POST /admin/buyers`

**Description**: Create a new retail buyer (admin endpoint).

**Request body**:
```json
{
  "name": "Flower Shop Moscow",
  "phone": "+79001234567",
  "email": "shop@flowers.ru",
  "address": "123 Main Street",
  "city_id": "uuid"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "name": "Flower Shop Moscow",
  "phone": "+79001234567",
  "email": "shop@flowers.ru",
  "address": "123 Main Street",
  "city_id": "uuid",
  "status": "active",
  "created_at": "2025-01-12T10:00:00Z",
  "updated_at": "2025-01-12T10:00:00Z"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/buyers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Flower Shop Moscow",
    "phone": "+79001234567",
    "email": "shop@flowers.ru",
    "address": "123 Main Street",
    "city_id": "uuid-here"
  }'
```

**Status codes**:
- 201: Successfully created
- 400: Validation error (phone already exists)
- 404: City not found

---

### List Buyers

**Endpoint**: `GET /admin/buyers`

**Description**: List buyers with filters (admin endpoint).

**Query parameters**:
- `status` (optional): Filter by status (active, blocked, pending_verification)
- `city_id` (optional): Filter by city
- `limit` (optional, default 100): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "name": "Flower Shop Moscow",
    "phone": "+79001234567",
    "email": "shop@flowers.ru",
    "address": "123 Main Street",
    "city_id": "uuid",
    "status": "active",
    "created_at": "2025-01-12T10:00:00Z",
    "updated_at": "2025-01-12T10:00:00Z"
  }
]
```

**Example**:
```bash
curl "http://localhost:8000/admin/buyers?status=active&limit=50"
```

---

### Get Buyer

**Endpoint**: `GET /admin/buyers/{buyer_id}`

**Description**: Get buyer details by ID (admin endpoint).

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Flower Shop Moscow",
  "phone": "+79001234567",
  "email": "shop@flowers.ru",
  "address": "123 Main Street",
  "city_id": "uuid",
  "status": "active",
  "created_at": "2025-01-12T10:00:00Z",
  "updated_at": "2025-01-12T10:00:00Z"
}
```

**Example**:
```bash
curl http://localhost:8000/admin/buyers/{uuid}
```

**Status codes**:
- 200: Success
- 404: Buyer not found

---

### Update Buyer

**Endpoint**: `PATCH /admin/buyers/{buyer_id}`

**Description**: Update buyer information (admin endpoint).

**Request body** (partial update):
```json
{
  "name": "Flower Shop Updated",
  "status": "blocked"
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "name": "Flower Shop Updated",
  "phone": "+79001234567",
  "email": "shop@flowers.ru",
  "address": "123 Main Street",
  "city_id": "uuid",
  "status": "blocked",
  "created_at": "2025-01-12T10:00:00Z",
  "updated_at": "2025-01-12T12:00:00Z"
}
```

**Example**:
```bash
curl -X PATCH http://localhost:8000/admin/buyers/{uuid} \
  -H "Content-Type: application/json" \
  -d '{"status": "blocked"}'
```

**Status codes**:
- 200: Success
- 400: Invalid status value
- 404: Buyer not found

**Valid status values**: `active`, `blocked`, `pending_verification`

---

## Orders (Retail)

### Create Order

**Endpoint**: `POST /orders`

**Description**: Create a new order (retail endpoint). MVP: No authentication - buyer_id passed in body.

**Request body**:
```json
{
  "buyer_id": "uuid",
  "items": [
    {
      "offer_id": "uuid",
      "quantity": 10,
      "notes": "Please pack carefully"
    }
  ],
  "delivery_address": "456 Oak Street",
  "delivery_date": "2025-01-15",
  "notes": "Deliver in the morning"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "buyer_id": "uuid",
  "supplier_id": "uuid",
  "status": "pending",
  "total_amount": "1000.00",
  "currency": "RUB",
  "delivery_address": "456 Oak Street",
  "delivery_date": "2025-01-15",
  "notes": "Deliver in the morning",
  "created_at": "2025-01-12T10:00:00Z",
  "confirmed_at": null,
  "rejected_at": null,
  "rejection_reason": null,
  "buyer": {
    "id": "uuid",
    "name": "Flower Shop Moscow",
    "phone": "+79001234567"
  },
  "supplier": {
    "id": "uuid",
    "name": "Flower Base Moscow"
  },
  "items": [
    {
      "id": "uuid",
      "offer_id": "uuid",
      "normalized_sku_id": "uuid",
      "quantity": 10,
      "unit_price": "100.00",
      "total_price": "1000.00",
      "notes": "Please pack carefully"
    }
  ]
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "uuid-here",
    "items": [
      {"offer_id": "uuid-here", "quantity": 10}
    ],
    "delivery_address": "456 Oak Street"
  }'
```

**Status codes**:
- 201: Successfully created
- 400: Validation error (buyer inactive, offers not found, multiple suppliers, negative quantity, etc.)
- 404: Buyer or offers not found

**MVP Constraints**:
- Single-supplier orders only (all items must be from same supplier)
- Price snapshot at order creation time (unit_price saved to order_item)
- No inventory check
- No authentication (buyer_id in request body)

---

### List Orders

**Endpoint**: `GET /orders`

**Description**: List orders with filters (retail endpoint).

**Query parameters**:
- `buyer_id` (optional): Filter by buyer
- `supplier_id` (optional): Filter by supplier
- `status` (optional): Filter by status (pending, confirmed, rejected, cancelled)
- `limit` (optional, default 50): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
{
  "total": 25,
  "limit": 50,
  "offset": 0,
  "orders": [
    {
      "id": "uuid",
      "buyer_id": "uuid",
      "supplier_id": "uuid",
      "status": "pending",
      "total_amount": "1000.00",
      "currency": "RUB",
      "delivery_address": "456 Oak Street",
      "delivery_date": "2025-01-15",
      "notes": null,
      "created_at": "2025-01-12T10:00:00Z",
      "confirmed_at": null,
      "rejected_at": null,
      "rejection_reason": null,
      "buyer": {
        "id": "uuid",
        "name": "Flower Shop Moscow",
        "phone": "+79001234567"
      },
      "supplier": {
        "id": "uuid",
        "name": "Flower Base Moscow"
      },
      "items": [...]
    }
  ]
}
```

**Example**:
```bash
# List buyer's orders
curl "http://localhost:8000/orders?buyer_id={uuid}&limit=20"

# Filter by status
curl "http://localhost:8000/orders?status=pending"
```

---

### Get Order

**Endpoint**: `GET /orders/{order_id}`

**Description**: Get order details by ID (retail endpoint).

**Response** (200 OK):
```json
{
  "id": "uuid",
  "buyer_id": "uuid",
  "supplier_id": "uuid",
  "status": "confirmed",
  "total_amount": "1000.00",
  "currency": "RUB",
  "delivery_address": "456 Oak Street",
  "delivery_date": "2025-01-15",
  "notes": "Deliver in the morning",
  "created_at": "2025-01-12T10:00:00Z",
  "confirmed_at": "2025-01-12T11:00:00Z",
  "rejected_at": null,
  "rejection_reason": null,
  "buyer": {
    "id": "uuid",
    "name": "Flower Shop Moscow",
    "phone": "+79001234567"
  },
  "supplier": {
    "id": "uuid",
    "name": "Flower Base Moscow"
  },
  "items": [
    {
      "id": "uuid",
      "offer_id": "uuid",
      "normalized_sku_id": "uuid",
      "quantity": 10,
      "unit_price": "100.00",
      "total_price": "1000.00",
      "notes": null
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/orders/{uuid}
```

**Status codes**:
- 200: Success
- 404: Order not found

---

## Supplier Orders (Admin)

### List Supplier Orders

**Endpoint**: `GET /admin/suppliers/{supplier_id}/orders`

**Description**: List orders for a supplier (supplier admin endpoint).

**Query parameters**:
- `status` (optional): Filter by status (pending, confirmed, rejected, cancelled)
- `limit` (optional, default 50): Max results
- `offset` (optional, default 0): Pagination offset

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "buyer_id": "uuid",
    "status": "pending",
    "total_amount": "1000.00",
    "currency": "RUB",
    "delivery_address": "456 Oak Street",
    "delivery_date": "2025-01-15",
    "notes": null,
    "created_at": "2025-01-12T10:00:00Z",
    "confirmed_at": null,
    "rejected_at": null,
    "rejection_reason": null,
    "buyer": {
      "id": "uuid",
      "name": "Flower Shop Moscow",
      "phone": "+79001234567"
    },
    "items_count": 2
  }
]
```

**Example**:
```bash
curl "http://localhost:8000/admin/suppliers/{uuid}/orders?status=pending"
```

**Status codes**:
- 200: Success
- 404: Supplier not found

---

### Confirm Order

**Endpoint**: `POST /admin/suppliers/{supplier_id}/orders/confirm`

**Description**: Confirm an order (supplier action).

**Request body**:
```json
{
  "order_id": "uuid"
}
```

**Response** (200 OK):
```json
{
  "order_id": "uuid",
  "status": "confirmed",
  "confirmed_at": "2025-01-12T11:00:00Z",
  "rejected_at": null,
  "rejection_reason": null
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/suppliers/{supplier_id}/orders/confirm \
  -H "Content-Type: application/json" \
  -d '{"order_id": "uuid-here"}'
```

**Status codes**:
- 200: Success
- 400: Order cannot be confirmed (wrong status, wrong supplier)
- 404: Order not found

**Notes**:
- Only orders in `pending` status can be confirmed
- Order must belong to the specified supplier
- Sets `confirmed_at` timestamp
- Status transition: `pending` → `confirmed`

---

### Reject Order

**Endpoint**: `POST /admin/suppliers/{supplier_id}/orders/reject`

**Description**: Reject an order with reason (supplier action).

**Request body**:
```json
{
  "order_id": "uuid",
  "reason": "Out of stock"
}
```

**Response** (200 OK):
```json
{
  "order_id": "uuid",
  "status": "rejected",
  "confirmed_at": null,
  "rejected_at": "2025-01-12T11:00:00Z",
  "rejection_reason": "Out of stock"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/suppliers/{supplier_id}/orders/reject \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "uuid-here",
    "reason": "Out of stock"
  }'
```

**Status codes**:
- 200: Success
- 400: Order cannot be rejected (wrong status, wrong supplier)
- 404: Order not found

**Notes**:
- Only orders in `pending` status can be rejected
- Order must belong to the specified supplier
- Sets `rejected_at` timestamp and `rejection_reason`
- Status transition: `pending` → `rejected`

---

### Get Supplier Order Metrics

**Endpoint**: `GET /admin/suppliers/{supplier_id}/orders/metrics`

**Description**: Get order statistics for supplier (supplier admin endpoint).

**Response** (200 OK):
```json
{
  "total_orders": 150,
  "pending": 25,
  "confirmed": 100,
  "rejected": 20,
  "cancelled": 5,
  "total_revenue": "150000.00"
}
```

**Example**:
```bash
curl http://localhost:8000/admin/suppliers/{uuid}/orders/metrics
```

**Status codes**:
- 200: Success
- 404: Supplier not found

**Notes**:
- `total_revenue`: Sum of confirmed order amounts (Decimal)
- Metrics filtered by supplier
- All counts and revenue are real-time aggregates

---

## Admin Order Metrics

### Get Global Order Metrics

**Endpoint**: `GET /admin/orders/metrics`

**Description**: Get global order statistics across all suppliers (admin endpoint).

**Response** (200 OK):
```json
{
  "total_orders": 500,
  "pending": 75,
  "confirmed": 350,
  "rejected": 60,
  "cancelled": 15,
  "total_revenue": "500000.00"
}
```

**Example**:
```bash
curl http://localhost:8000/admin/orders/metrics
```

**Notes**:
- `total_revenue`: Sum of all confirmed order amounts across all suppliers
- Global metrics (not filtered by supplier)
- Useful for platform-wide dashboards

---

## Error Responses

All endpoints follow consistent error format:

```json
{
  "detail": "Error message"
}
```

**Common status codes**:
- 400: Bad Request (invalid input, validation error)
- 404: Not Found (resource doesn't exist)
- 409: Conflict (constraint violation)
- 500: Internal Server Error (unexpected failure)

---

## Rate Limiting

**MVP**: No rate limiting.
**Production**: Add rate limiting per client/IP.

---

## OpenAPI Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Workflow Examples

### Complete Normalization Workflow

```bash
# 1. Bootstrap dictionary
curl -X POST http://localhost:8000/admin/dictionary/bootstrap

# 2. Create normalized SKUs
curl -X POST http://localhost:8000/admin/skus \
  -H "Content-Type: application/json" \
  -d '{"product_type": "rose", "variety": "Explorer", "title": "Rose Explorer"}'

# 3. Import CSV
curl -X POST http://localhost:8000/admin/suppliers/{id}/imports/csv \
  -F "file=@price_list.csv"

# 4. Propose mappings
curl -X POST http://localhost:8000/admin/normalization/propose \
  -H "Content-Type: application/json" \
  -d '{"supplier_id": "uuid-here"}'

# 5. Review tasks
curl http://localhost:8000/admin/normalization/tasks?status=open

# 6. Confirm mapping
curl -X POST http://localhost:8000/admin/normalization/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_item_id": "uuid-here",
    "normalized_sku_id": "uuid-here",
    "notes": "Confirmed"
  }'

# 7. Publish offers
curl -X POST http://localhost:8000/admin/publish/suppliers/{id}

# 8. Query offers
curl "http://localhost:8000/offers?product_type=rose"
```

---

## Version History

- **v0.6.0** (2026-02-06): Добавлены Import History endpoints — список импортов, ошибки парсинга, удаление, перепарсинг
- **v0.5.0** (2026-02-05): Добавлен Flower Catalog API — иерархический справочник типов/субтипов/сортов цветов
- **v0.4.0** (2026-02-03): Документация расширена: аутентификация, таблица содержания, русский язык
- **v0.3.0** (2025-01-13): Task 3 complete - Order flow (buyers, orders, supplier order management)
- **v0.2.0** (2025-01-12): Task 2 complete - Normalization and publishing
- **v0.1.0** (2025-01-10): Task 1 complete - Import pipeline

---

## Связанные документы

- [ARCHITECTURE.md](ARCHITECTURE.md) — общая архитектура системы
- [WORKFLOWS.md](WORKFLOWS.md) — бизнес-процессы
- [DATA_LIFECYCLE.md](DATA_LIFECYCLE.md) — жизненный цикл данных
- [NORMALIZATION_RULES.md](NORMALIZATION_RULES.md) — правила нормализации
- [FAILURE_MODES.md](FAILURE_MODES.md) — обработка ошибок

---

## OpenAPI Documentation

Интерактивная документация доступна по адресам:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
