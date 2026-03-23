# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 4: Deterministic Resumption Briefs

## Sprint Type

feature

## Sprint Reason

Phase 2 Sprint 3 open-loop backbone is merged. The next continuity-first seam is deterministic resumption support so operators can re-enter a thread with a compact, auditable brief instead of manually reconstructing context from raw events, memories, and open loops.

## Sprint Intent

Implement a bounded resumption-brief read seam (contracts, API, compiler-backed assembly, and `/chat` display adoption) without introducing automation, autonomous follow-up behavior, or worker orchestration.

## Git Instructions

- Branch Name: `codex/phase2-sprint4-resumption-briefs`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Typed memories and open loops are now shipped and stable.
- `/chat` still requires manual reconstruction to resume a thread efficiently.
- A deterministic brief seam is required before any future automation or vertical-agent specialization.

## Design Truth

- Reuse existing continuity, memory, and open-loop seams; do not create a parallel context pipeline.
- Build brief generation as deterministic assembly from durable records, not free-form model synthesis.
- Preserve per-user isolation and existing append-only audit guarantees.

## Exact Surfaces In Scope

- resumption-brief contracts + API behavior
- compiler-backed deterministic brief assembly
- `/chat` brief visibility for selected thread
- sprint-scoped backend and frontend tests

## Exact Files In Scope

- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [main.py](apps/api/src/alicebot_api/main.py)
- [compiler.py](apps/api/src/alicebot_api/compiler.py)
- [api.ts](apps/web/lib/api.ts)
- [page.tsx](apps/web/app/chat/page.tsx)
- [thread-summary.tsx](apps/web/components/thread-summary.tsx)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant tests under:
  - `tests/unit/`
  - `tests/integration/`
  - `apps/web/**/*.test.tsx`

## In Scope

- Add resumption-brief contracts (request/response schema) with explicit, typed fields.
- Add API endpoint:
  - `GET /v0/threads/{thread_id}/resumption-brief`
- Assemble brief deterministically from existing durable seams:
  - selected thread metadata
  - latest conversation events
  - active open loops
  - bounded memory highlights
  - latest workflow/task-step posture when present
- Include deterministic ordering and bounded limits for each brief section.
- Expose brief in `/chat` selected-thread summary panel with live/fixture/unavailable behavior parity.
- Add/update tests across API, compiler/assembly logic, and `/chat` UI seams.

## Out of Scope

- new database tables or migration work
- autonomous follow-up execution or reminders
- background workers or scheduler integration
- connector expansion
- multi-agent runtime/profile routing (Phase 3)
- broad UI redesign outside `/chat`

## Required Deliverables

- backend contracts/API for deterministic resumption brief read
- compiler or dedicated assembly helper for deterministic brief construction
- `/chat` resumption-brief display for selected thread
- updated sprint reports for this sprint only

## Acceptance Criteria

- endpoint returns deterministic brief payload for a selected thread with strict per-user isolation
- missing/cross-user thread behavior is deterministic (`404`)
- brief sections use bounded limits and stable ordering
- brief reflects active open loops and recent continuity evidence when present
- `/chat` renders brief content with live/fixture/unavailable states and no regression to existing chat workflow surfaces
- backend + frontend tests pass for touched seams
- no out-of-scope automation, worker, or Phase 3 routing work enters sprint

## Implementation Constraints

- preserve RLS and per-user isolation
- keep deterministic ordering in API and compiler outputs
- keep brief generation model-free and source-attributed to durable seams
- co-deliver tests with each seam change

## Control Tower Task Cards

### Task 1: Contracts + API
Owner: backend operative A  
Write scope:
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- API/integration tests

### Task 2: Deterministic Brief Assembly
Owner: backend operative B  
Write scope:
- `apps/api/src/alicebot_api/compiler.py`
- compiler tests

### Task 3: Chat UI Adoption
Owner: frontend operative  
Write scope:
- `apps/web/lib/api.ts`
- `apps/web/app/chat/page.tsx`
- `apps/web/components/thread-summary.tsx`
- related chat components/tests

### Task 4: Integration Review
Owner: control tower  
Responsibilities:
- verify contracts/API/assembly/UI coherence
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact resumption-brief fields and endpoint shipped
- API surface deltas and deterministic ordering rules
- exact commands/tests run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained deterministic-resumption-brief scoped
- contracts/API/assembly/UI consistency
- sufficient tests for all touched seams
- no hidden scope expansion

## Exit Condition

This sprint is complete when deterministic resumption briefs are exposed through a user-scoped API seam and surfaced in `/chat` selected-thread review with test-backed behavior and no automation/worker/Phase 3 scope expansion.
