# TASK 2.4 — Tests and Documentation (Final Task 2 Completion)

You are working in an existing repo where Task 1, Task 2.1, Task 2.2, and Task 2.3 are completed.
All functionality is implemented, now we need comprehensive tests and documentation.

## Goal
Complete Task 2 with:
1) Unit tests for confidence scoring and normalization logic
2) End-to-end integration test covering full workflow
3) ADMIN_API.md documentation with all endpoints
4) README.md update with Task 2 quickstart

## Scope (must implement)

### A) Unit Tests

#### File: `tests/unit/test_confidence_scoring.py`

**Test cases (minimum 5):**

1. **Test base confidence**
   - No matches: should return 0.10

2. **Test product_type match**
   - product_type match only: should return 0.40 (0.10 + 0.30)

3. **Test exact variety match**
   - product_type + exact variety: should return 0.85 (0.10 + 0.30 + 0.45)

4. **Test high similarity variety**
   - product_type + high similarity: should return 0.70 (0.10 + 0.30 + 0.30)

5. **Test negative signals**
   - has_mix_keyword: should deduct 0.25
   - name_too_short: should deduct 0.10
   - conflicting_product_type: should deduct 0.20

6. **Test clamping**
   - Negative total: should clamp to 0.0
   - Over 1.0: should clamp to 1.0

7. **Test combined signals**
   - product_type + variety + subtype + country: high score
   - product_type + mix keyword: reduced score

#### File: `tests/unit/test_normalization_logic.py`

**Test cases:**

1. **Test normalize_tokens()**
   - Cyrillic + Latin mixed
   - Special characters removal
   - Whitespace normalization
   - Currency symbol removal

2. **Test remove_stopwords()**
   - Remove common stopwords
   - Preserve meaningful words

3. **Test detect_product_type()**
   - Match by main value
   - Match by synonym
   - No match returns None

4. **Test detect_variety()**
   - Extract single Latin token
   - Extract multi-word variety (e.g., "Pink Floyd")
   - Apply variety_alias
   - No Latin tokens returns None

5. **Test variety_similarity()**
   - Exact match: returns "exact"
   - One contains other: returns "high"
   - Token overlap >= 0.7: returns "high"
   - Token overlap >= 0.4: returns "low"
   - No overlap: returns "none"

---

### B) Integration Test (End-to-End)

#### File: `tests/integration/test_task2_e2e.py`

**Test scenario: Complete normalization and publish workflow**

**Setup:**
1. Start with clean database (use test fixtures or setup/teardown)
2. Create test supplier: "Test Flower Base"

**Step 1: Import CSV**
- Upload test CSV with 5 items:
  - "Rose Explorer 60cm (Ecuador)" - 120
  - "Rose Mondial 50cm" - 95-99
  - "Carnation Pink 70cm (Netherlands)" - 45
  - "Alstroemeria White 80cm" - 65
  - "Rose Unknown Variety 60cm" - 100 (for unmapped case)
- Assert: import_batch created, status=parsed
- Assert: 5 supplier_items created
- Assert: 5 offer_candidates created

**Step 2: Bootstrap dictionary**
- POST /admin/dictionary/bootstrap
- Assert: 35+ entries created

**Step 3: Create normalized SKUs**
- POST /admin/skus:
  - SKU 1: {"product_type": "rose", "variety": "Explorer", "title": "Rose Explorer"}
  - SKU 2: {"product_type": "rose", "variety": "Mondial", "title": "Rose Mondial"}
  - SKU 3: {"product_type": "carnation", "variety": null, "title": "Carnation Standard"}
  - SKU 4: {"product_type": "alstroemeria", "variety": "White", "title": "Alstroemeria White"}
- Assert: 4 SKUs created

**Step 4: Run propose**
- POST /admin/normalization/propose with supplier_id
- Assert: proposed_mappings > 0
- Assert: tasks_created >= 1 (for "Unknown Variety")

**Step 5: List tasks**
- GET /admin/normalization/tasks?status=open
- Assert: at least 1 task returned
- Assert: task has supplier_item details
- Assert: task has proposed_mappings (if any)

**Step 6: Confirm mappings**
- Get proposed mappings for first 4 items (Explorer, Mondial, Pink, White)
- For each:
  - POST /admin/normalization/confirm with supplier_item_id and normalized_sku_id
  - Assert: 200 OK
  - Assert: mapping status=confirmed

**Step 7: Verify confirmed mappings**
- Query sku_mappings table directly
- Assert: 4 confirmed mappings exist
- Assert: Only ONE confirmed per supplier_item (constraint check)

**Step 8: Publish offers**
- POST /admin/publish/suppliers/{supplier_id}
- Assert: 200 OK
- Assert: offers_created = 4 (4 mapped items)
- Assert: skipped_unmapped = 1 (Unknown Variety)

**Step 9: Query offers**
- GET /offers
- Assert: 4 active offers returned
- Assert: Each offer has supplier and sku data
- Assert: All is_active = true

**Step 10: Filter offers**
- GET /offers?product_type=rose
- Assert: 2 rose offers (Explorer, Mondial)
- GET /offers?length_cm=60
- Assert: offers with length_cm=60 returned

**Step 11: Search offers**
- GET /offers?q=explorer
- Assert: Explorer offer returned

**Step 12: Re-publish (idempotency)**
- POST /admin/publish/suppliers/{supplier_id} again
- Assert: offers_deactivated = 4 (old ones)
- Assert: offers_created = 4 (new ones)
- GET /offers: still 4 active offers

**Teardown:**
- Clean up test data or use transaction rollback

---

### C) Documentation

#### File: `docs/ADMIN_API.md`

**Structure:**

```markdown
# Admin API Reference

## Overview
This document describes all admin endpoints for the B2B Flower Market Platform.

## Authentication
MVP: No authentication required. Add in production.

## Base URL
`http://localhost:8000`

---

## Suppliers

### Create Supplier
POST /admin/suppliers
...

### List Suppliers
GET /admin/suppliers
...

---

## Imports

### Upload CSV
POST /admin/suppliers/{supplier_id}/imports/csv
...

### Get Import Summary
GET /admin/imports/{import_batch_id}
...

---

## Dictionary Management

### Bootstrap Dictionary
POST /admin/dictionary/bootstrap
...

### List Dictionary Entries
GET /admin/dictionary
...

### Create Dictionary Entry
POST /admin/dictionary
...

### Update Dictionary Entry
PATCH /admin/dictionary/{entry_id}
...

---

## Normalized SKUs

### Create SKU
POST /admin/skus
...

### List SKUs
GET /admin/skus
...

### Get SKU
GET /admin/skus/{sku_id}
...

---

## Normalization

### Propose Mappings
POST /admin/normalization/propose
...

### List Tasks
GET /admin/normalization/tasks
...

### Confirm Mapping
POST /admin/normalization/confirm
...

---

## Publishing

### Publish Offers
POST /admin/publish/suppliers/{supplier_id}
...

---

## Retail (Read-only)

### List Offers
GET /offers
...
```

**For each endpoint, include:**
- Description
- HTTP method and path
- Request parameters (path, query, body)
- Request example (curl)
- Response schema
- Response example (JSON)
- Status codes
- Notes

---

#### File: `README.md` (update)

**Add section: Task 2 - Normalization & Publishing**

```markdown
## Task 2 - Normalization & Publishing

### Quick Start

#### 1. Bootstrap Dictionary
```bash
curl -X POST http://localhost:8000/admin/dictionary/bootstrap
```

#### 2. Create Normalized SKUs
```bash
curl -X POST http://localhost:8000/admin/skus \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "rose",
    "variety": "Explorer",
    "title": "Rose Explorer"
  }'
```

#### 3. Import CSV
```bash
curl -X POST http://localhost:8000/admin/suppliers/{id}/imports/csv \
  -F "file=@data/samples/test_price_list.csv"
```

#### 4. Propose Mappings
```bash
curl -X POST http://localhost:8000/admin/normalization/propose \
  -H "Content-Type: application/json" \
  -d '{"supplier_id": "..."}'
```

#### 5. Review Tasks
```bash
curl http://localhost:8000/admin/normalization/tasks?status=open
```

#### 6. Confirm Mapping
```bash
curl -X POST http://localhost:8000/admin/normalization/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_item_id": "...",
    "normalized_sku_id": "...",
    "notes": "Confirmed after review"
  }'
```

#### 7. Publish Offers
```bash
curl -X POST http://localhost:8000/admin/publish/suppliers/{id}
```

#### 8. Query Offers
```bash
curl "http://localhost:8000/offers?product_type=rose&limit=10"
```

### Normalization Workflow

1. **Import** → Creates supplier_items and offer_candidates
2. **Propose** → Creates sku_mappings (proposed) and normalization_tasks
3. **Review** → Admin reviews tasks and confirms/rejects mappings
4. **Confirm** → Sets mapping status to confirmed
5. **Publish** → Creates offers from offer_candidates with confirmed mappings
6. **Search** → Retail can query published offers

### Architecture

- Dictionary-driven normalization (product types, synonyms, regex rules)
- Confidence scoring based on multiple signals
- Manual review queue for low-confidence matches
- Transactional confirm (only one confirmed mapping per item)
- Replace-all publish strategy (deactivate old, insert new)
```

---

## Required Tests Summary

| Test File | Test Cases | Coverage |
|-----------|------------|----------|
| `test_confidence_scoring.py` | 7 cases | Confidence calculation |
| `test_normalization_logic.py` | 5 cases | Token normalization, detection |
| `test_task2_e2e.py` | 1 full scenario | End-to-end workflow |

**Total: 13+ test cases**

---

## Definition of Done

- ✅ Unit tests written and passing (confidence + logic)
- ✅ Integration test written and passing (full e2e)
- ✅ ADMIN_API.md created with all endpoints documented
- ✅ README.md updated with Task 2 quickstart
- ✅ All tests can be run with `pytest`
- ✅ Test coverage report generated
- ✅ No failing tests

---

## Output format for your response
1) Test implementation plan
2) Documentation structure
3) Files created/changed
4) Test run commands and results
5) Final Task 2 completion checklist
