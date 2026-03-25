# BUILD_REPORT.md

## Sprint Objective
Implement Phase 3 Sprint 8 execution-budget profile scope isolation by adding optional `agent_profile_id` scope to budgets, updating create/list/get contracts, and enforcing profile-aware budget matching/counting with deterministic global fallback.

## Completed Work
- Added migration `20260325_0037_execution_budget_agent_profile_scope`:
  - Added nullable `execution_budgets.agent_profile_id`.
  - Added FK `execution_budgets_agent_profile_id_fkey -> agent_profiles(id)`.
  - Replaced selector/match indexing with profile-aware index `execution_budgets_user_profile_match_idx`.
  - Replaced active uniqueness index to include profile scope via `COALESCE(agent_profile_id, '')` while preserving existing index name `execution_budgets_one_active_scope_idx`.
  - Added reversible downgrade restoring pre-sprint index/column shape.
- Wired store schema/query surface:
  - `ExecutionBudgetRow` now includes `agent_profile_id`.
  - Execution-budget INSERT/GET/LIST/DEACTIVATE/SUPERSEDE SQL now reads/writes `agent_profile_id`.
  - `ContinuityStore.create_execution_budget(...)` now accepts `agent_profile_id`.
- Updated API/contracts:
  - `ExecutionBudgetCreateInput` now accepts/serializes `agent_profile_id`.
  - `ExecutionBudgetRecord` now includes additive `agent_profile_id`.
  - `/v0/execution-budgets` request model now accepts optional `agent_profile_id`.
- Added create-time validation:
  - Budget create validates provided `agent_profile_id` exists in profile registry (`store.get_agent_profile_optional`).
- Implemented profile-aware budget evaluation behavior:
  - Resolves active thread profile from `request.thread_id`.
  - Matching precedence: profile-scoped active budgets first, then global (`agent_profile_id IS NULL`).
  - Preserved selector ordering within each scope: `specificity_desc`, `created_at_asc`, `id_asc`.
  - Completed-execution counting isolated to active thread profile scope (including global-fallback decisions) while preserving rolling-window behavior and history order.
- Updated lifecycle/supersede scope handling:
  - Supersede active-scope checks and duplicate scope messages now include profile scope.
  - Replacement budget preserves source `agent_profile_id`.
- Added/updated sprint-scoped tests:
  - New migration test file for `0037` upgrade/downgrade/index/FK contracts.
  - Updated unit store/main/execution-budget tests for additive `agent_profile_id` contract and profile-aware behavior.
  - Updated integration execution-budget API tests for profile scope uniqueness/validation.
  - Added integration proxy execution test for profile-first matching and global fallback isolation.

## Incomplete Work
- None within sprint scope.

## Files Changed
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/execution_budgets.py`
- `apps/api/alembic/versions/20260325_0037_execution_budget_agent_profile_scope.py`
- `tests/unit/test_20260325_0037_execution_budget_agent_profile_scope.py`
- `tests/unit/test_execution_budgets.py`
- `tests/unit/test_execution_budgets_main.py`
- `tests/unit/test_execution_budget_store.py`
- `tests/integration/test_execution_budgets_api.py`
- `tests/integration/test_proxy_execution_api.py`
- `BUILD_REPORT.md`

## Tests Run
- `./.venv/bin/python -m pytest tests/unit/test_20260325_0037_execution_budget_agent_profile_scope.py -q`
  - PASS (`4 passed`)
- `./.venv/bin/python -m pytest tests/unit/test_execution_budgets.py tests/unit/test_execution_budgets_main.py tests/unit/test_execution_budget_store.py -q`
  - PASS (`26 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_execution_budgets_api.py tests/integration/test_proxy_execution_api.py -q`
  - PASS (`24 passed`)
- `python3 scripts/run_phase2_validation_matrix.py`
  - PASS (`Phase 2 validation matrix result: PASS`)
  - Note: one intermediate run had a transient web-test failure; immediate rerun passed with no code changes.

## Blockers / Issues
- No implementation blockers.
- Environment note: integration and validation commands required local DB access outside sandbox constraints; commands were rerun with escalated permissions to complete verification.

## Deferred Scope (Explicit)
- No provider/connector surface expansion.
- No orchestration/worker runtime redesign.
- No profile CRUD endpoint expansion.

## Recommended Next Step
Open integration review (Control Tower Task 3) focused on deterministic profile-scope matching/counting and contract backward compatibility.
