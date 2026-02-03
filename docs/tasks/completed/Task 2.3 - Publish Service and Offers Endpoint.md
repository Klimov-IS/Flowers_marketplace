# TASK 2.3 — Publish Service + Retail Offers Endpoint

You are working in an existing repo where Task 1, Task 2.1, and Task 2.2 are completed.
Normalization flow works: propose → confirm mappings.

## Goal
Implement:
1) PublishService - convert offer_candidates → offers (published) for confirmed mappings
2) Admin endpoint: POST /admin/publish/suppliers/{supplier_id}
3) Retail endpoint: GET /offers - search published offers with filters

## Scope (must implement)

### A) PublishService
**File:** `apps/api/services/publish_service.py`

#### Method: `publish_supplier_offers()`

**Signature:**
```python
async def publish_supplier_offers(
    self,
    supplier_id: UUID,
) -> Dict[str, int]:
    """
    Publish offers for supplier from latest import.

    Returns: {
        "offers_deactivated": int,
        "offers_created": int,
        "skipped_unmapped": int,
    }
    """
```

**Algorithm:**

**Step 1: Validate supplier**
- Check supplier exists and is active
- Raise error if not found or blocked

**Step 2: Find latest successful import_batch**
- Query: `SELECT id FROM import_batches WHERE supplier_id = ? AND status = 'parsed' ORDER BY imported_at DESC LIMIT 1`
- If none found: raise error "No parsed imports found"

**Step 3: Fetch offer_candidates**
- Query: `SELECT * FROM offer_candidates WHERE import_batch_id = ? AND validation IN ('ok', 'warn')`
- Join with supplier_items to get stable_key

**Step 4: Fetch confirmed mappings**
- Query: `SELECT supplier_item_id, normalized_sku_id FROM sku_mappings WHERE status = 'confirmed' AND supplier_item_id IN (...)`
- Build map: {supplier_item_id → normalized_sku_id}

**Step 5: Deactivate old offers (in transaction)**
- UPDATE: `UPDATE offers SET is_active = false WHERE supplier_id = ? AND is_active = true`
- Count affected rows

**Step 6: Create new offers (in transaction)**
For each offer_candidate:
- Check if supplier_item has confirmed mapping (from Step 4)
- If NO mapping: skip, increment `skipped_unmapped`
- If HAS mapping:
  - Create new offer:
    ```python
    Offer(
        supplier_id=supplier_id,
        normalized_sku_id=mapping.normalized_sku_id,
        source_import_batch_id=import_batch_id,
        length_cm=candidate.length_cm,
        pack_type=candidate.pack_type,
        pack_qty=candidate.pack_qty,
        price_type=candidate.price_type,
        price_min=candidate.price_min,
        price_max=candidate.price_max,
        currency=candidate.currency,
        tier_min_qty=candidate.tier_min_qty,
        tier_max_qty=candidate.tier_max_qty,
        availability=candidate.availability,
        stock_qty=candidate.stock_qty,
        is_active=true,
        published_at=now(),
    )
    ```
  - Increment `offers_created`

**Step 7: Commit transaction**

**Step 8: Update import_batch status (optional)**
- UPDATE: `UPDATE import_batches SET status = 'published' WHERE id = ?`

**Step 9: Return summary**

---

### B) Admin publish endpoint
**File:** `apps/api/routers/publish.py`

**Route:** `POST /admin/publish/suppliers/{supplier_id}`

**Response:**
```json
{
  "supplier_id": "uuid",
  "import_batch_id": "uuid",
  "offers_deactivated": 15,
  "offers_created": 12,
  "skipped_unmapped": 3
}
```

**Status codes:**
- 200: Success
- 404: Supplier not found or no imports
- 500: Internal error

**Register in main.py:**
```python
from apps.api.routers import publish

app.include_router(
    publish.router,
    prefix="/admin/publish",
    tags=["publish"]
)
```

---

### C) Retail offers endpoint
**File:** `apps/api/routers/offers.py`

**Route:** `GET /offers`

**Query params:**
- `q`: Full text search (against normalized_skus.title, variety, product_type)
- `product_type`: Filter by product type
- `length_cm`: Filter by exact length
- `length_min` / `length_max`: Filter by length range
- `price_min` / `price_max`: Filter by price range
- `supplier_id`: Filter by supplier
- `is_active`: Filter by active status (default true)
- `limit`: Max results (default 100, max 500)
- `offset`: Pagination offset

**Response:**
```json
{
  "offers": [
    {
      "id": "uuid",
      "supplier": {
        "id": "uuid",
        "name": "Test Flower Base"
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
      "published_at": "2025-01-12T..."
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

**Implementation notes:**
- Join offers with suppliers (name)
- Join offers with normalized_skus (product_type, variety, title)
- Default filter: `is_active = true`
- Order by: `published_at DESC, price_min ASC`
- Use SQLAlchemy's `.options(joinedload())` for efficient joins

**Register in main.py:**
```python
from apps.api.routers import offers

app.include_router(
    offers.router,
    tags=["offers"]  # No prefix - public endpoint
)
```

---

## Publish strategy decisions

**MVP approach: Replace all**
- Deactivate ALL old offers for supplier
- Create new offers from latest import
- Simple, predictable, avoids complex diff logic

**Alternative (NOT for MVP): Incremental update**
- Compare old vs new offers
- Update changed, delete removed, insert new
- More complex, defer to later

---

## Required tests

### Integration test (`tests/integration/test_publish_and_offers.py`):

**Test 1: Publish flow**
1. Setup:
   - Create supplier
   - Import CSV
   - Bootstrap dictionary
   - Create normalized_skus
   - Run propose
   - Confirm mapping for at least 1 item
2. POST /admin/publish/suppliers/{id}
3. Assert:
   - 200 OK
   - offers_created > 0
   - skipped_unmapped >= 0 (for items without mapping)

**Test 2: Query offers**
1. After publish, GET /offers
2. Assert:
   - At least 1 offer returned
   - Offer has supplier and sku data joined
   - is_active = true

**Test 3: Filter offers**
1. GET /offers?product_type=rose
2. Assert: only rose offers returned
3. GET /offers?price_max=100
4. Assert: only offers with price_min <= 100

**Test 4: Re-publish (replace)**
1. Publish once (creates 10 offers)
2. Import new CSV with 8 items
3. Confirm mappings
4. Publish again
5. Assert:
   - Old 10 offers deactivated (is_active=false)
   - New 8 offers created (is_active=true)
   - GET /offers returns only 8 active

**Test 5: Search**
1. GET /offers?q=explorer
2. Assert: returns offers with "Explorer" in SKU title/variety

---

## Non-goals (explicitly do NOT implement)
- Offer versioning / history tracking
- Real-time stock updates
- Price change notifications
- Offer expiration logic
- Complex deduplication (offer signatures)

---

## Definition of Done
- PublishService.publish_supplier_offers() works
- POST /admin/publish/suppliers/{id} endpoint works
- GET /offers endpoint with all filters works
- Offers correctly joined with suppliers and SKUs
- Re-publish replaces old offers (is_active logic)
- Integration tests pass (5 test cases)
- Logging added for publish operations
- Endpoints documented in Swagger

---

## Output format for your response
1) Plan (publish algorithm + endpoints)
2) Implementation notes (transaction handling, join strategy)
3) Files created/changed
4) Test commands (curl examples)
5) DoD checklist results
