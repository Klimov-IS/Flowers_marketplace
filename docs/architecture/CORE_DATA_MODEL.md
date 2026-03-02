# 🧩 CORE_DATA_MODEL — B2B Flower Market Platform (MVP)

## 0) Цель документа

Зафиксировать:
- ключевые **сущности** и **связи**,
- **слои данных** (raw → parsed → normalized → published),
- базовые **инварианты** (что является “истиной”, что версионируется),
- модель, которая покрывает реальные прайсы поставщиков:
  - простые списки `Наименование/Цена`,
  - иерархии “категория → позиции”,
  - **матрицы цен** (длина × тип упаковки),
  - **тиры по объёму** (“от 100 до 200 шт”),
  - **диапазоны цен** (95–99).

---

## 1) Глоссарий

- **Raw** — исходные данные “как есть” (файл, строки, ячейки). Не редактируется.
- **Parsed** — типизированные поля, извлечённые из raw (price, length_cm, pack_qty…).
- **Normalized SKU** — единый стандартный товар (каноническая карточка), к которому маппятся позиции поставщиков.
- **Supplier Item** — позиция поставщика в его нотации (как в прайсе).
- **Offer** — коммерческое предложение: *Supplier + SKU + упаковка/длина/тиры + цена(+наличие)*.
- **Published Offer** — оффер, доступный рознице в поиске (после нормализации/валидации).

---

## 2) Слои данных и инварианты

### 2.1 RAW (источник истины по импорту)
**Содержит:**
- файл (метаданные),
- импорт-партию,
- строки/ячейки (в JSON/массиве),
- ссылки на источник (sheet/page/row).

**Инварианты:**
- Raw **не меняем** никогда.
- Любые исправления → через parsed/normalized, но с линком на raw.

---

### 2.2 PARSED (типизированные факты)
**Содержит:**
- извлечённые поля из raw: name, group, price, price_range, length_cm, pack_type, pack_qty, tier rules и т.д.
- результат “раскрытия” матриц/тиров:
  - одна raw-строка может породить **несколько parsed-элементов**.

**Инварианты:**
- Parsed версионируется по `import_batch_id` и `parse_run_id`.
- Ошибки парсинга сохраняются как события (не “теряем” строки).

---

### 2.3 NORMALIZED (единый каталог + маппинг)
**Содержит:**
- `normalized_sku` (канонические карточки),
- словари/синонимы/правила,
- таблицу соответствий `supplier_item → normalized_sku` с confidence.

**Инварианты:**
- Нормализация — это отдельный слой, допускающий ручной разбор и переобучение правил.
- Для каждого соответствия храним: метод, confidence, кто подтвердил, когда.

---

### 2.4 PUBLISHED (то, что видит розница)
**Содержит:**
- финальные `offers`, прошедшие валидацию и маппинг,
- снабжённые условиями (доставка/минималка),
- актуальные цены/тиры.

**Инварианты:**
- Published = функция от (latest valid price_list + mapping + delivery rules).
- Можно быстро пересобрать published при изменении словаря.

---

## 3) Сущности MVP и связи (концептуальная ER-модель)

### 3.1 Контрагенты и доступ

#### `supplier` (Оптовая база)
- id
- name
- city_id
- status (pending/active/blocked)
- contacts (json)

#### `buyer` (Розница)
- id
- name
- city_id
- status
- contacts (json)

#### `telegram_link` (Привязка Telegram → платформа)
Связь между Telegram-пользователем и сущностью платформы (supplier/buyer).
- id (UUID)
- telegram_user_id (BigInteger, unique) — ID пользователя в Telegram
- telegram_chat_id (BigInteger) — ID чата
- role (String(20)) — 'supplier' или 'buyer'
- entity_id (UUID) — FK на supplier.id или buyer.id
- username (String(100), nullable) — @username в Telegram
- first_name (String(100), nullable)
- is_active (Boolean, default true)
- created_at, updated_at

**Индексы:** `(role, entity_id)`, `(telegram_chat_id)`

**Связь:** один Telegram-пользователь может быть привязан только к одной сущности (unique по telegram_user_id).

#### `password_reset_code` (Коды сброса пароля)
Одноразовые 6-значные коды, отправляемые через Telegram-бота для восстановления пароля.
- id (UUID)
- user_id (UUID) — FK на supplier.id или buyer.id
- role (String(20)) — 'supplier' или 'buyer'
- code_hash (String(64)) — SHA-256 хеш кода (код не хранится в открытом виде)
- telegram_chat_id (BigInteger) — куда отправлен (для аудита)
- expires_at (TimestampTZ) — TTL 10 минут
- attempts (Integer, default 0) — счётчик неудачных попыток (макс 5)
- used_at (TimestampTZ, nullable) — когда использован
- created_at (TimestampTZ)

**Индексы:** `(user_id, role)`

**Безопасность:** rate limit 3 кода за 15 мин на email, блокировка после 5 неверных попыток.

*(Auth/users можно держать отдельным сервисом — здесь только доменные сущности.)*

---

### 3.2 Импорт и RAW слой

#### `import_batch`
Одна загрузка прайса поставщиком (или админом).
- id
- supplier_id
- source_type (csv/xlsx/pdf/image/api)
- source_filename
- imported_at
- declared_effective_date (если поставщик указал)
- status (received/parsed/published/failed)

#### `raw_row`
Строки/ячейки “как есть”.
- id
- import_batch_id
- row_kind (data/header/group/comment/empty)
- raw_cells_json (array/object)
- raw_text (конкат для поиска/дебага)
- row_ref (sheet/page/row)

#### `parse_run`
- id
- import_batch_id
- parser_version
- started_at / finished_at
- summary_json (сколько строк, сколько ошибок)

#### `parse_event` (ошибки/предупреждения)
- id
- parse_run_id
- raw_row_id
- severity (info/warn/error)
- code (например: MATRIX_HEADER_NOT_FOUND)
- message
- payload_json

---

### 3.3 PARSED слой (позиции поставщика)

#### `supplier_item`
Нормализованная “позиция поставщика” как объект, к которому потом будет маппинг.
- id
- supplier_id
- import_batch_id (последняя версия/источник)
- raw_name
- raw_group (страна/категория/раздел, если есть)
- name_norm (нормализованный текст для матчинг-поиска)
- attributes_json (всё, что извлекли: страна, бренд, сорт и т.п.)
- status (active/ambiguous/rejected)

**Зачем отдельный supplier_item:**
- одна и та же позиция может приходить в разных прайсах,
- это “узел” для нормализации.

#### `offer_candidate`
“Кандидат оффера” — то, что получается после раскрытия матриц/тиров.
- id
- supplier_item_id
- import_batch_id
- length_cm (nullable)
- pack_type (nullable: бак/упак/…)
- pack_qty (nullable: 10/20/25…)
- price_type (fixed/range)
- price_min / price_max
- currency (RUB)
- tier_min_qty / tier_max_qty (nullable)
- availability_type (unknown/in_stock/preorder)
- stock_qty (nullable)
- validation_status (ok/warn/error)
- validation_notes

**Важно:**  
raw “матрица” → много `offer_candidate` по (length_cm × pack_type).  
raw “тиры” → много `offer_candidate` по диапазонам qty.

---

### 3.4 NORMALIZED слой (каталог + словари)

#### Иерархический каталог цветов (NEW)

Структура справочника типов/субтипов/сортов:

```
flower_categories (опционально)
    └── flower_types (Роза, Хризантема, Эвкалипт)
          ├── flower_subtypes (Кустовая, Спрей, Пионовидная)
          │     └── subtype_synonyms
          ├── type_synonyms (роза, розы, rose → Роза)
          └── flower_varieties (Explorer, Freedom, Red Naomi)
                └── variety_synonyms (эксплорер → Explorer)
```

#### `flower_category`
Категории верхнего уровня (опционально).
- id
- name (Срезанные цветы / Зелень / Сухоцветы)
- slug (cut-flowers / greenery / dried)
- sort_order

#### `flower_type`
Тип цветка (основной справочник).
- id
- category_id (FK, nullable)
- canonical_name (Роза)
- slug (rosa)
- meta (JSONB: avg_length_min, avg_length_max, etc.)
- is_active

#### `flower_subtype`
Субтип цветка (кустовая, спрей, пионовидная).
- id
- type_id (FK → flower_types)
- name (Кустовая)
- slug (shrub)
- meta (JSONB)
- is_active

#### `type_synonym` / `subtype_synonym`
Синонимы для типов/субтипов.
- id
- type_id / subtype_id (FK)
- synonym (lowercase: "розы", "rose", "кустовая")
- priority (для сортировки при конфликтах)

**CONSTRAINT**: synonym UNIQUE — один синоним может указывать только на один тип.

#### `flower_variety`
Справочник известных сортов.
- id
- type_id (FK → flower_types, required)
- subtype_id (FK → flower_subtypes, nullable)
- name (Explorer)
- slug (explorer)
- official_colors (ARRAY: ["красный"])
- typical_length_min / typical_length_max
- meta (JSONB)
- is_verified (bool: проверено экспертом)
- is_active

#### `variety_synonym`
Синонимы сортов.
- id
- variety_id (FK)
- synonym (lowercase: "эксплорер")
- priority

**Триграмный индекс**: `flower_varieties.name` для fuzzy search.

---

#### `normalized_sku`
Каноническая карточка товара.
- id
- product_type (rose/carnation/alstroemeria/greens/packaging/…)
- variety (nullable) — сорт/линейка (если ведём)
- color (nullable)
- length_cm (nullable) — если длина является атрибутом SKU, либо переносим длину в offer
- stem_count / bud_type / grade (nullable — на будущее)
- title (человекочитаемо)
- search_tokens (tsvector/json)

> MVP-рекомендация: **длину держать в Offer**, а не в SKU.
SKU = "что это", Offer = "в каких параметрах продаётся".

#### `dictionary_entry`
Универсальная модель словаря/синонимов/правил.
- id
- dict_type (product_type/color/variety/country/pack_type/stopwords/regex_rule)
- key
- value
- synonyms (array)
- rules_json (regex/replace/extract)
- status (active/deprecated)

> **Note**: `dictionary_entry` остаётся для обратной совместимости и хранения цветов/стран.
> Типы цветов теперь управляются через `flower_types` + `type_synonyms`.

#### `sku_mapping`
Соответствие supplier_item → normalized_sku.
- id
- supplier_item_id
- normalized_sku_id
- method (rule/manual/semantic)
- confidence (0..1)
- status (proposed/confirmed/rejected)
- decided_by (user_id nullable)
- decided_at
- notes

#### `normalization_task` (ручной разбор)
- id
- supplier_item_id
- reason (unknown_product/ambiguous/needs_dictionary/…)
- priority
- status (open/in_progress/done)
- assigned_to

---

### 3.5 PUBLISHED слой (офферы для поиска и заказов)

#### `offer`
Финальный оффер, доступный для розницы.
- id
- supplier_id
- normalized_sku_id
- source_import_batch_id (откуда опубликовано)
- length_cm (nullable)
- pack_type (nullable)
- pack_qty (nullable)
- price_type (fixed/range)
- price_min / price_max
- currency
- tier_min_qty / tier_max_qty (nullable)
- is_active
- published_at

> Offer создаётся из `offer_candidate` только если:
> - `sku_mapping.status=confirmed`
> - `offer_candidate.validation_status=ok|warn` (по правилам)
> - supplier активен

#### `supplier_delivery_rule`
Условия поставщика.
- id
- supplier_id
- city_id
- delivery_zone (geojson/enum)
- min_order_amount (nullable)
- min_order_qty (nullable)
- delivery_windows (json)
- notes

---

### 3.6 Заказы (минимальный контур для MVP)

#### `order`
- id
- buyer_id
- city_id
- status (draft/sent/accepted/rejected/partial/completed/canceled)
- created_at
- notes

#### `order_line`
- id
- order_id
- offer_id
- qty
- unit_price (фиксируем на момент заказа)
- line_amount

#### `order_supplier_link`
Так как один заказ может включать несколько поставщиков.
- id
- order_id
- supplier_id
- status (sent/accepted/rejected/partial)
- supplier_notes

#### `order_event`
история статусов.
- id
- order_id
- entity_type (order/order_supplier_link)
- from_status / to_status
- at
- payload_json

---

## 4) Ключевые моделинговые решения (принятые для MVP)

1) **Offer — главный коммерческий объект.**  
   Цена зависит от (длина, упаковка, кратность, объём), поэтому это не SKU.

2) **Поддерживаем 3 схемы цены:**
   - fixed,
   - range (min/max),
   - tiers (qty ranges) через строки Offer с tier_min/max.

3) **Матрицы раскрываем в “плоские” OfferCandidate.**  
   Это упрощает поиск/фильтры и не требует хранения “матрицы” как отдельного типа.

4) **Raw неизменяем.**  
   Любые правки — через словарь/маппинг/перепубликацию.

5) **Нормализация управляемая (dictionary-driven) + manual-review queue.**

---

## 5) Поток данных (Data-flow)

1) Supplier загружает прайс → создаётся `import_batch`
2) Файл режется на `raw_row` (включая group/header lines)
3) `parse_run` создаёт:
   - `supplier_item` (стабильные позиции),
   - `offer_candidate` (раскрытие матриц/тиров)
4) Нормализация:
   - правила/словарь предлагают `sku_mapping (proposed)`
   - админ подтверждает → `confirmed`
5) Публикация:
   - из `offer_candidate` + `sku_mapping confirmed` создаются `offers`
6) Розница ищет/собирает корзину → `order`, `order_line`
7) Поставщик подтверждает/отклоняет → `order_event`

---

## 6) Минимальные требования к поиску/фильтрам (из модели)

Фильтры, которые модель покрывает:
- product_type (роза/…)
- length_cm
- price (min/max)
- supplier distance/zone (через delivery rules)
- pack_type / pack_qty (если нужно)

---

## 7) Что сознательно отложено (в DDL будет помечено как optional)

- настоящие остатки “в реальном времени” (пока snapshots/unknown)
- интеграции API/1С
- ML-матчинг (пока rule/manual)
- продвинутая логистика (маршрутизация, тарифы)
- платежи/комиссии/биллинг