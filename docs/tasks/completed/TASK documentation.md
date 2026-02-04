# TECHNICAL TASK
## Documentation Program for B2B Flower Market Platform

---

## 0. Purpose of this Technical Task

This task defines a **complete documentation program** for the B2B Flower Market Platform.

The goal is to:
- make the system fully explainable without reading code
- protect data correctness and normalization logic
- reduce onboarding and refactoring cost
- allow Cloud Code and engineers to work safely and incrementally
- preserve architectural decisions and domain knowledge

This task is **documentation-only**.
No product features are added unless documentation reveals inconsistencies.

---

## 1. Global Documentation Principles (mandatory)

These rules apply to **all documents** created in this task.

### 1.1 Reality-first principle
Documentation must describe **how the system actually works today**, not an idealized future.

If behavior is messy or constrained — document it explicitly.

---

### 1.2 Data-first principle
The core product asset is **data quality and normalization**, not UI.

Documents must prioritize:
- data lifecycle
- invariants
- contracts
- failure modes

---

### 1.3 Update discipline (non-negotiable)
If during development:
- data behavior changes → update docs
- normalization logic changes → update docs
- API schema changes → update docs
- assumptions change → update docs

Documentation updates are part of the **Definition of Done**.

---

### 1.4 Format & language
- Format: **Markdown (.md)**
- Language: **English**
- Tone: technical, explicit, unambiguous
- No placeholders like “TBD” unless explicitly allowed

---

## 2. Documentation Structure (target)

The final documentation set must cover:

1. Architecture
2. Core workflows
3. Data lifecycle & invariants
4. Backend API contracts
5. Normalization algorithm & rules
6. Failure modes & edge cases
7. Operational & scaling assumptions
8. Decision history (ADR)

Each block is defined as a task below.

---

## TASK 1 — ARCHITECTURE.md

### Goal
Describe the **structural architecture** of the platform and boundaries between components.

---

### Why this document is required
- Prevents accidental coupling of parsing, normalization, and publishing
- Allows safe refactoring
- Makes system navigable for new engineers and Cloud Code

---

### Document to create
`/docs/ARCHITECTURE.md`

---

### Must describe

1. High-level system overview
2. Major components:
   - API layer (FastAPI)
   - Core logic (`packages/core`)
   - Database (PostgreSQL)
   - Migrations (Alembic)
   - Background scripts / CLI
3. Responsibility boundaries:
   - where parsing lives
   - where normalization lives
   - where publishing lives
   - where orders live
4. Dependency rules:
   - what must remain pure
   - what can access DB
5. Data flow overview (textual diagram)

---

### Acceptance criteria
A reader can answer:
- “Where does this logic belong?”
- “What must stay pure?”
- “What breaks if I change this?”

---

## TASK 2 — WORKFLOWS.md

### Goal
Document **end-to-end business and data workflows**.

---

### Why this document is required
- Prevents regressions in multi-step flows
- Makes side effects explicit
- Serves as operational truth

---

### Document to create
`/docs/WORKFLOWS.md`

---

### Must include workflows

1. Supplier onboarding
2. CSV import (happy path)
3. CSV import (error paths)
4. Parsing & parse events
5. Normalization propose flow
6. Manual review flow
7. Mapping confirmation
8. Offer publishing
9. Retail offer search
10. Order creation
11. Supplier confirm / reject
12. Metrics & reporting

---

### Each workflow must describe
- Entry conditions
- Step-by-step actions
- Data created/modified
- Status transitions
- Exit conditions
- Failure points

---

### Acceptance criteria
- Workflow can be replayed mentally without code
- All side effects are explicit

---

## TASK 3 — DATA_LIFECYCLE.md

### Goal
Define **how data lives, evolves, and never corrupts history**.

---

### Why this document is required
This project is **data-first**.
Data lifecycle is the product.

---

### Document to create
`/docs/DATA_LIFECYCLE.md`

---

### Must describe

1. RAW data immutability
2. Import batches lifecycle
3. Supplier items evolution
4. Offer candidates lifecycle
5. Normalization mappings lifecycle
6. Offers lifecycle (replace-all strategy)
7. Orders lifecycle
8. Historical preservation rules

---

### Key invariants to document
- What is immutable
- What can be regenerated
- What must never be deleted
- What is versioned implicitly

---

### Acceptance criteria
- Data recovery strategies are clear
- Historical data safety is obvious

---

## TASK 4 — BACKEND_API.md

### Goal
Create a **formal backend API contract**.

---

### Why this document is required
- README is not a contract
- Prevents silent API drift
- Allows backend/frontend parallel work

---

### Document to create
`/docs/BACKEND_API.md`

---

### Must describe

For **each endpoint**:
- HTTP method & path
- Purpose
- Auth assumptions (MVP vs future)
- Request schema
- Response schema
- Status codes
- Idempotency expectations
- Error behavior

Include sections for:
- Admin API
- Retail API
- Internal/system endpoints

---

### Acceptance criteria
- Endpoint behavior is unambiguous
- Payloads match real implementation

---

## TASK 5 — NORMALIZATION_ALGORITHM.md

### Goal
Document the **core normalization intelligence** of the platform.

---

### Why this document is required
Normalization logic is the **key IP** of the product.

Without documentation:
- fixes become dangerous
- algorithm becomes unmaintainable

---

### Document to create
`/docs/NORMALIZATION_ALGORITHM.md`

---

### Must describe

1. Attribute extraction logic
2. Dictionary roles (types, synonyms, stopwords)
3. Candidate SKU search strategy:
   - exact
   - generic
   - similarity
4. Confidence score signals
5. Thresholds and their meaning
6. When manual tasks are created
7. Why “reject all → confirm one” is enforced

---

### Acceptance criteria
- Algorithm decisions are explainable
- Future tuning is safe

---

## TASK 6 — FAILURE_MODES.md

### Goal
Catalog **known and expected failure scenarios**.

---

### Why this document is required
Real supplier data is chaotic.
Failures are normal and must be predictable.

---

### Document to create
`/docs/FAILURE_MODES.md`

---

### Must include

- Invalid prices
- Broken ranges
- Mixed bundles
- Ambiguous names
- Conflicting dictionary rules
- Low-confidence normalization
- Partial publish
- Order edge cases

For each:
- Symptoms
- Root causes
- Detection
- Recovery strategy

---

### Acceptance criteria
- Failures are actionable, not mysterious

---

## TASK 7 — OPERATIONS.md

### Goal
Prepare the system for **production operation and scaling**.

---

### Why this document is required
Prevents chaos at first real load.

---

### Document to create
`/docs/OPERATIONS.md`

---

### Must describe

- Metrics to monitor
- Parse/normalization health indicators
- Publish safety checks
- Re-import strategy
- Rollback strategy
- Safe migration practices

---

### Acceptance criteria
- System behavior under load is predictable

---

## TASK 8 — ADR (Architecture Decision Records)

### Goal
Preserve **why key decisions were made**.

---

### Why this document is required
Prevents endless re-debates.

---

### Structure to create
`/docs/adr/`

---

### Must include ADRs for
- RAW immutability
- Replace-all publish strategy
- Single-supplier orders (MVP)
- No inventory checks
- Dictionary-driven normalization

---

### ADR format
Each ADR must include:
- Context
- Decision
- Consequences

---

## 3. Execution Rules

### 3.1 Order of execution
Tasks must be completed in this order:

1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

---

### 3.2 Task completion rules
A task is complete only when:
- Document is written
- Matches current system behavior
- Terminology is consistent
- Committed and pushed to Git

---

### 3.3 Git discipline
After each completed task:
- Commit documentation
- Use clear commit message
- Push changes

---

## 4. Final Outcome

After completing all tasks:

- The system is fully explainable without code
- Normalization logic is protected
- Data corruption risks are minimized
- Cloud Code can safely evolve the platform
- Knowledge becomes institutional, not tribal

---
