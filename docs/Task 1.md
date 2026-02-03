# TASK 1 — Project scaffold + DB migrations + Minimal CSV import (F1)

You are working inside an existing repo. If the repo is empty, scaffold it. If it already has a structure/stack, adapt without rewriting everything.

## Goal
Deliver a working backend foundation that:
1) boots locally with Postgres,
2) applies migrations to create the MVP schema (based on `/docs/CORE_DATA_MODEL.md` and the provided DDL draft),
3) exposes minimal admin endpoints:
   - healthcheck
   - create/list suppliers
   - upload a CSV price list for a supplier (simple “row table” format F1)
4) runs an import pipeline for F1:
   - creates `import_batches` (received)
   - stores all rows to `raw_rows`
   - creates `parse_run`
   - creates/updates `supplier_items` (stable_key logic)
   - creates `offer_candidates` with:
     - price_min (required)
     - price_type fixed|range (detect simple ranges like 95-99 or 95–99)
     - pack_qty from “Кол-во” column when present and valid
     - length_cm extracted from name if present (e.g., “60см”, “60 см”, “60cm”)
     - origin_country extracted from parentheses if present (e.g., “(Эквадор)”)
   - writes `parse_events` for any row that cannot be parsed (bad price, missing name, etc.)
   - marks `import_batches.status = parsed` on success; `failed` on fatal errors

No normalization UI yet. No publishing yet. No orders yet.

## Default stack (if repo is empty)
- Python 3.12 + FastAPI
- SQLAlchemy 2.0 + Alembic
- pytest
- ruff + black
- docker compose for local Postgres

## Input format (F1)
Expect CSV with headers like:
- "НАИМЕНОВАНИЕ" (required)
- "Цена" or "ЦЕНА" (required)
- "Кол-во" (optional)
- "ЗАКАЗ" / "СУММА" may exist (ignore for now, but store raw)

Implement header normalization (case-insensitive, trim, handle Cyrillic variants).

## Files / Structure (target)
- `/apps/api` (FastAPI app)
- `/packages/core` (pure parsing functions)
- `/infra/docker-compose.yml`
- `/infra/db` (optional)
- `/docs` already exists; do not rewrite those docs

## Required deliverables
1) Migrations (Alembic) creating all tables needed for this task:
   - cities, suppliers, import_batches, raw_rows, parse_runs, parse_events, supplier_items, offer_candidates
   - plus required enums + extensions
2) API endpoints:
   - `GET /health`
   - `POST /admin/suppliers` (create)
   - `GET /admin/suppliers` (list)
   - `POST /admin/suppliers/{supplier_id}/imports/csv` (multipart upload OR accept file path in dev mode)
   - `GET /admin/imports/{import_batch_id}` (summary: counts, status, parse events count)
3) A CLI script for local dev:
   - `python -m apps.api.scripts.import_csv --supplier "NAME" --file "path/to.csv"`
4) Basic tests:
   - one unit test for price parsing (fixed vs range)
   - one unit test for length parsing
   - one integration test that imports a tiny CSV and asserts:
     - import_batches created
     - raw_rows count == input lines
     - supplier_items created
     - offer_candidates created with correct fields
5) `.env.example` + README instructions to run locally

## Constraints
- Keep changes minimal and focused on this task.
- No feature creep (no normalization publish, no orders).
- RAW must be immutable and stored.
- Use structured logging and meaningful error messages.
- Do not leave temporary files in repo.
- Provide clear commands to run.

## Definition of Done
- `docker compose up -d` starts Postgres
- `alembic upgrade head` succeeds
- `uvicorn` starts API and `/health` returns ok
- Upload/import endpoint works for a sample CSV
- Tests pass
- README updated with exact run commands

## Output format for your response
1) Plan
2) Implementation notes
3) Files created/changed (list)
4) Commands to run
5) DoD checklist results
