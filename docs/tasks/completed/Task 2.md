# TASK 2 — Dictionary bootstrap + Propose mappings + Manual review + Publish offers (MVP)

You are working in an existing repo where Task 1 is completed.
The DB schema already includes normalized_skus, dictionary_entries, sku_mappings, normalization_tasks, offers, supplier_delivery_rules.

## Goal
Implement the MVP normalization workflow and publishing:
1) Dictionary bootstrap (idempotent)
2) Normalized SKU CRUD (minimal)
3) Propose mappings (rule-based) + create normalization tasks
4) Manual confirm mapping endpoint (transactional)
5) Publish offers from offer_candidates using confirmed mappings
6) Minimal retail offers endpoint for search/filters (read-only)

No UI required. API + services + tests + docs.

## Scope (must implement)

### A) Dictionary bootstrap + CRUD
1) Add an idempotent bootstrap command that seeds dictionary_entries with minimum sets:
   - product_type: rose/carnation/alstroemeria/chrysanthemum/greens/packaging (+ru synonyms)
   - country: Ecuador/Colombia/Netherlands/Kenya/Israel (+ru synonyms)
   - pack_type: bak/pack (бак/упак + synonyms)
   - stopwords: руб/р/₽, см/cm, прайс, цена, импорт, сортовые, etc.
   - regex_rule: patterns for length, origin_country, pack_qty, subtype (spray/bush/standard/premium)
2) Provide API endpoints:
   - POST /admin/dictionary/bootstrap (idempotent; returns counts inserted/updated)
   - GET  /admin/dictionary?dict_type=...
   - POST /admin/dictionary (create)
   - PATCH /admin/dictionary/{id} (update key/value/synonyms/rules/status)

### B) Normalized SKU minimal management
Endpoints:
- POST /admin/skus  (create normalized_sku)
- GET  /admin/skus  (list, with optional q search by title/variety/product_type)
- GET  /admin/skus/{id}

### C) Propose mappings (rule-based) + tasks
Implement a service that for each supplier_item (optionally filtered by supplier_id or import_batch_id):
1) Builds a normalized token string from supplier_items.raw_name + raw_group
2) Applies dictionary stopwords removal + synonyms + regex extraction (length/country/subtype/pack markers)
3) Detects product_type (from dict)
4) Detects variety:
   - prefer Latin tokens (Explorer, Mondial, Pink Floyd...) as candidate variety
   - apply variety_alias dict if present (optional; can skip in MVP)
5) Searches candidate normalized_skus:
   - exact match on (product_type + variety) if possible
   - else trigram similarity against title/variety
6) Creates sku_mappings with status=proposed (up to 5 per supplier_item) and confidence score.
7) If top confidence < 0.70 OR ambiguity (top2 diff < 0.05) OR missing product_type/variety:
   - create normalization_tasks (open) with priority based on:
     - number of offer_candidates for that supplier_item
     - supplier importance (optional: suppliers.meta.tier)
8) Ensure propose is idempotent per supplier_item per run:
   - do not duplicate identical proposed mappings (same supplier_item_id + normalized_sku_id + status=proposed)

Endpoints:
- POST /admin/normalization/propose
  Body: { "supplier_id": "...?" , "import_batch_id": "...?" , "limit": 1000? }
  Returns: counts created (proposed mappings, tasks)

- GET /admin/normalization/tasks?status=open&supplier_id=...
  Returns: task + supplier_item + top proposed mappings (with confidence) + a few raw_row samples if possible.

### D) Confirm mapping (transactional)
Endpoint:
- POST /admin/normalization/confirm
  Body: { "supplier_item_id": "...", "normalized_sku_id": "...", "notes": "..."? }
Behavior:
1) In a transaction:
   - set all existing mappings for supplier_item_id to status=rejected except selected one
   - upsert selected mapping to status=confirmed with decided_at, decided_by(optional), method=manual, confidence=1.0
   - mark related normalization_task status=done if exists
2) Must satisfy DB constraint: only one confirmed mapping per supplier_item.

### E) Publish offers (per supplier)
Endpoint:
- POST /admin/publish/suppliers/{supplier_id}
Behavior:
1) Determine latest successful import batch for supplier with status=parsed (or published if you choose).
2) Select offer_candidates from that batch where validation in (ok,warn)
3) Join with confirmed sku_mappings for supplier_items to get normalized_sku_id
4) In a transaction:
   - set existing offers for supplier to is_active=false
   - insert new offers (is_active=true, published_at=now, source_import_batch_id set)
   - (optional) avoid duplicates by a unique “offer signature” (normalized_sku_id+length_cm+pack_type+pack_qty+tier_min/max+price_min/max)
Return: counts (offers deactivated, offers inserted, skipped_unmapped)

### F) Retail offers read endpoint (minimal)
Endpoint:
- GET /offers
Query params (optional):
- q (full text against normalized_skus.title/variety/product_type)
- product_type
- length_cm
- price_min / price_max filters
- supplier_id
Return:
- offers joined with supplier name and normalized sku title
This is read-only.

## Non-goals (explicitly do NOT implement)
- UI
- Payments
- Real-time stock sync
- Order flow improvements
- F2-F5 complex parsing beyond what Task 1 already does
- Semantic embeddings / ML matching

## Required tests
1) Unit: confidence scoring / token normalization (at least 5 cases)
2) Integration: end-to-end scenario:
   - import CSV (Task 1 pipeline)
   - bootstrap dictionary
   - create at least 2 normalized_skus
   - run propose → confirm mapping for 1 supplier_item
   - publish offers
   - assert offers count > 0 and GET /offers returns expected items

## Docs
- Add /docs/ADMIN_API.md describing new endpoints with example curl payloads.
- Update README with quickstart for Task 2 actions.

## Definition of Done
- bootstrap endpoint seeds dictionaries idempotently
- propose creates mappings and tasks without duplicates
- confirm mapping works transactionally and resolves uniqueness constraint
- publish creates offers only for confirmed mappings and deactivates old ones
- GET /offers returns published offers with filters
- tests pass
- docs updated
- no scope creep

## Output format for your response
1) Plan
2) Implementation notes (key decisions + trade-offs)
3) Files changed (list)
4) Commands to run
5) DoD checklist results
