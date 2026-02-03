# 🌸 B2B Flower Market Platform

Data-first B2B marketplace for wholesale flowers.

## 📋 Overview

This is the MVP implementation of a B2B wholesale flower marketplace. The platform ingests supplier price lists (CSV/XLSX), normalizes data, and provides a unified catalog for retail buyers.

**Core focus**: Data quality and normalization over UI.

## 🏗️ Architecture

```
/apps/api          - FastAPI backend
/packages/core     - Pure parsing logic
/infra            - Docker Compose, database
/docs             - Product documentation
/data/samples     - Test data files
/tests            - Unit & integration tests
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL (via Docker)

### 1. Clone and Setup Environment

```bash
# Copy environment file
cp .env.example .env

# (Optional) Edit .env if needed
# Default values work for local development
```

### 2. Start PostgreSQL

```bash
cd infra
docker compose up -d

# Verify it's running
docker compose ps
```

### 3. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run Database Migrations

```bash
# Apply migrations
alembic upgrade head

# Verify tables created
# You can connect to DB and check:
# psql -h localhost -U flower_user -d flower_market
```

### 5. Start API Server

```bash
# Run with auto-reload
uvicorn apps.api.main:app --reload

# API will be available at:
# http://localhost:8000

# Swagger docs at:
# http://localhost:8000/docs
```

### 6. Create Test Supplier & Import CSV

```bash
# Option A: Via API (recommended)
curl -X POST http://localhost:8000/admin/suppliers \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Flower Base", "contacts": {}}'

# Option B: Via psql
# INSERT INTO suppliers (name, status) VALUES ('Test Flower Base', 'active');

# Import CSV via CLI
python -m apps.api.scripts.import_csv \
  --supplier "Test Flower Base" \
  --file "data/samples/test_price_list.csv"
```

## 📡 API Endpoints

### Health Check

```bash
GET /health
```

### Suppliers

```bash
# Create supplier
POST /admin/suppliers
{
  "name": "Flower Base LLC",
  "city_id": null,
  "contacts": {
    "phone": "+7...",
    "email": "..."
  }
}

# List suppliers
GET /admin/suppliers
```

### Imports

```bash
# Upload CSV price list
POST /admin/suppliers/{supplier_id}/imports/csv
Content-Type: multipart/form-data
file: <CSV file>

# Get import summary
GET /admin/imports/{import_batch_id}
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=apps --cov=packages

# Run with verbose output
pytest -v
```

## 📊 CSV Format (F1)

Supported columns (case-insensitive, Cyrillic/Latin):

- **НАИМЕНОВАНИЕ** (required) - Item name
- **ЦЕНА** (required) - Price (fixed: "100" or range: "95-99")
- **КОЛ-ВО** (optional) - Pack quantity

Example CSV:

```csv
НАИМЕНОВАНИЕ,ЦЕНА,КОЛ-ВО
Роза Explorer 60см (Эквадор),120,10
Роза Mondial 50см,95-99,
Гвоздика Розовая 70см (Голландия),45,25
```

### Attribute Extraction

The parser automatically extracts:

- **Length**: `60см`, `60 см`, `60cm` → `length_cm = 60`
- **Country**: `(Эквадор)`, `(Ecuador)` → `origin_country = "Ecuador"`
- **Pack qty**: `(10)`, `10 шт` → `pack_qty = 10`
- **Price range**: `95-99`, `95–99` → `price_type = "range"`

## 🗄️ Database Schema

Key tables:

- `suppliers` - Wholesale bases
- `import_batches` - Price list uploads
- `raw_rows` - Immutable source data
- `parse_runs` - Parsing executions
- `parse_events` - Errors/warnings
- `supplier_items` - Stable supplier positions
- `offer_candidates` - Parsed offers (ready for normalization)

See `/docs/CORE_DATA_MODEL.md` for details.

## 🔍 Viewing Import Results

```bash
# Via psql
psql -h localhost -U flower_user -d flower_market

# Check import batches
SELECT id, supplier_id, status, imported_at FROM import_batches;

# Check supplier items
SELECT id, raw_name, name_norm, status FROM supplier_items LIMIT 10;

# Check offer candidates
SELECT id, length_cm, price_min, price_max, pack_qty FROM offer_candidates LIMIT 10;

# Check parse events (errors)
SELECT severity, code, message FROM parse_events;
```

## 🐛 Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
cd infra && docker compose ps

# Restart if needed
docker compose restart

# Check logs
docker compose logs postgres
```

### Alembic Errors

```bash
# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
alembic upgrade head
```

### Import Fails

```bash
# Check parse events
SELECT * FROM parse_events ORDER BY created_at DESC LIMIT 10;

# Check logs
# uvicorn outputs structured logs
```

## 📚 Documentation

- `/docs/VISION.md` - Product vision
- `/docs/MVP_SCOPE.md` - MVP scope
- `/docs/CORE_DATA_MODEL.md` - Data model
- `/docs/IMPORT_PIPELINE.md` - Import pipeline
- `/docs/NORMALIZATION_RULES.md` - Normalization rules
- `/CLAUDE.md` - Engineering guidelines

## 🛠️ Development

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type check (if using mypy)
mypy apps packages
```

### Creating Migrations

```bash
# Auto-generate migration from models
alembic revision --autogenerate -m "description"

# Review generated migration
# Edit alembic/versions/xxx_description.py if needed

# Apply
alembic upgrade head
```

## 📝 Task 1 Deliverables Checklist

- ✅ Docker Compose for PostgreSQL
- ✅ FastAPI app with structured logging
- ✅ SQLAlchemy 2.0 models
- ✅ Alembic migrations
- ✅ CSV parser (F1 format)
- ✅ Import pipeline (raw → parsed → supplier_items → offer_candidates)
- ✅ API endpoints (health, suppliers, imports)
- ✅ CLI script for import
- ✅ Unit tests (parsing)
- ✅ Integration test (CSV import)
- ✅ README with run instructions

---

## 🎯 Task 2 - Normalization & Publishing

Task 2 implements dictionary-driven normalization and offer publishing workflow.

### Quick Start

#### 1. Bootstrap Dictionary

Create seed dictionary with product types, countries, stopwords, regex rules, etc:

```bash
curl -X POST http://localhost:8000/admin/dictionary/bootstrap
```

Expected response:
```json
{"created": 35, "updated": 0}
```

#### 2. Create Normalized SKUs

Create canonical product cards (normalized SKUs) for matching:

```bash
# Create Rose Explorer SKU
curl -X POST http://localhost:8000/admin/skus \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "rose",
    "variety": "Explorer",
    "title": "Rose Explorer",
    "meta": {"origin_default": "Ecuador"}
  }'

# Create Carnation SKU
curl -X POST http://localhost:8000/admin/skus \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "carnation",
    "variety": null,
    "title": "Carnation Standard"
  }'
```

#### 3. Import CSV (Task 1)

Already covered in Quick Start above. Creates supplier_items and offer_candidates.

#### 4. Propose Mappings

Run dictionary-driven normalization to propose SKU mappings:

```bash
curl -X POST http://localhost:8000/admin/normalization/propose \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": "uuid-from-step-3"
  }'
```

Expected response:
```json
{
  "processed_items": 150,
  "proposed_mappings": 450,
  "tasks_created": 25
}
```

**What happens:**
- Analyzes each supplier_item
- Extracts attributes (product_type, variety, subtype, country)
- Searches candidate SKUs (exact → generic → similarity)
- Calculates confidence scores (multi-signal algorithm)
- Creates top 5 mappings (confidence > 0.10)
- Creates manual review tasks for low confidence (<0.70)

#### 5. Review Tasks

List normalization tasks for manual review:

```bash
curl "http://localhost:8000/admin/normalization/tasks?status=open&limit=10"
```

Expected response (enriched with context):
```json
{
  "tasks": [
    {
      "id": "uuid",
      "reason": "Low confidence: 0.45",
      "priority": 150,
      "supplier_item": {
        "raw_name": "Роза неизвестная 60см",
        "name_norm": "роза неизвестная 60"
      },
      "proposed_mappings": [
        {
          "normalized_sku_id": "uuid",
          "confidence": 0.45,
          "sku_title": "Rose Standard"
        }
      ],
      "sample_raw_rows": [
        {"raw_text": "Роза неизвестная 60см | 120"}
      ]
    }
  ]
}
```

#### 6. Confirm Mapping

After manual review, confirm correct mapping:

```bash
curl -X POST http://localhost:8000/admin/normalization/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_item_id": "uuid-from-task",
    "normalized_sku_id": "uuid-of-correct-sku",
    "notes": "Confirmed after review - looks correct"
  }'
```

Expected response:
```json
{
  "mapping": {
    "status": "confirmed",
    "confidence": 1.0,
    "method": "manual",
    "decided_at": "2025-01-12T..."
  }
}
```

**What happens:**
- Rejects ALL existing mappings for this supplier_item
- Creates/updates confirmed mapping (confidence=1.0)
- Marks related normalization_task as 'done'
- **Enforces uniqueness**: Only ONE confirmed mapping per supplier_item

#### 7. Publish Offers

Publish offers from confirmed mappings:

```bash
curl -X POST http://localhost:8000/admin/publish/suppliers/{uuid}
```

Expected response:
```json
{
  "supplier_id": "uuid",
  "import_batch_id": "uuid",
  "offers_deactivated": 150,
  "offers_created": 145,
  "skipped_unmapped": 5
}
```

**What happens:**
- Finds latest parsed import_batch
- Deactivates ALL old offers (is_active=false)
- Creates new offers for candidates with confirmed mappings
- Skips candidates without confirmed mapping
- Updates import_batch status to 'published'

#### 8. Query Offers (Retail)

Search published offers:

```bash
# List all offers
curl "http://localhost:8000/offers?limit=10"

# Filter by product type
curl "http://localhost:8000/offers?product_type=rose"

# Full text search
curl "http://localhost:8000/offers?q=explorer"

# Filter by price and length
curl "http://localhost:8000/offers?price_max=150&length_cm=60"

# Pagination
curl "http://localhost:8000/offers?limit=20&offset=40"
```

Expected response:
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
      "price_min": 120.00,
      "currency": "RUB",
      "published_at": "2025-01-12T..."
    }
  ],
  "total": 145
}
```

### Normalization Workflow

```
1. Import CSV
   ↓
   Creates: supplier_items, offer_candidates

2. Propose Mappings
   ↓
   Creates: sku_mappings (proposed), normalization_tasks
   Algorithm:
   - Extract attributes (product_type, variety, subtype, country)
   - Search candidate SKUs (exact/generic/similarity)
   - Calculate confidence scores (multi-signal)
   - Create top 5 mappings + review task if needed

3. Manual Review
   ↓
   Admin reviews tasks and proposed mappings

4. Confirm Mapping
   ↓
   Updates: sku_mapping (status=confirmed)
   Marks: normalization_task (status=done)
   Enforces: Only ONE confirmed per supplier_item

5. Publish Offers
   ↓
   Creates: offers (is_active=true)
   Deactivates: old offers (is_active=false)
   Strategy: Replace-all (simple, predictable)

6. Retail Search
   ↓
   Query: Active offers with filters
```

### Architecture

**Dictionary-driven normalization:**
- `dictionary_entries` - Product types, synonyms, stopwords, regex rules
- Normalization algorithm uses dictionary for attribute extraction
- Confidence scoring based on multiple signals (product_type, variety, subtype, country)

**Manual review queue:**
- Low confidence matches (<0.70) create tasks
- Ambiguous matches (top 2 diff <0.05) create tasks
- Tasks enriched with context (item details, proposed mappings, sample rows)

**Transactional confirm:**
- Atomic operation: reject old → upsert confirmed → mark tasks done
- Database constraint enforces uniqueness (one confirmed per item)

**Replace-all publish:**
- Simple strategy: deactivate all old, create new
- Only publishes candidates with confirmed mappings
- Preserves history (old offers remain with is_active=false)

### Additional Endpoints

See full API documentation: [`/docs/ADMIN_API.md`](docs/ADMIN_API.md)

**Dictionary Management:**
- `POST /admin/dictionary/bootstrap` - Seed dictionary
- `GET /admin/dictionary` - List entries
- `POST /admin/dictionary` - Create entry
- `PATCH /admin/dictionary/{id}` - Update entry

**Normalized SKUs:**
- `POST /admin/skus` - Create SKU
- `GET /admin/skus` - List/search SKUs
- `GET /admin/skus/{id}` - Get SKU

**Normalization:**
- `POST /admin/normalization/propose` - Run normalization
- `GET /admin/normalization/tasks` - List review tasks
- `POST /admin/normalization/confirm` - Confirm mapping

**Publishing:**
- `POST /admin/publish/suppliers/{id}` - Publish offers

**Retail:**
- `GET /offers` - Search offers (public endpoint)

### Testing Task 2

```bash
# Unit tests (normalization logic)
pytest tests/unit/test_normalization_logic.py -v

# Integration tests (endpoints)
pytest tests/integration/test_normalization_endpoints.py -v
pytest tests/integration/test_publish_and_offers.py -v

# End-to-end test (full workflow)
pytest tests/integration/test_task2_e2e.py -v
```

### 📝 Task 2 Deliverables Checklist

- ✅ Database layer (6 new models: NormalizedSKU, DictionaryEntry, SKUMapping, NormalizationTask, Offer, SupplierDeliveryRule)
- ✅ Migration 002 (normalized layer)
- ✅ Dictionary management (bootstrap + CRUD)
- ✅ Normalized SKU management (CRUD)
- ✅ Core normalization logic (tokens, detection, confidence scoring)
- ✅ NormalizationService (propose with dictionary-driven algorithm)
- ✅ Normalization endpoints (propose, tasks, confirm)
- ✅ PublishService (replace-all strategy)
- ✅ Publish endpoint (admin)
- ✅ Offers endpoint (retail search with filters)
- ✅ Unit tests (29 tests for normalization logic)
- ✅ Integration tests (21 tests for endpoints + workflows)
- ✅ End-to-end test (complete workflow)
- ✅ API documentation (ADMIN_API.md)
- ✅ README updated with Task 2 quickstart

---

## 🛒 Task 3 - Order Flow

Task 3 implements complete order workflow: buyers, orders, and supplier order management.

### Quick Start

#### 1. Create Buyer (Admin)

Create a retail buyer account:

```bash
curl -X POST http://localhost:8000/admin/buyers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Flower Shop Moscow",
    "phone": "+79001234567",
    "email": "shop@flowers.ru",
    "address": "123 Main Street",
    "city_id": "uuid-from-cities-table"
  }'
```

Expected response:
```json
{
  "id": "uuid",
  "name": "Flower Shop Moscow",
  "phone": "+79001234567",
  "status": "active",
  "created_at": "2025-01-13T..."
}
```

#### 2. List Available Offers (Retail)

Buyer browses published offers from Task 2:

```bash
# Search for roses
curl "http://localhost:8000/offers?product_type=rose&limit=10"

# Filter by price and length
curl "http://localhost:8000/offers?price_max=150&length_cm=60"
```

Expected response:
```json
{
  "offers": [
    {
      "id": "offer-uuid",
      "supplier": {"id": "uuid", "name": "Flower Base Moscow"},
      "sku": {"product_type": "rose", "variety": "Explorer"},
      "price_min": 100.00,
      "currency": "RUB"
    }
  ]
}
```

#### 3. Create Order (Retail)

Buyer creates an order:

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "uuid-from-step-1",
    "items": [
      {
        "offer_id": "uuid-from-step-2",
        "quantity": 10,
        "notes": "Please pack carefully"
      }
    ],
    "delivery_address": "456 Oak Street",
    "delivery_date": "2025-01-15",
    "notes": "Deliver in the morning"
  }'
```

Expected response:
```json
{
  "id": "order-uuid",
  "buyer_id": "uuid",
  "supplier_id": "uuid",
  "status": "pending",
  "total_amount": "1000.00",
  "currency": "RUB",
  "created_at": "2025-01-13T...",
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
      "offer_id": "uuid",
      "quantity": 10,
      "unit_price": "100.00",
      "total_price": "1000.00"
    }
  ]
}
```

**MVP Constraints:**
- Single-supplier orders only (all items must be from same supplier)
- Price snapshot at order creation (unit_price saved to order_item)
- No inventory check
- No authentication (buyer_id in request body)

#### 4. Supplier Views Orders

Supplier lists their pending orders:

```bash
curl "http://localhost:8000/admin/suppliers/{supplier-uuid}/orders?status=pending"
```

Expected response:
```json
[
  {
    "id": "order-uuid",
    "buyer": {
      "id": "uuid",
      "name": "Flower Shop Moscow",
      "phone": "+79001234567"
    },
    "status": "pending",
    "total_amount": "1000.00",
    "created_at": "2025-01-13T...",
    "items_count": 1
  }
]
```

#### 5. Supplier Confirms Order

Supplier confirms the order:

```bash
curl -X POST http://localhost:8000/admin/suppliers/{supplier-uuid}/orders/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-uuid-from-step-3"
  }'
```

Expected response:
```json
{
  "order_id": "uuid",
  "status": "confirmed",
  "confirmed_at": "2025-01-13T11:00:00Z",
  "rejected_at": null,
  "rejection_reason": null
}
```

**Status transition:** `pending` → `confirmed`

#### 6. Alternative: Supplier Rejects Order

If supplier needs to reject:

```bash
curl -X POST http://localhost:8000/admin/suppliers/{supplier-uuid}/orders/reject \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-uuid",
    "reason": "Out of stock"
  }'
```

Expected response:
```json
{
  "order_id": "uuid",
  "status": "rejected",
  "rejected_at": "2025-01-13T11:00:00Z",
  "rejection_reason": "Out of stock"
}
```

**Status transition:** `pending` → `rejected`

#### 7. Buyer Views Order Status

Buyer checks order details:

```bash
# Get specific order
curl "http://localhost:8000/orders/{order-uuid}"

# List all buyer's orders
curl "http://localhost:8000/orders?buyer_id={buyer-uuid}"

# Filter by status
curl "http://localhost:8000/orders?buyer_id={buyer-uuid}&status=confirmed"
```

#### 8. Admin Views Metrics

Platform admin views order statistics:

```bash
# Global metrics (all suppliers)
curl "http://localhost:8000/admin/orders/metrics"

# Supplier-specific metrics
curl "http://localhost:8000/admin/suppliers/{supplier-uuid}/orders/metrics"
```

Expected response:
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

### Order Workflow

```
1. Buyer browses published offers
   ↓
2. Buyer creates order (pending status)
   ↓
   Validation:
   - Buyer must be active
   - All offers must exist and be active
   - All offers from same supplier (MVP constraint)
   - Quantities must be positive
   - Price snapshot saved to order_item
   ↓
3. Supplier views pending orders
   ↓
4a. Supplier confirms → status: confirmed
    OR
4b. Supplier rejects → status: rejected
   ↓
5. Buyer views updated order status
```

### Architecture

**Order validation:**
- Single-supplier constraint (MVP simplification)
- Active buyer and offer checks
- Price snapshot (prevents historical data corruption)
- No inventory check (MVP)

**Status workflow:**
- `pending` → Initial state after order creation
- `confirmed` → Supplier accepted order
- `rejected` → Supplier declined with reason
- `cancelled` → (Reserved for future buyer cancellation)

**Price handling:**
- `unit_price` snapshot at order creation time
- For range prices: uses average `(price_min + price_max) / 2`
- Stored in `order_items.unit_price` (immutable)
- Order `total_amount` = sum of all items

**No authentication (MVP):**
- Buyer endpoints: buyer_id in request body
- Supplier endpoints: supplier_id in path parameter
- Production: Add JWT auth with buyer/supplier roles

### Additional Endpoints

See full API documentation: [`/docs/ADMIN_API.md`](docs/ADMIN_API.md)

**Buyer Management (Admin):**
- `POST /admin/buyers` - Create buyer
- `GET /admin/buyers` - List buyers
- `GET /admin/buyers/{id}` - Get buyer
- `PATCH /admin/buyers/{id}` - Update buyer

**Orders (Retail):**
- `POST /orders` - Create order
- `GET /orders` - List orders (filter by buyer/supplier/status)
- `GET /orders/{id}` - Get order details

**Supplier Orders (Admin):**
- `GET /admin/suppliers/{id}/orders` - List supplier's orders
- `POST /admin/suppliers/{id}/orders/confirm` - Confirm order
- `POST /admin/suppliers/{id}/orders/reject` - Reject order with reason
- `GET /admin/suppliers/{id}/orders/metrics` - Supplier order statistics

**Order Metrics (Admin):**
- `GET /admin/orders/metrics` - Global order statistics

### Testing Task 3

```bash
# Unit tests (order validation)
pytest tests/unit/test_order_validation.py -v

# Integration tests (order flow)
pytest tests/integration/test_order_flow.py -v

# All tests
pytest -v
```

### 📝 Task 3 Deliverables Checklist

- ✅ Database layer (3 new models: Buyer, Order, OrderItem)
- ✅ Migration 003 (buyers, orders, order_items tables)
- ✅ OrderService (create, confirm, reject, metrics)
- ✅ Buyer management endpoints (admin: POST, GET, PATCH)
- ✅ Order endpoints (retail: POST create, GET list/details)
- ✅ Supplier order endpoints (admin: list, confirm, reject, metrics)
- ✅ Order metrics endpoints (admin: global + per-supplier)
- ✅ Price snapshot logic (unit_price saved at order time)
- ✅ Single-supplier validation (MVP constraint)
- ✅ Status workflow (pending → confirmed/rejected)
- ✅ Unit tests (13+ tests for order validation)
- ✅ Integration tests (13+ tests for order flow)
- ✅ API documentation (ADMIN_API.md updated)
- ✅ README updated with Task 3 quickstart

---

## 🚢 Migrating to Yandex Managed PostgreSQL

When ready for production:

1. Create managed PostgreSQL cluster in Yandex Cloud
2. Update `.env`:
   ```
   DB_HOST=rc1a-xxx.mdb.yandexcloud.net
   DB_PORT=6432
   DB_NAME=flower_market
   DB_USER=...
   DB_PASSWORD=...
   ```
3. Run migrations: `alembic upgrade head`
4. Done!

## 📄 License

Proprietary - All rights reserved.

## 👥 Contact

For questions or support, contact the development team.
