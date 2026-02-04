# CLAUDE.md — B2B Flower Market Platform (Engineering Playbook)

## 0) Context (read first)
This repository implements a data-first B2B marketplace for wholesale flowers in a single city.

The core asset is the normalized market database (not the UI). The MVP focus:
- ingest supplier price lists (CSV/XLSX first-class),
- preserve RAW immutably,
- parse into typed records,
- normalize supplier items to canonical SKUs via dictionary + manual review,
- publish offers for retail search,
- minimal order flow (no payments).

### Canonical docs (must read before coding)
- `/docs/architecture/VISION.md`
- `/docs/architecture/MVP_SCOPE.md`
- `/docs/architecture/CORE_DATA_MODEL.md`
- `/docs/architecture/IMPORT_PIPELINE.md`
- `/docs/architecture/NORMALIZATION_RULES.md`

If anything conflicts, these docs are source-of-truth.

---

## 1) Operating Rules (non-negotiable)
1. **No scope creep:** implement only what the task asks + required plumbing.
2. **Data-first:** prioritize ingestion/normalization correctness over UI.
3. **RAW is immutable:** never mutate raw inputs; fixes happen via parsing rules/dictionaries/mappings.
4. **Small, reviewable changes:** produce incremental commits with clear diffs.
5. **Every change updates docs:** if behavior/DB/API changes, update relevant docs.
6. **No junk files:** do not leave temp files. Use `/tmp` only, never commit. Keep repo clean.
7. **Deterministic parsing:** parsing must be reproducible; log versions and decisions.
8. **Observability:** write structured logs, persist parse events, and make failures diagnosable.

---

## 2) Deliverables Format (what to output each task)
For each task, respond with:
1) **Plan** (steps + files to touch)
2) **Assumptions** (only if needed, minimal)
3) **Implementation notes** (important decisions)
4) **Commands to run** (local dev + tests)
5) **DoD checklist** (explicit verification)

---

## 3) Repository Layout (target)
- `/docs` — product + engineering docs
- `/apps/api` — backend API (ingestion, admin endpoints, orders)
- `/packages/core` — shared parsing/normalization logic (pure functions)
- `/infra` — docker compose, local tooling, migrations
- `/data` — sample inputs (non-sensitive), test fixtures

---

## 4) Tech Stack (default unless repo already dictates otherwise)
Stack: FastAPI async + SQLAlchemy async + Alembic + structlog + pytest + Postgres16

Реальные пути: apps/api, packages/core, infra, tests, data

---

## 5) Database & Migrations
- All schema changes must be in migrations.
- Tables/columns use `snake_case`.
- UUID primary keys default to `gen_random_uuid()`.
- Add indexes for hot paths:
  - supplier_items name matching
  - offers filtering
  - raw debug search (trgm)
- Prefer **soft deletes** only where explicitly needed; otherwise use status/is_active flags.

---

## 6) Ingestion Pipeline (contract)
Pipeline stages must map to:
- `import_batches` (received → parsed → published/failed)
- `raw_rows` (immutable)
- `parse_runs` + `parse_events`
- `supplier_items`
- `offer_candidates`
- normalization: `dictionary_entries`, `sku_mappings`, `normalization_tasks`
- publishing: `offers`

Publishing rule (MVP):
- only publish offers where mapping is **confirmed**
- publish only from latest successful import batch per supplier; old offers set `is_active=false`

---

## 7) Normalization Rules (contract)
- Dictionary-driven extraction + propose → manual confirm flow.
- Confidence thresholds are defined in `/docs/architecture/NORMALIZATION_RULES.md`.
- “Matrix” and “tiers” must be expanded into flat `offer_candidates`.
- “Bundle list in one row” default = SAFE MODE (manual review), unless explicitly enabled.

---

## 8) API Principles (MVP)
- Provide admin endpoints sufficient to:
  - create/list suppliers
  - upload/import a price list
  - inspect parse results/errors
  - review normalization tasks
  - confirm mappings
  - trigger republish

Keep endpoints minimal and documented.

---

## 9) Testing & Quality
Minimum for each implemented feature:
- Unit tests for parsing/normalization primitives
- Integration test for at least one “happy-path” import → parsed rows in DB
- Basic validation tests (bad prices, tier mismatch, etc.)

---

## 10) Security & Secrets
- Never commit secrets.
- Use `.env.example` for local config.
- Validate uploads (size/type).
- Store file references in DB (not raw file bytes in DB).

---

## 11) Definition of Done (global)
A task is done only when:
- DB migrations apply cleanly
- API starts locally
- Tests pass
- No leftover temp files
- Docs updated (if behavior/schema changed)
- Clear run instructions provided