# TASK 2.2 — Normalization Endpoints (Propose, Tasks, Confirm)

You are working in an existing repo where Task 1, partial Task 2, and Task 2.1 (NormalizationService) are completed.

## Goal
Expose normalization functionality via admin API endpoints:
1) POST /admin/normalization/propose - trigger propose for supplier/batch
2) GET /admin/normalization/tasks - list manual review tasks with context
3) POST /admin/normalization/confirm - confirm mapping (transactional)

## Scope (must implement)

### A) Propose endpoint
**Route:** `POST /admin/normalization/propose`

**Request body:**
```json
{
  "supplier_id": "uuid?",
  "import_batch_id": "uuid?",
  "limit": 1000
}
```

**Behavior:**
- Call `NormalizationService.propose()`
- At least one of supplier_id or import_batch_id must be provided
- If both provided: filter by both
- If neither: return 400 Bad Request

**Response:**
```json
{
  "processed_items": 10,
  "proposed_mappings": 25,
  "tasks_created": 2
}
```

**Status codes:**
- 200: Success
- 400: Invalid request (no filters provided)
- 404: Supplier or import_batch not found
- 500: Internal error

---

### B) Tasks list endpoint
**Route:** `GET /admin/normalization/tasks`

**Query params:**
- `status`: filter by task status (open, in_progress, done)
- `supplier_id`: filter by supplier
- `limit`: max results (default 50)
- `offset`: pagination offset (default 0)

**Response:**
```json
{
  "tasks": [
    {
      "id": "uuid",
      "supplier_item_id": "uuid",
      "reason": "Low confidence: 0.45",
      "priority": 150,
      "status": "open",
      "assigned_to": null,
      "created_at": "2025-01-12T...",
      "supplier_item": {
        "id": "uuid",
        "raw_name": "Роза неизвестная 60см",
        "raw_group": null,
        "name_norm": "роза неизвестная 60",
        "attributes": {}
      },
      "proposed_mappings": [
        {
          "id": "uuid",
          "normalized_sku_id": "uuid",
          "confidence": 0.45,
          "sku_title": "Rose Standard",
          "sku_variety": null
        }
      ],
      "sample_raw_rows": [
        {
          "raw_text": "Роза неизвестная 60см | 120"
        }
      ]
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Notes:**
- Join with `supplier_items` to get item details
- Join with `sku_mappings` (status=proposed) to get top proposals
- Optionally join with `raw_rows` via `offer_candidates` to show sample data (limit 3 rows)
- Order by priority DESC, created_at ASC

---

### C) Confirm mapping endpoint
**Route:** `POST /admin/normalization/confirm`

**Request body:**
```json
{
  "supplier_item_id": "uuid",
  "normalized_sku_id": "uuid",
  "notes": "Manual confirmation after review"
}
```

**Behavior (TRANSACTIONAL):**
1. Start transaction
2. Verify supplier_item exists
3. Verify normalized_sku exists
4. Update/Insert sku_mapping:
   - Set ALL existing mappings for supplier_item_id to status='rejected'
   - UPSERT selected mapping:
     - If exists with status=proposed: update to confirmed
     - If not exists: create new
   - Set fields:
     - `status = "confirmed"`
     - `method = "manual"`
     - `confidence = 1.0`
     - `decided_at = now()`
     - `decided_by = null` (MVP: no auth)
     - `notes = provided_notes`
5. Mark related normalization_task (if exists) as status='done'
6. Commit transaction
7. Return updated mapping

**Response:**
```json
{
  "mapping": {
    "id": "uuid",
    "supplier_item_id": "uuid",
    "normalized_sku_id": "uuid",
    "status": "confirmed",
    "confidence": 1.0,
    "method": "manual",
    "decided_at": "2025-01-12T...",
    "notes": "Manual confirmation..."
  }
}
```

**Status codes:**
- 200: Success
- 400: Invalid request
- 404: Supplier item or SKU not found
- 409: Conflict (should not happen if logic is correct)
- 500: Internal error

**Critical:** This endpoint MUST enforce the DB constraint:
- Only ONE confirmed mapping per supplier_item
- The unique partial index ensures this at DB level

---

## Implementation structure

### File: `apps/api/routers/normalization.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Pydantic schemas
class ProposeRequest(BaseModel):
    supplier_id: UUID | None = None
    import_batch_id: UUID | None = None
    limit: int = 1000

class ProposeResponse(BaseModel):
    processed_items: int
    proposed_mappings: int
    tasks_created: int

class TaskResponse(BaseModel):
    # ... full schema

class ConfirmRequest(BaseModel):
    supplier_item_id: UUID
    normalized_sku_id: UUID
    notes: str | None = None

class ConfirmResponse(BaseModel):
    # ... mapping schema

# Endpoints
@router.post("/propose", response_model=ProposeResponse)
async def propose_mappings(
    request: ProposeRequest,
    db: AsyncSession = Depends(get_db),
) -> ProposeResponse:
    # Implementation

@router.get("/tasks", response_model=TasksListResponse)
async def list_tasks(
    status: str | None = None,
    supplier_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> TasksListResponse:
    # Implementation

@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_mapping(
    request: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> ConfirmResponse:
    # Implementation
```

### Register router in `apps/api/main.py`:
```python
from apps.api.routers import normalization

app.include_router(
    normalization.router,
    prefix="/admin/normalization",
    tags=["normalization"]
)
```

---

## Required tests

### Integration test (`tests/integration/test_normalization_endpoints.py`):

**Test 1: Propose flow**
1. Setup: create supplier, import CSV, bootstrap dictionary, create SKUs
2. POST /admin/normalization/propose with supplier_id
3. Assert: 200 OK, counts > 0

**Test 2: List tasks**
1. After propose, GET /admin/normalization/tasks?status=open
2. Assert: tasks returned with supplier_item details

**Test 3: Confirm mapping**
1. Get task from list
2. POST /admin/normalization/confirm with supplier_item_id and sku_id
3. Assert: 200 OK, mapping confirmed
4. GET task again: status should be 'done'

**Test 4: Idempotency**
1. Run propose twice
2. Assert: second run doesn't create duplicates

**Test 5: Confirm constraint**
1. Confirm mapping for item A → SKU 1
2. Try to confirm item A → SKU 2
3. Assert: OLD mapping rejected, NEW mapping confirmed

---

## Non-goals (explicitly do NOT implement)
- Authentication/authorization (no decided_by for MVP)
- Bulk confirm endpoint
- Task assignment workflow
- Real-time updates / websockets

---

## Definition of Done
- All 3 endpoints implemented and working
- Propose endpoint validates inputs correctly
- Tasks endpoint returns enriched data (item + mappings + samples)
- Confirm endpoint is transactional and enforces uniqueness
- Integration tests pass (5 test cases)
- Endpoints documented in Swagger (automatic via FastAPI)
- Logging added for all operations

---

## Output format for your response
1) Plan (endpoint by endpoint breakdown)
2) Implementation notes (transaction handling, error cases)
3) Files created/changed
4) Test commands (curl examples)
5) DoD checklist results
