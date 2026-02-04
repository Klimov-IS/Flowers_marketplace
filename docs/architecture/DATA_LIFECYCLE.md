# DATA_LIFECYCLE.md — Жизненный цикл данных

## Обзор

Этот документ описывает жизненные циклы всех ключевых сущностей системы:
- State machines для каждой сущности
- Переходы между статусами
- Политики архивирования и retention

---

## 1. ImportBatch — Загрузка прайса

### 1.1 State Machine

```
                    ┌─────────────┐
                    │  received   │  ← Файл загружен, ждёт парсинга
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  parsing    │  ← В процессе парсинга
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐     │     ┌──────▼──────┐
       │   parsed    │     │     │   failed    │  ← Критическая ошибка
       └──────┬──────┘     │     └─────────────┘
              │            │
              │     ┌──────▼──────┐
              │     │ partially   │  ← Частично распарсен (есть ошибки)
              │     │   parsed    │
              │     └──────┬──────┘
              │            │
              └─────┬──────┘
                    │
             ┌──────▼──────┐
             │ publishing  │  ← В процессе публикации
             └──────┬──────┘
                    │
              ┌─────┴─────┐
              │           │
       ┌──────▼──────┐  ┌─▼───────────┐
       │  published  │  │ publish_    │
       └─────────────┘  │   failed    │
                        └─────────────┘
```

### 1.2 Статусы

| Статус | Описание | Следующие |
|--------|----------|-----------|
| `received` | Файл загружен в систему | parsing |
| `parsing` | Идёт парсинг CSV | parsed, partially_parsed, failed |
| `parsed` | Успешно распарсен | publishing |
| `partially_parsed` | Распарсен с ошибками | publishing |
| `failed` | Критическая ошибка парсинга | (терминальный) |
| `publishing` | Идёт публикация офферов | published, publish_failed |
| `published` | Офферы опубликованы | (терминальный) |
| `publish_failed` | Ошибка публикации | publishing (retry) |

### 1.3 Триггеры переходов

```python
# received → parsing
def start_parsing(batch_id: UUID):
    batch.status = "parsing"
    batch.parsing_started_at = datetime.utcnow()

# parsing → parsed
def complete_parsing(batch_id: UUID, stats: ParseStats):
    if stats.errors == 0:
        batch.status = "parsed"
    elif stats.success_rate > 0.5:
        batch.status = "partially_parsed"
    else:
        batch.status = "failed"
    batch.parsing_completed_at = datetime.utcnow()

# parsed → publishing
def start_publishing(batch_id: UUID):
    batch.status = "publishing"
    batch.publishing_started_at = datetime.utcnow()

# publishing → published
def complete_publishing(batch_id: UUID, offer_count: int):
    batch.status = "published"
    batch.offers_published = offer_count
    batch.publishing_completed_at = datetime.utcnow()
```

---

## 2. RawRow — Сырые данные

### 2.1 Жизненный цикл

```
┌─────────────┐
│   created   │  ← Создан при парсинге ImportBatch
└─────────────┘
      │
      │ (IMMUTABLE - никогда не меняется!)
      │
      ▼
┌─────────────┐
│  archived   │  ← Перемещён в архив (retention policy)
└─────────────┘
```

### 2.2 Принципы

1. **IMMUTABLE** — RawRow НИКОГДА не модифицируется после создания
2. **Audit trail** — сохраняет оригинальные данные для debug/audit
3. **Связь** — всегда привязан к ImportBatch и SupplierItem (если создан)

### 2.3 Retention Policy

| Тип | Срок хранения | Действие |
|-----|---------------|----------|
| Active batches | Бессрочно | Хранить |
| Old batches (>6 months) | 6 месяцев | Архивировать в cold storage |
| Failed batches | 30 дней | Удалить |

---

## 3. SupplierItem — Позиция поставщика

### 3.1 State Machine

```
┌─────────────┐
│   created   │  ← Новая позиция (первый импорт)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   active    │  ← Есть в последнем прайсе
└──────┬──────┘
       │
       │  (новый импорт без этой позиции)
       ▼
┌─────────────┐
│  inactive   │  ← Нет в последнем прайсе
└──────┬──────┘
       │
       │  (появляется снова)
       ▼
┌─────────────┐
│   active    │  ← Реактивирован
└─────────────┘
```

### 3.2 Ключевые поля

| Поле | Назначение |
|------|------------|
| `stable_key` | Уникальный ключ для дедупликации (hash от supplier_id + raw_name + attributes) |
| `is_active` | Есть ли в последнем импорте |
| `last_seen_at` | Когда последний раз видели в импорте |
| `first_seen_at` | Когда впервые появился |

### 3.3 Stable Key Algorithm

```python
def generate_stable_key(
    supplier_id: UUID,
    raw_name: str,
    length_cm: Optional[int],
    pack_qty: Optional[int],
    country: Optional[str]
) -> str:
    """
    Генерирует стабильный ключ для дедупликации.

    Изменение алгоритма → дубликаты в БД!
    """
    normalized = raw_name.lower().strip()
    # Remove extra spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    parts = [
        str(supplier_id),
        normalized,
        str(length_cm or ""),
        str(pack_qty or ""),
        (country or "").lower()
    ]

    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]
```

---

## 4. OfferCandidate — Кандидат на оффер

### 4.1 State Machine

```
┌─────────────┐
│   pending   │  ← Создан после парсинга
└──────┬──────┘
       │
       │  (нормализация)
       ▼
┌─────────────┐
│  processed  │  ← Нормализация завершена (есть SKUMapping)
└──────┬──────┘
       │
       │  (публикация + mapping confirmed)
       ▼
┌─────────────┐
│  published  │  ← Оффер опубликован
└─────────────┘

       │
       │  (ошибка парсинга цены/qty)
       ▼
┌─────────────┐
│   failed    │  ← Невалидные данные
└─────────────┘
```

### 4.2 Статусы

| Статус | Описание | Может публиковаться? |
|--------|----------|---------------------|
| `pending` | Ждёт нормализации | Нет |
| `processed` | Нормализация done | Да (если mapping confirmed) |
| `published` | Оффер создан | — |
| `failed` | Ошибка данных | Нет |

### 4.3 Связи

```
OfferCandidate
    │
    ├── import_batch_id → ImportBatch
    │
    ├── supplier_item_id → SupplierItem
    │       │
    │       └── sku_mapping → NormalizedSKU
    │
    └── offer_id → Offer (после публикации)
```

---

## 5. SKUMapping — Маппинг на канонический SKU

### 5.1 State Machine

```
┌─────────────┐
│  proposed   │  ← Автоматически предложен
└──────┬──────┘
       │
       ├───────────────────┐
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  confirmed  │     │  rejected   │
└─────────────┘     └──────┬──────┘
                           │
                           │  (переназначен на другой SKU)
                           ▼
                    ┌─────────────┐
                    │  confirmed  │
                    └─────────────┘
```

### 5.2 Статусы

| Статус | Описание | Влияние на публикацию |
|--------|----------|----------------------|
| `proposed` | Предложен автоматически | Не публикуется |
| `confirmed` | Подтверждён оператором | Публикуется |
| `rejected` | Отклонён (неверный SKU) | Не публикуется |

### 5.3 Confidence Score

```
┌─────────────────────────────────────────────┐
│           Confidence Score Rules            │
├─────────────────────────────────────────────┤
│                                             │
│  ≥ 0.9  ──▶  Auto-confirm (опционально)    │
│                                             │
│  0.7-0.9 ──▶  Proposed, ждёт review        │
│                                             │
│  < 0.7  ──▶  NormalizationTask создан      │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 6. NormalizationTask — Задача на ручной review

### 6.1 State Machine

```
┌─────────────┐
│   pending   │  ← Создан (low confidence или ambiguous)
└──────┬──────┘
       │
       ├───────────────────┬───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  resolved   │     │   skipped   │     │  escalated  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 6.2 Статусы

| Статус | Описание |
|--------|----------|
| `pending` | Ждёт review |
| `resolved` | Маппинг подтверждён/изменён |
| `skipped` | Пропущен (решим позже) |
| `escalated` | Передан senior-оператору |

### 6.3 Task Types

| Тип | Причина создания |
|-----|------------------|
| `ambiguous_mapping` | Несколько возможных SKU |
| `low_confidence` | Confidence < 0.7 |
| `new_variety` | Сорт не найден в словаре |
| `unknown_product` | Тип продукта не определён |

---

## 7. NormalizedSKU — Канонический SKU

### 7.1 State Machine

```
┌─────────────┐
│   active    │  ← Используется в маппингах
└──────┬──────┘
       │
       │  (слияние с другим SKU)
       ▼
┌─────────────┐
│   merged    │  ← Объединён, есть redirect
└─────────────┘
       │
       │  (все ссылки перенаправлены)
       ▼
┌─────────────┐
│  deprecated │  ← Больше не используется
└─────────────┘
```

### 7.2 Merge Logic

При объединении дублирующихся SKU:

```python
def merge_skus(source_sku_id: UUID, target_sku_id: UUID):
    """
    Объединяет два SKU.

    source → будет помечен как merged
    target → остаётся active
    """
    # 1. Перенаправить все маппинги
    UPDATE sku_mappings
    SET normalized_sku_id = target_sku_id
    WHERE normalized_sku_id = source_sku_id

    # 2. Перенаправить все офферы
    UPDATE offers
    SET normalized_sku_id = target_sku_id
    WHERE normalized_sku_id = source_sku_id

    # 3. Пометить source как merged
    UPDATE normalized_skus
    SET status = 'merged', merged_into_id = target_sku_id
    WHERE id = source_sku_id
```

---

## 8. Offer — Публичный оффер

### 8.1 State Machine

```
┌─────────────┐
│   active    │  ← Виден покупателям
└──────┬──────┘
       │
       │  (новый импорт того же поставщика)
       ▼
┌─────────────┐
│  inactive   │  ← Скрыт (устаревший прайс)
└──────┬──────┘
       │
       │  (retention policy)
       ▼
┌─────────────┐
│  archived   │  ← В архиве
└─────────────┘
```

### 8.2 Правила активации

1. **Один активный batch** — при публикации нового прайса:
   - Все старые офферы поставщика → `is_active = false`
   - Новые офферы → `is_active = true`

2. **Только confirmed mappings** — оффер создаётся только если:
   - `sku_mapping.status = 'confirmed'`

### 8.3 Retention

| Возраст | Статус | Действие |
|---------|--------|----------|
| 0-7 дней | active | Показывать |
| 7-30 дней | inactive | Хранить для истории |
| 30-90 дней | inactive | Архивировать |
| >90 дней | archived | Удалить из основной БД |

---

## 9. Order — Заказ

### 9.1 State Machine

```
                    ┌─────────────┐
                    │   pending   │  ← Создан покупателем
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐     │     ┌──────▼──────┐
       │  confirmed  │     │     │  cancelled  │  ← Отменён покупателем
       └──────┬──────┘     │     └─────────────┘
              │            │
              │     ┌──────▼──────┐
              │     │  rejected   │  ← Отклонён поставщиком
              │     └─────────────┘
              │
       ┌──────▼──────┐
       │   shipped   │  ← Отправлен
       └──────┬──────┘
              │
       ┌──────▼──────┐
       │  delivered  │  ← Доставлен
       └─────────────┘
```

### 9.2 Статусы

| Статус | Кто меняет | Следующие возможные |
|--------|------------|---------------------|
| `pending` | Система | confirmed, rejected, cancelled |
| `confirmed` | Поставщик | shipped, cancelled |
| `rejected` | Поставщик | (терминальный) |
| `shipped` | Поставщик | delivered |
| `delivered` | Поставщик/Покупатель | (терминальный) |
| `cancelled` | Покупатель | (терминальный) |

### 9.3 Timestamps

| Поле | Когда заполняется |
|------|-------------------|
| `created_at` | При создании |
| `confirmed_at` | pending → confirmed |
| `rejected_at` | pending → rejected |
| `shipped_at` | confirmed → shipped |
| `delivered_at` | shipped → delivered |
| `cancelled_at` | * → cancelled |

---

## 10. Buyer — Покупатель

### 10.1 State Machine

```
┌─────────────┐
│  registered │  ← Зарегистрирован
└──────┬──────┘
       │
       │  (подтверждение email)
       ▼
┌─────────────┐
│  verified   │  ← Email подтверждён
└──────┬──────┘
       │
       │  (первый заказ)
       ▼
┌─────────────┐
│   active    │  ← Активный покупатель
└──────┬──────┘
       │
       │  (блокировка)
       ▼
┌─────────────┐
│   blocked   │  ← Заблокирован
└─────────────┘
```

---

## 11. User Authentication Lifecycle

### 11.1 Token Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Login     │───▶│  Access     │───▶│   API       │
│   Request   │    │  Token      │    │   Request   │
└─────────────┘    │  (15 min)   │    └─────────────┘
                   └──────┬──────┘
                          │
                          │ (expired)
                          ▼
                   ┌─────────────┐
                   │  Refresh    │
                   │  Token      │
                   │  (7 days)   │
                   └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  New Access │
                   │  Token      │
                   └─────────────┘
```

### 11.2 Token Lifetimes

| Токен | TTL | Обновление |
|-------|-----|------------|
| Access Token | 15 минут | Через refresh token |
| Refresh Token | 7 дней | При login |

---

## 12. Data Archiving Strategy

### 12.1 Hot / Warm / Cold Storage

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           HOT (Primary DB)                               │
│  - Active offers                                                        │
│  - Pending orders                                                       │
│  - Recent import batches (last 30 days)                                │
│  - Active normalization tasks                                           │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    │ (30 days)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           WARM (Archive tables)                          │
│  - Completed orders                                                     │
│  - Published batches                                                    │
│  - Inactive offers                                                      │
│  - Resolved tasks                                                       │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    │ (90 days)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           COLD (Object Storage / S3)                     │
│  - Raw rows (for audit)                                                 │
│  - Old batches                                                          │
│  - Historical offers                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Retention Policies Summary

| Сущность | Hot | Warm | Cold | Delete |
|----------|-----|------|------|--------|
| ImportBatch | 30 дней | 60 дней | 1 год | >1 года |
| RawRow | 30 дней | 60 дней | Бессрочно | Никогда (audit) |
| SupplierItem | Всегда | — | — | Никогда |
| OfferCandidate | 30 дней | 60 дней | 1 год | >1 года |
| Offer | 7 дней active | 90 дней | 1 год | >1 года |
| Order | 30 дней | 1 год | 5 лет | >5 лет |
| NormalizationTask | До resolved | 90 дней | 1 год | >1 года |

---

## 13. Связанные документы

- [ARCHITECTURE.md](ARCHITECTURE.md) — общая архитектура
- [WORKFLOWS.md](WORKFLOWS.md) — бизнес-процессы
- [CORE_DATA_MODEL.md](CORE_DATA_MODEL.md) — модель данных
- [FAILURE_MODES.md](FAILURE_MODES.md) — обработка ошибок
