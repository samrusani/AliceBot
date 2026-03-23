# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 3: Capture Classification And Open-Loop Backbone

## Sprint Type

feature

## Sprint Reason

Phase 2 Sprint 2 typed memory backbone is merged. The next dependency is a first-class open-loop domain so unresolved commitments can be captured, reviewed, and resolved deterministically instead of inferred ad hoc from raw memory entries.

## Sprint Intent

Implement a narrow open-loop backbone (schema, store, contracts/API, compiler inclusion, and `/memories` review adoption) using the shipped typed-memory substrate, without introducing automation or worker orchestration.

## Git Instructions

- Branch Name: `codex/phase2-sprint3-open-loop-backbone`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Typed memory is now available; unresolved intent still has no dedicated lifecycle seam.
- Open loops are required before continuity-first resumption can be accurate.
- This keeps scope narrow while creating a reusable seam for later vertical agents.

## Design Truth

- Reuse current memory and continuity seams; do not create a parallel capture stack.
- Keep open-loop lifecycle deterministic and auditable.
- Preserve append-only revision guarantees and per-user isolation.

## Exact Surfaces In Scope

- open-loop schema + persistence
- open-loop contracts + API behavior
- compiler context-pack open-loop serialization
- `/memories` open-loop review adoption
- sprint-scoped backend and frontend tests

## Exact Files In Scope

- [store.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/store.py)
- [contracts.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/contracts.py)
- [memory.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/memory.py)
- [main.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/main.py)
- [compiler.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/compiler.py)
- [api.ts](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/lib/api.ts)
- [page.tsx](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/app/memories/page.tsx)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)
- relevant migration + tests under:
  - `apps/api/alembic/versions/`
  - `tests/unit/`
  - `tests/integration/`
  - `apps/web/**/*.test.tsx`

## In Scope

- Add an `open_loops` table with deterministic lifecycle fields:
  - `id`, `user_id`, `memory_id`, `title`, `status`, `opened_at`, `due_at`, `resolved_at`, `resolution_note`, `created_at`, `updated_at`
- Add lifecycle domain validation for `status` (`open`, `resolved`, `dismissed`).
- Add store methods for create/list/detail/update-status with strict user scoping.
- Add API endpoints:
  - `GET /v0/open-loops`
  - `GET /v0/open-loops/{open_loop_id}`
  - `POST /v0/open-loops`
  - `POST /v0/open-loops/{open_loop_id}/status`
- Extend memory admission flow to allow optional open-loop creation when memory candidate includes `open_loop` payload.
- Include top open loops in compiled context payload with deterministic ordering and bounded limits.
- Show open-loop summary/list and selected detail in `/memories` with safe live/fixture fallbacks.
- Add/update tests across migration, store, API, compiler, and UI seams.

## Out of Scope

- autonomous follow-up execution or reminders
- resumption brief synthesis
- background workers or scheduler integration
- connector expansion
- multi-agent runtime/profile routing (Phase 3)
- broad UI redesign outside `/memories`

## Required Deliverables

- migration-backed open-loop domain
- backend store/contracts/API support for open-loop lifecycle
- compiler serialization for open-loop context slice
- `/memories` open-loop review surface (summary + detail)
- updated sprint reports for this sprint only

## Acceptance Criteria

- open loops persist and return from list/detail APIs with strict per-user isolation
- invalid open-loop status values are rejected deterministically (`400`)
- status transitions (`open` -> `resolved`/`dismissed`) persist audit fields correctly
- memory admission can create an open loop when requested, without regressing existing admissions
- compiled context includes open loops deterministically when present
- `/memories` renders open-loop summary and selected details without regression
- backend + frontend tests pass for touched seams
- no out-of-scope automation or orchestration work enters sprint

## Implementation Constraints

- preserve RLS and per-user isolation
- keep deterministic ordering in API and compiler outputs
- keep backward-safe defaults for memory admission without open-loop payload
- co-deliver tests with each seam change

## Control Tower Task Cards

### Task 1: Schema + Store
Owner: backend operative A  
Write scope:
- migration file(s)
- `apps/api/src/alicebot_api/store.py`
- store/migration tests

### Task 2: Contracts + API
Owner: backend operative B  
Write scope:
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- API/integration tests

### Task 3: Compiler Integration
Owner: backend operative C  
Write scope:
- `apps/api/src/alicebot_api/compiler.py`
- compiler tests

### Task 4: Memory UI Adoption
Owner: frontend operative  
Write scope:
- `apps/web/lib/api.ts`
- `apps/web/app/memories/page.tsx`
- related memory components/tests

### Task 5: Integration Review
Owner: control tower  
Responsibilities:
- verify schema/store/contracts/compiler/UI coherence
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact open-loop fields and endpoints shipped
- migration id(s) and API surface deltas
- exact commands/tests run with outcomes
- explicit deferred scope (resumption/workers/automation/Phase 3 runtime)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained open-loop-backbone scoped
- schema/store/contracts/compiler/UI consistency
- sufficient tests for all touched seams
- no hidden scope expansion

## Exit Condition

This sprint is complete when open loops are fully wired through persistence, API, compiler, and `/memories` review with deterministic, test-backed behavior and no automation/worker/Phase 3 scope expansion.
