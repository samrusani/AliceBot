# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 6: Unified Explicit Signal Capture

## Sprint Type

feature

## Sprint Reason

Phase 2 Sprint 5 explicit commitment capture is merged. Explicit extraction is now split across two separate endpoints, which creates operator overhead and inconsistent capture flow. The next seam is one deterministic capture endpoint that runs both explicit preference and explicit commitment extraction for a single user message.

## Sprint Intent

Implement a bounded, deterministic unified capture endpoint that orchestrates existing explicit preference and explicit commitment extraction pipelines for one `message.user` source event, without introducing automation or background workers.

## Git Instructions

- Branch Name: `codex/phase2-sprint6-unified-explicit-signal-capture`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Typed memory, open-loop lifecycle, resumption briefs, and explicit commitment extraction are shipped.
- Capture still requires separate calls (`extract-explicit-preferences` and `extract-explicit-commitments`) for one message event.
- A unified deterministic capture seam is the lowest-risk step before any optional UI-triggered capture workflow.

## Design Truth

- Reuse existing extraction modules; do not duplicate extraction logic.
- Keep capture deterministic and pattern-based with zero model calls.
- Preserve per-user isolation, append-only revision guarantees, and open-loop dedupe behavior.

## Exact Surfaces In Scope

- unified capture contracts + API behavior
- deterministic orchestration over existing extraction pipelines
- web API client adoption for the unified endpoint
- sprint-scoped backend and frontend tests

## Exact Files In Scope

- [explicit_signal_capture.py](apps/api/src/alicebot_api/explicit_signal_capture.py)
- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [main.py](apps/api/src/alicebot_api/main.py)
- [explicit_preferences.py](apps/api/src/alicebot_api/explicit_preferences.py)
- [explicit_commitments.py](apps/api/src/alicebot_api/explicit_commitments.py)
- [api.ts](apps/web/lib/api.ts)
- [api.test.ts](apps/web/lib/api.test.ts)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant tests under:
  - `tests/unit/`
  - `tests/integration/`
  - `apps/web/**/*.test.tsx`

## In Scope

- Add typed contracts for unified capture request/response.
- Add API endpoint:
  - `POST /v0/memories/capture-explicit-signals`
- Endpoint input:
  - `user_id` (required)
  - `source_event_id` (required; must reference a user-owned `message.user` event)
- Deterministically orchestrate both pipelines for the same source event:
  - explicit preference extraction/admission
  - explicit commitment extraction/admission/open-loop outcomes
- Preserve current deterministic validation semantics for invalid/non-user/missing/cross-user source event requests.
- Return unified response with per-pipeline sections and aggregate summary:
  - `preferences`: candidates/admissions/summary
  - `commitments`: candidates/admissions/summary
  - `summary`: aggregate counts and source event metadata
- Keep existing endpoints fully backward compatible:
  - `POST /v0/memories/extract-explicit-preferences`
  - `POST /v0/open-loops/extract-explicit-commitments`
- Add web API client function for unified endpoint and tests for request wiring.
- Add/update unit and integration tests for orchestration correctness, deterministic ordering of section execution, and repeat-call idempotence behavior.

## Out of Scope

- autonomous follow-up execution or reminders
- background workers or scheduler integration
- connector expansion
- multi-agent runtime/profile routing (Phase 3)
- free-form model-based extraction or classification
- broad UI redesign or automatic capture triggers in `/chat`/`/memories`

## Required Deliverables

- backend contracts/API for unified explicit signal capture
- deterministic orchestration module with tests
- web API client support for unified capture endpoint
- updated sprint reports for this sprint only

## Acceptance Criteria

- unified endpoint returns deterministic payload with strict per-user isolation
- invalid/missing/non-user-message `source_event_id` returns deterministic `400`
- unified payload contains preference section, commitment section, and aggregate summary with coherent counts
- repeat calls for the same source event preserve no-duplicate-active-open-loop behavior
- legacy explicit extraction endpoints remain operational and unchanged in behavior
- backend + frontend tests pass for touched seams
- no out-of-scope automation, worker, or Phase 3 routing work enters sprint

## Implementation Constraints

- preserve RLS and per-user isolation
- keep extraction deterministic and pattern-based (no model calls)
- keep orchestration sequence explicit and stable (preferences first, commitments second)
- keep memory/open-loop evidence source-attributed to the original event
- co-deliver tests with each seam change

## Control Tower Task Cards

### Task 1: Contracts + API
Owner: backend operative A  
Write scope:
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- API/integration tests

### Task 2: Orchestration Module
Owner: backend operative B  
Write scope:
- `apps/api/src/alicebot_api/explicit_signal_capture.py`
- `apps/api/src/alicebot_api/explicit_preferences.py`
- `apps/api/src/alicebot_api/explicit_commitments.py`
- unit tests

### Task 3: Web API Client
Owner: frontend operative  
Write scope:
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`

### Task 4: Integration Review
Owner: control tower  
Responsibilities:
- verify contracts/API/orchestration/client coherence
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact unified endpoint payload schema
- orchestration sequence and legacy-endpoint compatibility notes
- dedupe/no-side-effect guarantees
- exact commands/tests run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained unified-explicit-signal-capture scoped
- contracts/API/orchestration/client consistency
- sufficient tests for all touched seams
- no hidden scope expansion

## Exit Condition

This sprint is complete when unified explicit-signal capture is available through one user-scoped deterministic endpoint, correctly orchestrates preference and commitment extraction without regressions to legacy endpoints, and passes sprint-scoped tests without automation/worker/Phase 3 scope expansion.
