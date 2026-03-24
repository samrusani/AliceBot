# BUILD_REPORT.md

## Sprint Objective
Implement Phase 3 Sprint 1 (Multi-Agent Profile Backbone) by adding deterministic agent profile identity, persisting thread-level `agent_profile_id`, exposing profile registry read APIs, and propagating active profile metadata through context compile and response generation surfaces without expanding orchestration scope.

## Completed Work
- Added deterministic in-process Phase 3 profile registry:
  - New module: `apps/api/src/alicebot_api/phase3_profiles.py`
  - Profiles shipped:
    - `assistant_default`
    - `coach_default`
  - Deterministic list/read helpers for profile ids and records.

- Added thread profile persistence and binding:
  - New Alembic migration: `apps/api/alembic/versions/20260324_0032_thread_agent_profiles.py`
  - `threads.agent_profile_id` added as `text NOT NULL DEFAULT 'assistant_default'`
  - Added DB constraint for deterministic current profile domain:
    - `threads_agent_profile_id_check` in (`assistant_default`, `coach_default`)
  - Added index:
    - `threads_user_agent_profile_created_idx (user_id, agent_profile_id, created_at DESC, id DESC)`
  - Store layer updated to read/write `agent_profile_id` on thread create/get/list.

- Extended contracts and thread payloads:
  - `ThreadCreateInput` now carries `agent_profile_id` (default `assistant_default`).
  - `ThreadRecord` now includes `agent_profile_id`.
  - Added deterministic contracts for `/v0/agent-profiles` list payload (`items` + `summary`).

- Extended API surfaces in-scope:
  - New endpoint: `GET /v0/agent-profiles` (deterministic registry payload + stable ordering summary).
  - `POST /v0/threads` now accepts optional `agent_profile_id`.
    - Omitted profile id defaults to `assistant_default`.
    - Invalid profile id returns deterministic `422` payload:
      - `code: invalid_agent_profile_id`
      - stable message
      - stable `allowed_agent_profile_ids` list.
  - Thread list/detail/create payloads now expose persisted `agent_profile_id`.
  - `POST /v0/context/compile` now includes metadata:
    - `metadata.agent_profile_id` for the active thread profile.
  - `POST /v0/responses` now includes metadata in both success and model-failure payloads:
    - `metadata.agent_profile_id`.

- Verification tests added/updated in sprint scope:
  - Added migration unit test:
    - `tests/unit/test_20260324_0032_thread_agent_profiles.py`
  - Updated continuity integration coverage for:
    - non-default thread profile create/read/list
    - omitted `agent_profile_id` defaults to `assistant_default`
    - invalid profile 422 behavior
    - deterministic `/v0/agent-profiles` payload
    - compile metadata propagation
  - Updated responses integration coverage for response metadata propagation.

## Incomplete Work
- None in sprint scope.

## Files Changed
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/phase3_profiles.py`
- `apps/api/alembic/versions/20260324_0032_thread_agent_profiles.py`
- `tests/integration/test_continuity_api.py`
- `tests/integration/test_responses_api.py`
- `tests/unit/test_20260324_0032_thread_agent_profiles.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `./.venv/bin/python -m pytest tests/integration/test_continuity_api.py tests/integration/test_responses_api.py -q`
- Initial sandbox run: blocked by local Postgres access policy (`localhost:5432 Operation not permitted`).
- Elevated rerun outcome after adding omitted-profile coverage: PASS (`11 passed in 3.21s`).

2. `./.venv/bin/python -m pytest tests/unit/test_20260324_0032_thread_agent_profiles.py -q`
- Outcome: PASS (`3 passed in 0.13s`).

3. `python3 scripts/run_phase2_validation_matrix.py`
- Initial sandbox run: NO_GO due sandbox DB access restrictions (not logic regressions).
- Elevated rerun outcome: PASS.
- PASS step summary:
  - `control_doc_truth: PASS`
  - `gate_contract_tests: PASS`
  - `readiness_gates: PASS`
  - `backend_integration_matrix: PASS`
  - `web_validation_matrix: PASS`

## Blockers/Issues
- Sandbox network restrictions prevented direct local Postgres access for integration/matrix runs.
- Resolved by rerunning required verification commands with elevated local access.

## Explicit Deferred Scope
- Per-profile model/provider switching
- Runner/worker orchestration changes
- Connector capability expansion
- Auth model changes
- UI profile selector and web routing behavior changes

## Recommended Next Step
1. Proceed to Control Tower integration review focused on profile-boundary correctness and sprint-scope containment, then open PR from `codex/phase3-sprint1-agent-profile-backbone`.
