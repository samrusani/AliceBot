# BUILD_REPORT.md

## Sprint Objective
Phase 3 Sprint 6: Profile-Scoped Policy Evaluation and Routing.

Implement policy profile attribution and scope policy evaluation/routing to the active thread profile domain (global `NULL` + thread-matching profile), while preserving backward-compatible global policy behavior.

## Completed Work
- Added migration `20260325_0035_policy_agent_profile_scope`:
- Added nullable `policies.agent_profile_id`.
- Added FK `policies_agent_profile_id_fkey` -> `agent_profiles(id)`.
- Replaced active-policy index with profile-aware deterministic index:
- dropped `policies_user_active_priority_created_idx`
- added `policies_user_active_profile_priority_created_idx` on `(user_id, active, agent_profile_id, priority, created_at, id)`.
- Updated store policy schema/read/write wiring:
- `PolicyRow` now includes `agent_profile_id`.
- policy insert/select/list SQL now includes `agent_profile_id`.
- `create_policy(..., agent_profile_id=None)` supports global and profile-scoped policy rows.
- `list_active_policies(agent_profile_id=...)` loads only global + matching-profile active policies when profile is provided.
- Updated contracts and API model wiring:
- `PolicyCreateInput` accepts optional `agent_profile_id`.
- `PolicyRecord` includes `agent_profile_id`.
- `/v0/policies` request now accepts optional `agent_profile_id`.
- `/v0/policies` validates non-null `agent_profile_id` against registered profiles and returns deterministic 422 on invalid IDs.
- Updated policy runtime behavior:
- policy serialization includes `agent_profile_id`.
- policy evaluation context loading is thread-profile-scoped.
- `evaluate_policy_request` now evaluates only global + thread-profile-matched active policies.
- Updated routing/approval policy context behavior:
- tool allowlist and tool routing now load policy context using thread `agent_profile_id`.
- approval routing outcomes now honor scoped policy sets (mismatched profile policies excluded).
- Added/updated verification coverage:
- new migration unit test for 0035 statement order and invariants.
- updated policy store unit tests for `agent_profile_id` SQL parameterization and scoped active-policy query.
- updated policy unit tests for scoped evaluation behavior.
- updated integration policy tests for scoped/global deterministic evaluation and additive API contract field.
- added integration approval test proving profile-mismatched policy exclusion in routing.

## Incomplete Work
- None within sprint scope.

## Files Changed
- `apps/api/alembic/versions/20260325_0035_policy_agent_profile_scope.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/policy.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/tools.py`
- `tests/unit/test_20260325_0035_policy_agent_profile_scope.py`
- `tests/unit/test_policy.py`
- `tests/unit/test_policy_store.py`
- `tests/integration/test_policy_api.py`
- `tests/integration/test_approval_api.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `./.venv/bin/python -m pytest tests/unit/test_20260325_0035_policy_agent_profile_scope.py -q`
- PASS (`4 passed`)

2. `./.venv/bin/python -m pytest tests/unit/test_policy.py tests/unit/test_policy_store.py -q`
- PASS (`11 passed`)

3. `./.venv/bin/python -m pytest tests/integration/test_policy_api.py tests/integration/test_approval_api.py -q`
- PASS (`14 passed`)

4. `python3 scripts/run_phase2_validation_matrix.py`
- PASS
- `control_doc_truth: PASS`
- `gate_contract_tests: PASS`
- `readiness_gates: PASS`
- `backend_integration_matrix: PASS`
- `web_validation_matrix: PASS`

5. `./.venv/bin/python -m pytest tests/unit/test_tools.py tests/unit/test_approvals.py -q`
- PASS (`17 passed`)

## Blockers/Issues
- Sandbox networking blocked localhost PostgreSQL access for DB-backed integration/matrix commands.
- Resolved by rerunning required commands with elevated permissions.
- Scope-adjacent unit regressions in `tests/unit/test_tools.py` and `tests/unit/test_approvals.py` were detected and fixed (legacy stub compatibility for missing `agent_profile_id`/older `list_active_policies` signatures).

## Explicit Deferred Scope
- No profile CRUD expansion.
- No per-profile provider/model routing expansion.
- No tool orchestration expansion beyond policy-layer scope filtering.
- No connector/auth/orchestration expansion.

## Recommended Next Step
1. Control Tower review focused on profile-scope filtering correctness, deterministic ordering invariants, and merge readiness.
