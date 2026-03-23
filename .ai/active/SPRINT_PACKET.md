# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 2: Typed Memory Backbone

## Sprint Type

feature

## Sprint Reason

Phase 2 planning reset is complete and merged. The next required build seam is typed memory infrastructure so continuity-first capture, open loops, resumption, and later multi-agent vertical profiles can reuse one durable substrate.

## Sprint Intent

Implement typed memory metadata end-to-end (schema, store, contracts/API, compiler serialization, memory UI, tests) without widening into open-loop workflows, resumption generation, or worker orchestration.

## Git Instructions

- Branch Name: `codex/phase2-sprint2-typed-memory-backbone`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Phase 2 now defines continuity-first outcomes; current memory model is too flat.
- Sprint 2 typed memory backbone is the critical dependency for Sprint 3 capture/open-loop domain.
- This is the narrowest high-leverage seam that advances Phase 2 without scope creep.

## Design Truth

- Extend existing memory architecture; do not create parallel memory stacks.
- Keep behavior deterministic, test-backed, and audit-friendly.
- Preserve current review and explainability guarantees.

## Exact Surfaces In Scope

- memory schema + persistence
- memory contracts + API behavior
- compiler context-pack memory serialization
- `/memories` UI typed metadata adoption
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

- Add typed memory fields:
  - `memory_type`
  - `confidence`
  - `salience`
  - `confirmation_status`
  - `valid_from`
  - `valid_to`
  - `last_confirmed_at`
- Persist/retrieve typed metadata through store + API.
- Keep revisions append-only and metadata-auditable.
- Include typed metadata in compiler memory serialization.
- Render typed metadata in `/memories` list/detail with safe fallbacks.
- Add/update tests across migration, API, compiler, and UI seams.

## Out of Scope

- open-loop records/workflows
- capture classification pipeline
- resumption brief generation
- focus dashboard
- worker activation
- connector expansion
- Phase 3 agent runtime/profile implementation

## Required Deliverables

- migration-backed typed memory metadata support
- backend store/contracts/API support for typed memory fields
- compiler serialization of typed memory metadata
- `/memories` typed metadata visibility + filtering
- updated sprint reports for this sprint only

## Acceptance Criteria

- typed memory metadata persists and returns from list/detail APIs
- invalid `memory_type` values are rejected deterministically
- revision guarantees remain append-only and correct
- compiled context includes typed memory metadata
- `/memories` reflects typed metadata without regression
- backend + frontend tests pass for touched seams
- no out-of-scope feature work enters sprint

## Implementation Constraints

- preserve RLS and per-user isolation
- preserve deterministic ordering in compiler/review outputs
- keep defaults backward-safe when typed metadata is absent
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
- exact typed fields shipped
- migration id(s) and API surface deltas
- exact commands/tests run with outcomes
- explicit deferred scope (open loops/resumption/workers/Phase 3 runtime)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained typed-memory-backbone scoped
- schema/store/contracts/compiler/UI consistency
- sufficient tests for all touched seams
- no hidden scope expansion

## Exit Condition

This sprint is complete when typed memory metadata is fully wired through persistence, API, compiler, and `/memories` UI with deterministic, test-backed behavior and no open-loop or Phase 3 runtime scope expansion.
