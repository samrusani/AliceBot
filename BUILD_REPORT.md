# BUILD_REPORT.md

## Sprint Objective
Phase 3 Sprint 7: Profile-Scoped Model Routing.

Route `/v0/responses` model selection by active thread profile runtime config (`model_provider`, `model_name`) with deterministic fallback to global `Settings.model_provider` / `Settings.model_name` when profile runtime config is absent.

## Completed Work
- Added migration `20260325_0036_agent_profile_model_runtime`:
- added nullable `agent_profiles.model_provider` and `agent_profiles.model_name`.
- added bounded-provider/runtime-pairing constraints:
- `agent_profiles_model_provider_check`
- `agent_profiles_model_runtime_pairing_check`
- seeded deterministic runtime config for shipped profiles:
- `assistant_default` -> `openai_responses` / `gpt-5-mini`
- `coach_default` -> `openai_responses` / `gpt-5`
- Updated profile registry/store contract wiring:
- `AgentProfileRow` now includes `model_provider`, `model_name`.
- agent profile list/get SQL now selects runtime config columns.
- `AgentProfileRecord` now includes additive runtime config fields.
- profile registry serialization now exposes runtime fields in `/v0/agent-profiles` responses.
- Implemented response model routing:
- added `resolve_thread_model_runtime(...)` in `response_generation.py`.
- `/v0/responses` now resolves active thread profile, uses profile runtime model/provider when both are present.
- deterministic fallback to global settings when profile runtime is missing/incomplete or profile lookup is absent.
- preserved existing response envelope/trace structure and failure semantics.
- Added/updated sprint verification tests:
- new migration unit test `test_20260325_0036_agent_profile_model_runtime.py`.
- added runtime routing/fallback unit tests in `test_response_generation.py`.
- updated continuity integration expectations for additive agent profile runtime fields.
- updated responses integration to verify profile-specific model routing and deterministic fallback behavior.

## Incomplete Work
- None within sprint scope.

## Files Changed
- `apps/api/alembic/versions/20260325_0036_agent_profile_model_runtime.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/phase3_profiles.py`
- `apps/api/src/alicebot_api/response_generation.py`
- `tests/unit/test_20260325_0036_agent_profile_model_runtime.py`
- `tests/unit/test_response_generation.py`
- `tests/integration/test_continuity_api.py`
- `tests/integration/test_responses_api.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `./.venv/bin/python -m pytest tests/unit/test_20260325_0036_agent_profile_model_runtime.py -q`
- PASS (`4 passed in 0.22s`)

2. `./.venv/bin/python -m pytest tests/unit/test_response_generation.py -q`
- PASS (`6 passed in 0.24s`)

3. `./.venv/bin/python -m pytest tests/integration/test_continuity_api.py tests/integration/test_responses_api.py -q`
- PASS (`13 passed in 4.64s`)

4. `python3 scripts/run_phase2_validation_matrix.py`
- PASS
- `control_doc_truth: PASS`
- `gate_contract_tests: PASS`
- `readiness_gates: PASS`
- `backend_integration_matrix: PASS`
- `web_validation_matrix: PASS`

## Blockers/Issues
- Sandbox denied localhost PostgreSQL access for DB-backed integration and matrix commands.
- Resolved by rerunning required DB-backed commands with elevated permissions.

## Explicit Deferred Scope
- No profile CRUD endpoint work.
- No new provider integrations or credential/orchestration expansion.
- No policy/tooling redesign beyond routing to existing provider surface.
- No web UI changes.

## Recommended Next Step
1. Control Tower review focused on deterministic profile runtime routing/fallback behavior and merge readiness.
