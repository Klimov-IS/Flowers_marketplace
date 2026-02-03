# TASK 2 — Complete Roadmap & Task Breakdown

## Overview
Task 2 завершает MVP нормализации и публикации офферов. Разбит на 4 подзадачи для управляемости.

---

## Task Structure

```
Task 2 (Complete MVP Normalization & Publishing)
│
├── Task 2.0 ✅ DONE (Dictionary, SKU, Core Logic) — 60% complete
│   ├── DB models + migration
│   ├── Dictionary bootstrap + CRUD
│   ├── SKU CRUD
│   └── Core normalization logic (tokens, detection, confidence)
│
├── Task 2.1 🚧 TODO (NormalizationService)
│   ├── propose() method - rule-based matching
│   ├── Create sku_mappings (proposed)
│   ├── Create normalization_tasks
│   └── Idempotency guarantees
│
├── Task 2.2 🚧 TODO (Normalization Endpoints)
│   ├── POST /admin/normalization/propose
│   ├── GET /admin/normalization/tasks
│   └── POST /admin/normalization/confirm (transactional)
│
├── Task 2.3 🚧 TODO (Publish + Offers)
│   ├── PublishService.publish_supplier_offers()
│   ├── POST /admin/publish/suppliers/{id}
│   └── GET /offers (retail endpoint)
│
└── Task 2.4 🚧 TODO (Tests + Docs)
    ├── Unit tests (confidence, logic)
    ├── Integration test (full e2e)
    ├── ADMIN_API.md
    └── README update
```

---

## Task 2.0 ✅ COMPLETED

**Status:** 60% of Task 2 done
**Time spent:** ~4 hours
**Files created:** 14 files

### What's done:
- ✅ 6 new DB models (NormalizedSKU, DictionaryEntry, SKUMapping, NormalizationTask, Offer, SupplierDeliveryRule)
- ✅ Migration 002 with full schema
- ✅ Dictionary seed data (35+ entries)
- ✅ DictionaryService with idempotent bootstrap
- ✅ Dictionary CRUD endpoints
- ✅ SKUService with CRUD operations
- ✅ SKU endpoints with search
- ✅ Core normalization logic:
  - Token normalization
  - Stopword removal
  - Product type detection
  - Variety detection
  - Confidence scoring

### How to test:
```bash
python test_imports.py  # Verify all imports work
# See QUICK_TEST.md for full test guide
```

---

## Task 2.1 🚧 NormalizationService

**File:** `docs/Task 2.1 - Normalization Service.md`
**Estimated time:** 2-3 hours
**Priority:** CRITICAL PATH

### Deliverables:
- [ ] `apps/api/services/normalization_service.py`
- [ ] `NormalizationService.propose()` method
- [ ] Helper methods (_load_dictionaries, _process_supplier_item, etc)
- [ ] Unit tests for detection functions
- [ ] Integration test for propose flow

### Key algorithm:
1. Load dictionaries (product_type, country, stopwords, variety_alias, regex_rules)
2. Normalize supplier_item text (stopwords, synonyms)
3. Detect product_type and variety
4. Search candidate normalized_skus (exact + similarity)
5. Calculate confidence scores
6. Create sku_mappings (status=proposed)
7. Create normalization_tasks for low confidence (<0.70)

### Success criteria:
- Propose creates mappings with correct confidence
- Tasks created for unmapped items
- Idempotency works (no duplicates on re-run)
- Tests pass

---

## Task 2.2 🚧 Normalization Endpoints

**File:** `docs/Task 2.2 - Normalization Endpoints.md`
**Estimated time:** 2 hours
**Dependencies:** Task 2.1 must be done first

### Deliverables:
- [ ] `apps/api/routers/normalization.py`
- [ ] POST /admin/normalization/propose
- [ ] GET /admin/normalization/tasks (with enriched data)
- [ ] POST /admin/normalization/confirm (transactional)
- [ ] Integration tests for all endpoints

### Key implementation:
- **Propose:** Validate inputs, call NormalizationService.propose()
- **Tasks:** Join with supplier_items, sku_mappings, raw_rows for context
- **Confirm:** TRANSACTIONAL - reject old, confirm new, mark task done

### Success criteria:
- All 3 endpoints work correctly
- Confirm enforces uniqueness constraint (one confirmed mapping per item)
- Integration tests pass
- Logging added

---

## Task 2.3 🚧 Publish + Offers

**File:** `docs/Task 2.3 - Publish Service and Offers Endpoint.md`
**Estimated time:** 2 hours
**Dependencies:** Task 2.2 must be done first

### Deliverables:
- [ ] `apps/api/services/publish_service.py`
- [ ] `apps/api/routers/publish.py`
- [ ] `apps/api/routers/offers.py`
- [ ] POST /admin/publish/suppliers/{id}
- [ ] GET /offers with filters
- [ ] Integration tests

### Key algorithm (Publish):
1. Find latest parsed import_batch for supplier
2. Get offer_candidates (validation=ok/warn)
3. Join with confirmed sku_mappings
4. Deactivate old offers (is_active=false)
5. Create new offers (is_active=true)
6. Return counts

### Key features (Offers):
- Filters: q, product_type, length_cm, price_min/max, supplier_id
- Pagination: limit/offset
- Joins: offers + suppliers + normalized_skus
- Order: published_at DESC, price_min ASC

### Success criteria:
- Publish creates offers from confirmed mappings only
- Re-publish replaces old offers
- GET /offers works with all filters
- Tests pass

---

## Task 2.4 🚧 Tests + Documentation

**File:** `docs/Task 2.4 - Tests and Documentation.md`
**Estimated time:** 2-3 hours
**Dependencies:** Task 2.1, 2.2, 2.3 must be done

### Deliverables:
- [ ] `tests/unit/test_confidence_scoring.py` (7+ cases)
- [ ] `tests/unit/test_normalization_logic.py` (5+ cases)
- [ ] `tests/integration/test_task2_e2e.py` (full workflow)
- [ ] `docs/ADMIN_API.md` (complete endpoint reference)
- [ ] Update `README.md` with Task 2 quickstart

### E2E test scenario:
1. Import CSV (5 items)
2. Bootstrap dictionary
3. Create SKUs (4 exact matches)
4. Propose mappings
5. List tasks
6. Confirm 4 mappings
7. Publish offers
8. Query offers with filters
9. Re-publish (idempotency)

### Documentation requirements:
- All endpoints documented with curl examples
- Request/response schemas
- Status codes
- Notes and gotchas

### Success criteria:
- All tests pass
- Test coverage report shows good coverage
- Documentation is complete and accurate
- README quickstart works end-to-end

---

## Total Effort Estimate

| Task | Status | Time Estimate | Priority |
|------|--------|---------------|----------|
| Task 2.0 | ✅ Done | 4h (spent) | - |
| Task 2.1 | 🚧 TODO | 2-3h | CRITICAL |
| Task 2.2 | 🚧 TODO | 2h | HIGH |
| Task 2.3 | 🚧 TODO | 2h | HIGH |
| Task 2.4 | 🚧 TODO | 2-3h | MEDIUM |

**Total remaining: 8-10 hours**

---

## Execution Order (Strict Dependencies)

```
Task 2.0 (done)
    ↓
Task 2.1 (NormalizationService) ← START HERE
    ↓
Task 2.2 (Normalization Endpoints)
    ↓
Task 2.3 (Publish + Offers)
    ↓
Task 2.4 (Tests + Docs) ← FINISH HERE
```

**Cannot skip or reorder** - each task depends on previous ones.

---

## Current Status Summary

### ✅ WORKING
- DB schema complete
- Migrations ready
- Dictionary bootstrap works
- SKU CRUD works
- Core logic implemented
- All imports successful

### 🚧 TODO (Critical Path)
- **Task 2.1:** NormalizationService.propose() ← NEXT
- **Task 2.2:** Normalization endpoints
- **Task 2.3:** Publish service + offers endpoint
- **Task 2.4:** Tests + documentation

### 📊 Progress
- **Overall Task 2:** 60% complete
- **Critical path:** NormalizationService (next blocker)
- **Estimated completion:** 8-10 hours from now

---

## Quick Reference

### Task Files Location
- `docs/Task 2.1 - Normalization Service.md`
- `docs/Task 2.2 - Normalization Endpoints.md`
- `docs/Task 2.3 - Publish Service and Offers Endpoint.md`
- `docs/Task 2.4 - Tests and Documentation.md`

### Progress Tracking
- `TASK2_PROGRESS.md` - detailed progress report
- `QUICK_TEST.md` - how to test current work

### Development Files
- `test_imports.py` - verify imports work
- `.env` - local config
- `alembic/versions/002_*.py` - migration

---

## How to Start Task 2.1

1. Read: `docs/Task 2.1 - Normalization Service.md`
2. Create: `apps/api/services/normalization_service.py`
3. Implement: `NormalizationService.propose()`
4. Test: Unit tests + integration test
5. Verify: Run propose for test supplier

**Start command:**
```bash
# Create the service file
touch apps/api/services/normalization_service.py

# Open task description
cat docs/Task\ 2.1\ -\ Normalization\ Service.md
```

Good luck! 🚀
