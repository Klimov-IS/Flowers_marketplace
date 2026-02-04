# FAILURE_MODES.md — Обработка ошибок и восстановление

## Обзор

Этот документ описывает типичные сценарии сбоев, стратегии обработки ошибок и процедуры восстановления для B2B Flower Market Platform.

---

## 1. Категории ошибок

### 1.1 Классификация

| Категория | Описание | Влияние |
|-----------|----------|---------|
| **Transient** | Временные сбои (сеть, timeout) | Retry помогает |
| **Permanent** | Некорректные данные, бизнес-ошибки | Требует fix |
| **System** | Инфраструктура (DB, storage) | Critical |
| **User** | Ошибки ввода, валидации | Информировать пользователя |

### 1.2 Severity Levels

```
CRITICAL  ──▶  Система недоступна, потеря данных
HIGH      ──▶  Основной flow заблокирован
MEDIUM    ──▶  Отдельная функция недоступна
LOW       ──▶  Косметический дефект, workaround есть
```

---

## 2. Import Pipeline Failures

### 2.1 File Upload Errors

| Ошибка | Причина | Handling |
|--------|---------|----------|
| `file_too_large` | Размер > max_size | 400 Bad Request, сообщение пользователю |
| `invalid_mime_type` | Не CSV/XLSX | 400 Bad Request, список допустимых форматов |
| `upload_timeout` | Сеть/сервер медленный | 504 Gateway Timeout, retry |
| `storage_error` | Диск/S3 недоступен | 500 Internal Error, alert |

**Recovery:**
```
1. Пользователь получает понятное сообщение об ошибке
2. Файл не сохраняется частично
3. ImportBatch не создаётся или создаётся со status=failed
```

### 2.2 Encoding Errors

| Ошибка | Причина | Handling |
|--------|---------|----------|
| `unknown_encoding` | Не UTF-8/CP1251/CP866 | Попробовать chardet, иначе fail |
| `decode_error` | Битый файл | Partial parse + warning |

**Стратегия определения кодировки:**

```python
ENCODING_PRIORITY = ["utf-8", "cp1251", "cp866", "latin-1"]

def detect_encoding(content: bytes) -> str:
    for enc in ENCODING_PRIORITY:
        try:
            content.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    raise EncodingError("Unable to detect encoding")
```

### 2.3 CSV Parsing Errors

| Ошибка | Причина | Handling |
|--------|---------|----------|
| `no_headers_found` | Заголовки не распознаны | Fail batch, manual review |
| `column_mismatch` | Разное кол-во колонок в строках | Skip row, log warning |
| `empty_file` | Файл пустой | Fail batch |
| `malformed_csv` | Некорректные кавычки/разделители | Try semicolon, иначе fail |

**Smart Header Detection:**

```python
def detect_header_row(rows: List[List[str]], max_rows: int = 20) -> int:
    """
    Поиск строки с заголовками в первых 20 строках.

    Некоторые прайсы имеют метаданные вверху файла.
    """
    KNOWN_HEADERS = ["наименование", "название", "номенклатура",
                     "цена", "price", "стоимость", "количество"]

    best_idx, best_score = 0, 0
    for idx, row in enumerate(rows[:max_rows]):
        row_text = " ".join(cell.lower() for cell in row if cell)
        score = sum(1 for kw in KNOWN_HEADERS if kw in row_text)
        if score >= 2 and score > best_score:
            best_score = score
            best_idx = idx

    return best_idx
```

### 2.4 Price Parsing Errors

| Ошибка | Причина | Handling |
|--------|---------|----------|
| `invalid_price_format` | "бесплатно", "договорная" | Skip row, log |
| `negative_price` | Отрицательное значение | Skip row, log |
| `price_too_high` | > 1,000,000 | Warning, manual review |
| `range_invalid` | min > max | Swap values, warning |

**Price Parsing Strategy:**

```python
def parse_price(price_str: str) -> dict:
    """
    Парсинг цены с поддержкой русского формата.

    Форматы:
    - "1 699,00" → 1699.00 (русский)
    - "150-200"  → min=150, max=200 (диапазон)
    - "от 100"   → min=100, max=None
    """
    # Remove spaces (thousands separator)
    price_clean = re.sub(r"[\s\u00a0]", "", price_str)
    # Replace comma with dot (Russian decimal)
    price_clean = price_clean.replace(",", ".")

    # Try parse
    try:
        value = Decimal(price_clean)
        return {"price_min": value, "price_max": None, "error": None}
    except:
        return {"price_min": None, "price_max": None, "error": "invalid_format"}
```

---

## 3. Normalization Failures

### 3.1 Dictionary Lookup Errors

| Ошибка | Причина | Handling |
|--------|---------|----------|
| `product_type_not_found` | Новый тип продукта | Low confidence, create task |
| `variety_ambiguous` | Несколько совпадений | Multiple mappings, manual review |
| `conflicting_signals` | Роза + гвоздика в одном названии | Penalty, manual review |

**Recovery:**
```
1. Всегда создаём SKUMapping (даже с низким confidence)
2. Создаём NormalizationTask для ручного разбора
3. Не блокируем pipeline — офферы публикуются после confirm
```

### 3.2 Confidence Too Low

```
Threshold: confidence < 0.70

Actions:
1. Create NormalizationTask(reason="low_confidence")
2. Set priority based on:
   - offer_candidate count
   - supplier importance
   - historical frequency
3. Item appears in admin review queue
```

### 3.3 SKU Creation Failures

| Ошибка | Причина | Handling |
|--------|---------|----------|
| `duplicate_sku` | SKU с такими атрибутами уже есть | Return existing, warn |
| `invalid_product_type` | Неизвестный тип | 400 Bad Request |
| `missing_required` | Нет product_type | 400 Bad Request |

---

## 4. Publishing Failures

### 4.1 Pre-publish Validation

| Проверка | Ошибка | Handling |
|----------|--------|----------|
| Supplier exists | `supplier_not_found` | 404 Not Found |
| Supplier active | `supplier_inactive` | 400 Bad Request |
| Has parsed batch | `no_parsed_imports` | 404 Not Found |
| Has confirmed mappings | `no_confirmed_mappings` | 400, partial publish |

### 4.2 Publish Transaction Failures

```python
async def publish_offers(supplier_id: UUID) -> dict:
    """
    Публикация должна быть атомарной.

    Transaction:
    1. BEGIN
    2. Deactivate old offers
    3. Create new offers
    4. Update batch status
    5. COMMIT

    On failure: ROLLBACK all changes
    """
    async with db.begin():
        # Step 1: Deactivate
        await db.execute(
            update(Offer)
            .where(Offer.supplier_id == supplier_id)
            .where(Offer.is_active == True)
            .values(is_active=False)
        )

        # Step 2: Create new offers
        # ... (may fail on constraint violation)

        # Step 3: Update batch
        batch.status = "published"

    # If any step fails, transaction rolls back
```

### 4.3 Partial Publish

Когда не все offer_candidates имеют confirmed mappings:

```
Result:
{
  "offers_created": 145,
  "skipped_unmapped": 5,
  "status": "partial"
}

User notification:
"Published 145 offers. 5 items skipped (no confirmed mapping)."
```

---

## 5. Order Flow Failures

### 5.1 Order Creation Errors

| Ошибка | Причина | HTTP | Recovery |
|--------|---------|------|----------|
| `buyer_not_found` | Несуществующий buyer_id | 404 | — |
| `buyer_inactive` | Покупатель заблокирован | 400 | Contact support |
| `offer_not_found` | Оффер не существует | 404 | Refresh catalog |
| `offer_inactive` | Оффер деактивирован | 400 | Refresh catalog |
| `multiple_suppliers` | Офферы от разных поставщиков | 400 | Split into multiple orders |
| `quantity_invalid` | qty <= 0 | 400 | Fix input |

### 5.2 Order Status Transition Errors

```
Allowed transitions:

pending → confirmed (supplier)
pending → rejected (supplier)
pending → cancelled (buyer)
confirmed → shipped (supplier)
confirmed → cancelled (buyer, with penalty?)
shipped → delivered (supplier/buyer)

INVALID transitions (400 Bad Request):
- rejected → confirmed
- delivered → * (terminal state)
- cancelled → * (terminal state)
```

### 5.3 Concurrent Order Conflicts

```
Scenario: Two buyers order the same offer simultaneously,
          but stock is limited.

MVP handling:
- No inventory check (assume unlimited stock)
- Supplier confirms/rejects manually

Production handling:
- Optimistic locking on offer.stock_qty
- If conflict: 409 Conflict, "Stock changed, please refresh"
```

---

## 6. Authentication Failures

### 6.1 Token Errors

| Ошибка | HTTP | Body | Recovery |
|--------|------|------|----------|
| Missing Authorization header | 401 | `{"detail": "Not authenticated"}` | Add header |
| Invalid token format | 401 | `{"detail": "Invalid token"}` | Re-login |
| Token expired | 401 | `{"detail": "Token expired"}` | Use refresh token |
| Refresh token expired | 401 | `{"detail": "Refresh token expired"}` | Re-login |
| User not found | 401 | `{"detail": "User not found"}` | Account deleted |
| User inactive | 403 | `{"detail": "Account not active"}` | Contact support |

### 6.2 Token Refresh Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   API Call   │────▶│  401 Expired │────▶│   Refresh    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                            ┌─────────────────────┼─────────────────────┐
                            │                     │                     │
                     ┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐
                     │  New Tokens │       │  401 Invalid│       │  Re-login   │
                     │  Retry API  │       │  Re-login   │       │  Required   │
                     └─────────────┘       └─────────────┘       └─────────────┘
```

---

## 7. Database Failures

### 7.1 Connection Errors

| Ошибка | Причина | Handling |
|--------|---------|----------|
| `connection_refused` | DB не запущена | Retry 3x, then 503 |
| `connection_timeout` | Сеть/нагрузка | Retry with backoff |
| `pool_exhausted` | Все соединения заняты | Queue or 503 |

**Health Check:**

```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": str(e)}
        )
```

### 7.2 Constraint Violations

| Constraint | Error | Handling |
|------------|-------|----------|
| `unique_stable_key` | Duplicate supplier_item | Upsert (update existing) |
| `unique_confirmed_mapping` | Multiple confirmed for same item | Reject, keep existing |
| `fk_supplier_id` | Referenced supplier deleted | 400, "Supplier not found" |

### 7.3 Migration Failures

```
Scenario: Alembic migration fails mid-way

Recovery:
1. Check alembic_version table for current state
2. alembic downgrade -1 (if possible)
3. Fix migration script
4. alembic upgrade head

NEVER:
- Delete alembic_version manually
- Edit already-applied migrations
- Run migrations in production without backup
```

---

## 8. Что ломается при изменениях

### 8.1 Critical Changes

| Изменение | Последствие | Mitigation |
|-----------|-------------|------------|
| Изменение `stable_key` алгоритма | Дубликаты supplier_items | Migration script to recompute keys |
| Изменение confidence weights | Другие результаты нормализации | Re-run propose, review threshold |
| Удаление dictionary entry | Existing mappings break | Soft delete, deprecate first |
| Изменение SKU structure | Broken joins, invalid offers | Migration + republish |
| Изменение Offer schema | Frontend breaks | Version API, deprecation period |

### 8.2 Safe Changes

| Изменение | Безопасно? | Примечания |
|-----------|------------|------------|
| Добавление dictionary entry | ✓ | Immediate effect on new imports |
| Добавление SKU | ✓ | No effect until mapping |
| Добавление поля в model | ✓ | With default, nullable |
| Изменение log format | ✓ | No runtime effect |
| Добавление нового endpoint | ✓ | Backwards compatible |

### 8.3 Breaking Changes Checklist

```markdown
Before deploying breaking change:

□ Database migration prepared and tested
□ Rollback migration prepared
□ API versioning (if public)
□ Frontend updated (if schema changed)
□ Documentation updated
□ Notification to stakeholders
□ Backup created
□ Monitoring alerts configured
```

---

## 9. Logging and Debugging

### 9.1 Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Good: structured, searchable
logger.info(
    "import_completed",
    batch_id=str(batch.id),
    supplier_id=str(batch.supplier_id),
    rows_total=150,
    rows_success=145,
    rows_failed=5,
    duration_ms=1234
)

# Bad: unstructured string
logger.info(f"Import {batch.id} completed: 145/150 rows in 1234ms")
```

### 9.2 Error Logging

```python
try:
    result = await parse_csv(content)
except ParseError as e:
    logger.error(
        "parse_failed",
        batch_id=str(batch_id),
        error_type=type(e).__name__,
        error_message=str(e),
        row_number=e.row_number if hasattr(e, 'row_number') else None
    )
    raise
```

### 9.3 Debug Information in Errors

```python
class ImportError(Exception):
    def __init__(self, message: str, batch_id: UUID, details: dict = None):
        self.batch_id = batch_id
        self.details = details or {}
        super().__init__(message)

# Usage
raise ImportError(
    "Price parsing failed",
    batch_id=batch.id,
    details={
        "row_number": 42,
        "raw_value": "договорная",
        "expected_format": "numeric"
    }
)
```

---

## 10. Recovery Procedures

### 10.1 Re-import CSV

```bash
# If import failed and needs retry
# 1. Check batch status
curl http://localhost:8000/admin/imports/{batch_id}

# 2. If status = "failed", delete batch and retry
# (or keep for audit and create new import)

# 3. Re-upload
curl -X POST http://localhost:8000/admin/suppliers/{id}/imports/csv \
  -F "file=@price.csv"
```

### 10.2 Re-normalize

```bash
# If normalization needs re-run (e.g., dictionary updated)

# 1. Clear proposed mappings (optional)
DELETE FROM sku_mappings
WHERE status = 'proposed'
  AND supplier_item_id IN (SELECT id FROM supplier_items WHERE supplier_id = ?)

# 2. Re-run propose
curl -X POST http://localhost:8000/admin/normalization/propose \
  -H "Content-Type: application/json" \
  -d '{"supplier_id": "..."}'
```

### 10.3 Re-publish

```bash
# If offers need republishing

curl -X POST http://localhost:8000/admin/publish/suppliers/{supplier_id}

# This will:
# 1. Deactivate all old offers
# 2. Create new offers from latest batch
# 3. Only confirmed mappings included
```

### 10.4 Database Recovery

```bash
# If database needs restoration

# 1. Stop API
systemctl stop flower-api

# 2. Restore from backup
pg_restore -d flower_market backup.dump

# 3. Check alembic version
alembic current

# 4. Apply any missing migrations
alembic upgrade head

# 5. Start API
systemctl start flower-api

# 6. Verify health
curl http://localhost:8000/health
```

---

## 11. Monitoring Alerts

### 11.1 Critical Alerts

| Metric | Threshold | Action |
|--------|-----------|--------|
| API error rate | > 5% | Page on-call |
| DB connection failures | > 3 in 1 min | Check DB, restart pool |
| Import failure rate | > 50% | Check encoding, format changes |
| Response time P99 | > 5s | Scale up, optimize queries |

### 11.2 Warning Alerts

| Metric | Threshold | Action |
|--------|-----------|--------|
| Normalization task queue | > 100 pending | Add operator capacity |
| Disk usage | > 80% | Archive old data |
| Token refresh failures | > 10/hour | Check auth service |

---

## 12. Связанные документы

- [ARCHITECTURE.md](ARCHITECTURE.md) — общая архитектура
- [WORKFLOWS.md](WORKFLOWS.md) — бизнес-процессы
- [OPERATIONS.md](OPERATIONS.md) — операционные процедуры
- [ADMIN_API.md](ADMIN_API.md) — API документация
