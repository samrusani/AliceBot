# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 5: Explicit Commitment Capture

## Sprint Type

feature

## Sprint Reason

Phase 2 Sprint 4 deterministic resumption briefs are merged. The next missing continuity seam is explicit commitment capture so user-stated follow-ups can become governed open-loop records without manual data entry.

## Sprint Intent

Implement a bounded explicit-commitment extraction seam that reads one `message.user` event and creates a deterministic open-loop record (plus linked memory evidence) through existing governed admission pathways, without automation or worker orchestration.

## Git Instructions

- Branch Name: `codex/phase2-sprint5-explicit-commitment-capture`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Typed memory, open-loop lifecycle, and resumption brief seams are now shipped.
- Commitment capture is still manual and creates operator friction.
- A deterministic extraction seam is required before safe future reminder/orchestration work.

## Design Truth

- Reuse existing continuity events, memory admission, and open-loop seams; do not add parallel storage.
- Keep extraction pattern-driven and deterministic; no model-based interpretation.
- Preserve per-user isolation, append-only memory revision guarantees, and auditable source linkage.

## Exact Surfaces In Scope

- commitment extraction contracts + API behavior
- deterministic pattern extraction and admission orchestration
- `/memories` review parity (captured open-loop + linked memory evidence visible through existing surfaces)
- sprint-scoped backend and frontend tests

## Exact Files In Scope

- [explicit_commitments.py](apps/api/src/alicebot_api/explicit_commitments.py)
- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [main.py](apps/api/src/alicebot_api/main.py)
- [memory.py](apps/api/src/alicebot_api/memory.py)
- [store.py](apps/api/src/alicebot_api/store.py)
- [api.ts](apps/web/lib/api.ts)
- [page.tsx](apps/web/app/memories/page.tsx)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant tests under:
  - `tests/unit/`
  - `tests/integration/`
  - `apps/web/**/*.test.tsx`

## In Scope

- Add typed contracts for explicit commitment extraction request/response.
- Add API endpoint:
  - `POST /v0/open-loops/extract-explicit-commitments`
- Endpoint input:
  - `user_id` (required)
  - `source_event_id` (required; must reference a user-owned `message.user` event)
- Deterministically extract commitment candidates from explicit patterns (for example: `remind me to ...`, `i need to ...`, `don't let me forget to ...`, `remember to ...`), with bounded normalization and clause rejection rules.
- Persist extracted commitments through existing governed seams:
  - admit/update a linked memory evidence record
  - create an open-loop record linked to that memory when no active open loop already exists for the same memory
- Return deterministic extraction summary including:
  - candidate count
  - admitted-memory decisions
  - open-loop create/noop outcomes
  - source event identity/kind
- Add/update `/memories` API wiring/tests if needed so newly captured commitment loops and linked memory evidence remain visible with existing live/fixture/unavailable behavior.
- Add/update tests across extraction logic, endpoint behavior, user isolation, and deterministic idempotence-on-repeat for the same source event.

## Out of Scope

- autonomous follow-up execution or reminders
- background workers or scheduler integration
- connector expansion
- multi-agent runtime/profile routing (Phase 3)
- free-form model-based extraction or classification
- broad UI redesign outside `/memories`

## Required Deliverables

- backend contracts/API for explicit commitment extraction
- deterministic extraction module with tests
- governed admission + open-loop creation orchestration with duplicate-open-loop guard for repeated source events
- updated sprint reports for this sprint only

## Acceptance Criteria

- endpoint returns deterministic extraction payload with strict per-user isolation
- invalid/missing/non-user-message `source_event_id` returns deterministic `400`
- cross-user or missing event access is rejected deterministically without side effects
- supported explicit commitment statements produce candidate(s), memory admission(s), and open-loop outcome(s)
- repeated extraction for the same source event does not create duplicate active open loops for the same derived commitment memory
- `/memories` existing review surfaces continue to show resulting open-loop and memory evidence without regression
- backend + frontend tests pass for touched seams
- no out-of-scope automation, worker, or Phase 3 routing work enters sprint

## Implementation Constraints

- preserve RLS and per-user isolation
- keep extraction deterministic and pattern-based (no model calls)
- keep memory/open-loop evidence source-attributed to the original event
- co-deliver tests with each seam change

## Control Tower Task Cards

### Task 1: Contracts + API
Owner: backend operative A  
Write scope:
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- API/integration tests

### Task 2: Extraction + Admission Orchestration
Owner: backend operative B  
Write scope:
- `apps/api/src/alicebot_api/explicit_commitments.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/store.py`
- unit tests

### Task 3: Web Surface Compatibility
Owner: frontend operative  
Write scope:
- `apps/web/lib/api.ts`
- `apps/web/app/memories/page.tsx`
- related memory components/tests

### Task 4: Integration Review
Owner: control tower  
Responsibilities:
- verify contracts/API/extraction/admission/UI coherence
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact extraction patterns, endpoint, and payload fields shipped
- API surface deltas and dedupe/no-side-effect rules
- exact commands/tests run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained explicit-commitment-capture scoped
- contracts/API/extraction/admission/UI consistency
- sufficient tests for all touched seams
- no hidden scope expansion

## Exit Condition

This sprint is complete when explicit commitment extraction is available through a user-scoped deterministic API seam, persists through governed memory/open-loop pathways with repeat-call duplicate protection, and passes sprint-scoped tests without automation/worker/Phase 3 scope expansion.
