# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 1: Multi-Agent Profile Backbone

## Sprint Type

feature

## Sprint Reason

Phase 2 closeout is complete and validation is green. The next non-redundant step is to open Phase 3 by introducing explicit agent profile identity so separate agents can be deployed without sharing one implicit runtime persona.

## Sprint Intent

Add a minimal, deterministic backend backbone for agent profiles and thread-level profile binding, without changing existing tool orchestration breadth or connector scope.

## Git Instructions

- Branch Name: `codex/phase3-sprint1-agent-profile-backbone`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- This is the first implementation seam required for “multiple separate agents.”
- It is orthogonal to completed Phase 2 hardening (gate/doc/closeout work), so it is not redundant.
- It creates a durable identity boundary before opening broader routing/orchestration work.

## Design Truth

- Keep existing default behavior for callers that do not provide a profile.
- Persist explicit profile identity on thread records.
- Keep the initial profile surface bounded: registry read + thread binding + response/compile propagation.
- Do not widen tool execution, connector actions, or worker orchestration in this sprint.

## Exact Surfaces In Scope

- agent profile contracts and deterministic in-process registry
- thread creation/list/detail profile binding
- context compile / response output includes active profile identity
- migration and tests for new thread profile column and behavior

## Exact Files In Scope

- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [main.py](apps/api/src/alicebot_api/main.py)
- [store.py](apps/api/src/alicebot_api/store.py)
- [phase3_profiles.py](apps/api/src/alicebot_api/phase3_profiles.py)
- [20260324_0032_thread_agent_profiles.py](apps/api/alembic/versions/20260324_0032_thread_agent_profiles.py)
- [test_continuity_api.py](tests/integration/test_continuity_api.py)
- [test_responses_api.py](tests/integration/test_responses_api.py)
- [test_20260324_0032_thread_agent_profiles.py](tests/unit/test_20260324_0032_thread_agent_profiles.py)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `./.venv/bin/python -m pytest tests/integration/test_continuity_api.py tests/integration/test_responses_api.py -q`
  - `./.venv/bin/python -m pytest tests/unit/test_20260324_0032_thread_agent_profiles.py -q`
  - `python3 scripts/run_phase2_validation_matrix.py`

## In Scope

- Add deterministic Phase 3 profile registry module with at least:
  - `assistant_default` profile
  - one additional profile (for example `coach_default`) with distinct id/name/description
- Add `agent_profile_id` thread column with migration:
  - non-null with deterministic default `assistant_default`
  - user-scoped reads preserved
- Extend thread create request to optionally accept `agent_profile_id`:
  - invalid profile id returns deterministic 422
  - omitted profile id uses default
- Expose profile identity in thread list/detail responses.
- Include active `agent_profile_id` in context compile and `/v0/responses` response metadata.
- Add a bounded read endpoint for available profiles:
  - `GET /v0/agent-profiles`

## Out of Scope

- per-profile model-provider switching
- external LLM provider integration changes
- auth model changes
- runner/worker orchestration
- connector scope expansion
- web UI profile selector

## Required Deliverables

- migration for thread profile binding
- profile registry and API read surface
- thread + compile + response profile propagation
- integration and migration tests passing
- updated sprint reports for this sprint only

## Acceptance Criteria

- Threads persist and return `agent_profile_id`.
- Creating a thread with a valid non-default profile succeeds and remains isolated per user.
- Creating a thread with invalid profile id fails deterministically.
- `/v0/agent-profiles` returns deterministic profile registry payload.
- `/v0/context/compile` and `/v0/responses` include active profile id metadata.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No out-of-scope behavior changes enter sprint.

## Implementation Constraints

- keep deterministic outputs and stable ordering
- do not introduce external dependencies
- preserve existing endpoint behavior when `agent_profile_id` is omitted
- keep migration reversible

## Control Tower Task Cards

### Task 1: Profile Registry + Contracts
Owner: tooling operative  
Write scope:
- `apps/api/src/alicebot_api/phase3_profiles.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`

### Task 2: Persistence + Migration
Owner: tooling operative  
Write scope:
- `apps/api/alembic/versions/20260324_0032_thread_agent_profiles.py`
- `apps/api/src/alicebot_api/store.py`

### Task 3: Verification
Owner: tooling operative  
Write scope:
- `tests/integration/test_continuity_api.py`
- `tests/integration/test_responses_api.py`
- `tests/unit/test_20260324_0032_thread_agent_profiles.py`

### Task 4: Integration Review
Owner: control tower  
Responsibilities:
- verify profile identity seam is complete and bounded
- verify no hidden Phase 3 scope expansion
- verify phase2 matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact migration behavior and defaults
- exact API/contract deltas
- exact verification command outcomes
- explicit deferred scope (routing/orchestration/model-provider switching)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained profile-backbone scoped
- thread/profile propagation and validation behavior correctness
- migration safety and user isolation
- no hidden scope expansion

## Exit Condition

This sprint is complete when the repo can persist and expose explicit thread-level agent profile identity with deterministic validation and tests, while keeping all prior Phase 2 gates green.
