# Task 2.1 - Normalization Service - COMPLETED

**Status**: ✅ Complete
**Date**: 2025-01-12

## Summary

Implemented the core NormalizationService with rule-based SKU mapping proposal logic. The service analyzes supplier items, searches for candidate normalized SKUs, calculates confidence scores, and creates mappings or manual review tasks.

## Deliverables

### 1. NormalizationService Implementation
**File**: `apps/api/services/normalization_service.py` (~442 lines)

**Key Methods**:
- `propose()` - Main entry point for proposing mappings
  - Accepts filters: supplier_id or import_batch_id
  - Processes active supplier_items
  - Returns summary with counts

- `_process_supplier_item()` - Core logic for single item
  - Normalizes tokens and removes stopwords
  - Extracts attributes (product_type, variety, subtype, country)
  - Searches candidate SKUs
  - Calculates confidence for each candidate
  - Creates top 5 mappings (confidence > 0.10)
  - Creates manual review task if needed

- `_search_candidate_skus()` - Three-tier strategy
  1. Exact match (product_type + variety)
  2. Generic match (product_type only, variety IS NULL)
  3. Similarity search (all with same product_type, limit 10)

- `_calculate_priority()` - Task priority calculation
  - Base: 100
  - +2 per offer_candidate
  - +50 for "key" tier suppliers

- `_create_mapping_if_not_exists()` - Idempotent mapping creation
- `_create_task_if_needed()` - Idempotent task creation
- `_load_dictionaries()` - Load all active dictionary entries grouped by type

**Algorithm Highlights**:
```python
# Confidence scoring with multiple signals
confidence = calculate_confidence(
    product_type_match=(product_type == candidate.product_type),
    variety_match=variety_similarity(variety, candidate.variety),
    subtype_match=(subtype == candidate.subtype),
    country_match=(country == candidate.origin_country),
    has_mix_keyword="mix" in text or "микс" in text,
    name_too_short=len(tokens) < 3,
    conflicting_product_type=False,
)

# Task creation conditions
if not candidates:
    create_task("No candidate SKUs found")
elif top_confidence < 0.70:
    create_task(f"Low confidence: {confidence}")
elif top2_diff < 0.05:
    create_task(f"Ambiguous: similar scores ({diff})")
```

**Features**:
- Async/await throughout
- Dictionary-driven normalization
- Multi-signal confidence scoring
- Idempotency guarantees (check-then-insert)
- Structured logging with contextual information
- Error handling with continue-on-failure for batch processing

### 2. Unit Tests
**File**: `tests/unit/test_normalization_logic.py` (29 tests, 100% passing)

**Test Coverage**:
- **TestNormalization** (5 tests): Token processing
  - Basic normalization (lowercase, special chars)
  - Cyrillic handling
  - Whitespace normalization
  - Stopword removal

- **TestDetection** (7 tests): Attribute extraction
  - Product type detection (exact, synonym, not found)
  - Variety detection (multi-word, alias, not found)

- **TestConfidenceScoring** (10 tests): Scoring algorithm
  - Base confidence
  - Product type match
  - Variety matches (exact, high, low)
  - Negative signals (mix keyword, short name)
  - Combined signals
  - Clamping to [0.0, 1.0]

- **TestVarietySimilarity** (7 tests): Similarity calculation
  - Exact match (case insensitive)
  - Substring containment (high similarity)
  - Token overlap (high, low, none)
  - Null handling

**Test Results**:
```
============================= 29 passed in 0.26s ==============================
```

### 3. Integration Tests
**File**: `tests/integration/test_normalization_propose.py` (4 tests, requires DB)

**Test Scenarios**:
1. `test_normalization_propose_flow` - Complete flow with idempotency
   - Import CSV with 5 items
   - Run propose()
   - Verify mappings and tasks created
   - Run propose() again
   - Assert no duplicates (idempotency)

2. `test_normalization_propose_by_batch` - Filter by import_batch_id
3. `test_normalization_propose_no_candidates` - Behavior when no SKUs exist
4. `test_normalization_error_handling` - Validation and error cases

**Note**: Integration tests require running PostgreSQL database:
```bash
cd infra && docker compose up -d
alembic upgrade head
pytest tests/integration/test_normalization_propose.py -v
```

### 4. Documentation
**File**: `tests/integration/README.md`

Provides instructions for running integration tests with prerequisites and coverage details.

## Technical Decisions

### 1. Idempotency Strategy
Used check-then-insert pattern instead of INSERT ON CONFLICT:
```python
# Check if exists
existing = await self.db.execute(
    select(SKUMapping).where(
        SKUMapping.supplier_item_id == supplier_item_id,
        SKUMapping.normalized_sku_id == normalized_sku_id,
        SKUMapping.status == "proposed",
    )
)
if existing.scalar_one_or_none():
    return False  # Already exists

# Create new
mapping = SKUMapping(...)
self.db.add(mapping)
return True
```

**Rationale**: Better observability and explicit control vs database-level conflict handling.

### 2. Search Strategy Priority
1. **Exact match first** (product_type + variety)
2. **Generic fallback** (product_type only, variety IS NULL)
3. **Similarity search** (all with product_type, scored by confidence)

**Rationale**: Fast path for exact matches, graceful degradation to generic or fuzzy matching.

### 3. Top-N Mappings
Keep top 5 candidates with confidence > 0.10

**Rationale**: Provide multiple options for manual review while filtering noise.

### 4. Task Creation Thresholds
- No candidates → create task
- Top confidence < 0.70 → create task
- Top 2 confidence diff < 0.05 → create task (ambiguous)

**Rationale**: Balance automation with manual review quality. Thresholds from NORMALIZATION_RULES.md.

### 5. Priority Calculation
Dynamic priority based on business value:
- Base: 100
- +2 per offer_candidate (demand signal)
- +50 for "key" tier suppliers (strategic importance)

**Rationale**: Prioritize high-impact items for manual review.

## Integration Points

### Inputs
- `supplier_items` table (status="active")
- `dictionary_entries` table (all types: product_type, stopword, variety_alias, regex_rule)
- `normalized_skus` table (candidate SKUs)

### Outputs
- `sku_mappings` table (status="proposed", method="rule")
- `normalization_tasks` table (status="open")

### Dependencies
- `packages.core.normalization.tokens` - Token processing
- `packages.core.normalization.detection` - Attribute extraction
- `packages.core.normalization.confidence` - Confidence scoring

## Testing

### Unit Tests (No DB required)
```bash
pytest tests/unit/test_normalization_logic.py -v
```
**Result**: 29 passed in 0.26s ✅

### Integration Tests (Requires DB)
```bash
# Start PostgreSQL
cd infra && docker compose up -d

# Run migrations
alembic upgrade head

# Run tests
pytest tests/integration/test_normalization_propose.py -v
```

**Expected**: 4 tests covering full flow, filtering, edge cases, and idempotency

## Definition of Done ✅

- [x] NormalizationService.propose() implemented with all helper methods
- [x] Algorithm matches specification in Task 2.1
- [x] Dictionary loading and filtering
- [x] Attribute extraction (product_type, variety, subtype, country)
- [x] Three-tier candidate search strategy
- [x] Multi-signal confidence scoring
- [x] Top-N mapping creation (idempotent)
- [x] Task creation for low confidence/ambiguous cases
- [x] Priority calculation based on business value
- [x] Structured logging throughout
- [x] Error handling with graceful degradation
- [x] Unit tests written (29 tests, 100% passing)
- [x] Integration tests written (4 tests, requires DB)
- [x] Code follows project conventions (async/await, type hints, docstrings)
- [x] No junk files or temp artifacts

## Next Steps

**Task 2.2** - Normalization Endpoints:
1. Create `apps/api/routers/normalization.py`
2. Implement POST /admin/normalization/propose
3. Implement GET /admin/normalization/tasks
4. Implement POST /admin/normalization/confirm
5. Write integration tests for endpoints

**Estimated**: 2 hours

## Files Changed

### Created (3 files)
- `apps/api/services/normalization_service.py` (442 lines)
- `tests/unit/test_normalization_logic.py` (232 lines)
- `tests/integration/test_normalization_propose.py` (295 lines)
- `tests/integration/README.md` (31 lines)
- `tests/integration/__init__.py` (empty)

### Modified (0 files)
None - service is standalone and ready for router integration

**Total**: 5 new files, ~1000 lines of production + test code

---

**Reviewed by**: Claude
**Sign-off**: Task 2.1 complete and ready for Task 2.2
