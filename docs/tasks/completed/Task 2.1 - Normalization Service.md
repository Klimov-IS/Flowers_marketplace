# TASK 2.1 — Implement NormalizationService (Propose Mappings + Tasks)

You are working in an existing repo where Task 1 and partial Task 2 are completed.
Database schema includes all normalized layer tables. Dictionary bootstrap, SKU CRUD, and core normalization logic are ready.

## Goal
Implement the core normalization service that:
1) Takes supplier_items (by supplier_id or import_batch_id)
2) Applies dictionary-driven normalization (stopwords, synonyms, regex extraction)
3) Detects product_type and variety
4) Searches for candidate normalized_skus (exact match + similarity)
5) Creates sku_mappings with status=proposed and confidence scores
6) Creates normalization_tasks for low confidence cases (<0.70)
7) Ensures idempotency (no duplicate proposed mappings)

## Scope (must implement)

### A) NormalizationService.propose()
Service: `apps/api/services/normalization_service.py`

Method signature:
```python
async def propose(
    self,
    supplier_id: Optional[UUID] = None,
    import_batch_id: Optional[UUID] = None,
    limit: int = 1000,
) -> Dict[str, int]:
    """
    Propose SKU mappings for supplier_items.

    Returns: {
        "processed_items": int,
        "proposed_mappings": int,
        "tasks_created": int,
    }
    """
```

#### Algorithm (per supplier_item):

**Step 1: Load dictionaries**
- Load from DB:
  - product_type dict (active entries)
  - country dict
  - stopword dict
  - variety_alias dict
  - regex_rule dict (subtype patterns)

**Step 2: Build normalized context**
- Combine `raw_name` + `raw_group` (if exists)
- Apply `normalize_tokens()` from `packages.core.normalization.tokens`
- Build stopwords set from dictionary
- Apply `remove_stopwords()`

**Step 3: Extract attributes**
- Use `detect_product_type()` with product_type dict
- Use `detect_variety()` with variety_alias dict
- Use `detect_subtype()` with regex_rules
- Extract country from `supplier_items.attributes` (already extracted in Task 1)

**Step 4: Search candidate normalized_skus**

Search strategies (in priority order):
1. **Exact match**: `product_type` + `variety` exact match
   - Query: `WHERE product_type = ? AND variety = ?`
   - If found: confidence boost

2. **Product type only**: if variety not detected
   - Query: `WHERE product_type = ? AND variety IS NULL`

3. **Similarity search** (if no exact match):
   - Query: `WHERE product_type = ?` (limit 10)
   - Calculate `variety_similarity()` for each candidate
   - Keep top 5 by similarity score

**Step 5: Calculate confidence for each candidate**
- Use `calculate_confidence()` from `packages.core.normalization.confidence`
- Inputs:
  - `product_type_match`: bool
  - `variety_match`: "exact" | "high" | "low" | None (from `variety_similarity()`)
  - `subtype_match`: bool
  - `country_match`: bool (compare with sku.meta.origin_default if exists)
  - `has_mix_keyword`: check if "mix" or "микс" in name
  - `name_too_short`: check if < 3 tokens after stopword removal
  - `conflicting_product_type`: check if multiple product types detected

**Step 6: Create sku_mappings (proposed)**
- For each candidate with confidence > 0.10:
  - Check if mapping already exists:
    - Query: `SELECT FROM sku_mappings WHERE supplier_item_id = ? AND normalized_sku_id = ? AND status = 'proposed'`
    - If exists: skip (idempotency)
  - Create new mapping:
    - `status = "proposed"`
    - `method = "rule"`
    - `confidence = calculated_score`
  - Limit to top 5 candidates per supplier_item

**Step 7: Create normalization_task (if needed)**
Conditions for creating task:
- Top confidence < 0.70 OR
- No product_type detected OR
- No candidates found OR
- Top 2 candidates have confidence diff < 0.05 (ambiguity)

Task fields:
- `reason`: string describing why (e.g., "Low confidence: 0.45", "Product type not detected", "Ambiguous: 2 candidates with similar scores")
- `priority`: calculated as:
  - base = 100
  - +2 * (count of offer_candidates for this supplier_item)
  - +50 if supplier.meta.tier == "key" (if field exists)
- `status = "open"`

**Step 8: Return summary**
Return counts of:
- processed_items
- proposed_mappings (total created)
- tasks_created

#### Idempotency guarantees:
- Do NOT create duplicate `sku_mappings` with same (supplier_item_id, normalized_sku_id, status=proposed)
- Do NOT create duplicate `normalization_tasks` for same supplier_item_id with status=open
- Use `SELECT ... FOR UPDATE` or check-then-insert pattern

---

### B) Helper methods (in NormalizationService)

```python
async def _load_dictionaries(self) -> Dict:
    """Load all active dictionary entries grouped by type."""

async def _process_supplier_item(
    self,
    supplier_item: SupplierItem,
    dictionaries: Dict,
) -> Dict:
    """Process single supplier_item. Returns summary."""

async def _search_candidate_skus(
    self,
    product_type: Optional[str],
    variety: Optional[str],
) -> List[NormalizedSKU]:
    """Search for candidate SKUs."""

async def _calculate_priority(
    self,
    supplier_item: SupplierItem,
) -> int:
    """Calculate task priority."""

async def _create_mapping_if_not_exists(
    self,
    supplier_item_id: UUID,
    normalized_sku_id: UUID,
    confidence: Decimal,
    method: str = "rule",
) -> bool:
    """Create mapping if not exists. Returns True if created."""

async def _create_task_if_needed(
    self,
    supplier_item_id: UUID,
    reason: str,
    priority: int,
) -> bool:
    """Create task if not exists. Returns True if created."""
```

---

## Required tests (minimum)

### Unit tests (`tests/unit/test_normalization_logic.py`):
1. Test `detect_product_type()` with various inputs
2. Test `detect_variety()` with Latin tokens
3. Test `calculate_confidence()` with different signal combinations (5+ cases)
4. Test `variety_similarity()` for exact/high/low/none

### Integration test (`tests/integration/test_normalization_propose.py`):
1. Setup:
   - Create supplier
   - Import CSV with 3-5 items
   - Bootstrap dictionary
   - Create 2-3 normalized_skus (one exact match, one similar)
2. Run: `propose()` for supplier
3. Assert:
   - sku_mappings created (count > 0)
   - At least one mapping has confidence > 0.70
   - At least one task created for unmatched item
4. Run: `propose()` again (idempotency test)
5. Assert:
   - Counts remain same (no duplicates)

---

## Non-goals (explicitly do NOT implement)
- Semantic embeddings / ML matching
- Auto-confirm mappings (always status=proposed)
- Batch processing with parallelization (keep simple for MVP)
- Complex trigram similarity (use simple token overlap)

---

## Definition of Done
- `NormalizationService.propose()` works for supplier_id or import_batch_id filters
- Mappings created with correct confidence scores
- Tasks created for low confidence cases
- Idempotency works (re-running propose doesn't create duplicates)
- Unit tests pass (5+ test cases)
- Integration test passes (full flow)
- Code follows existing patterns (async, logging, error handling)

---

## Output format for your response
1) Plan (algorithm steps breakdown)
2) Implementation notes (key decisions)
3) Files created/changed (list)
4) Test commands
5) DoD checklist results
