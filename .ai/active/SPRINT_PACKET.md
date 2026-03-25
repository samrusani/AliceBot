# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 8: Profile-Scoped Execution Budget Isolation

## Sprint Type

feature

## Sprint Reason

Sprint 7 completed profile-scoped response model routing. The next non-redundant gap is governed execution budget isolation: execution budgets are still user-global, so one profile can exhaust limits that should be isolated to another profile.

## Sprint Intent

Scope execution-budget matching and counting to the active thread profile, with deterministic fallback to global budgets when no profile-specific budget matches.

## Git Instructions

- Branch Name: `codex/phase3-sprint8-profile-budget-scope`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the next non-redundant seam after identity, memory isolation, policy isolation, and model isolation.
- It closes a remaining shared-governance gap where execution budgets can still cross-contaminate profiles.
- It advances separate-agent runtime behavior without widening orchestration or connector scope.

## Redundancy Guard

- Already shipped in Sprint 1: thread-level profile identity + metadata propagation.
- Already shipped in Sprint 2: web profile selection/visibility.
- Already shipped in Sprint 3: profile-aware response prompting.
- Already shipped in Sprint 4: durable profile registry + thread FK.
- Already shipped in Sprint 5: profile-scoped memory/context isolation.
- Already shipped in Sprint 6: profile-scoped policy evaluation/routing.
- Already shipped in Sprint 7: profile-scoped model/provider routing for `/v0/responses`.
- Missing and required now: profile-scoped execution budget matching + counted execution history isolation.

## Design Truth

- Execution budgets can optionally target one `agent_profile_id` while preserving global budget support via nullable scope.
- Budget match precedence remains deterministic:
  - first match active budgets scoped to the thread profile
  - then match active global budgets (`agent_profile_id IS NULL`)
  - within each scope, preserve existing selector specificity and stable ordering
- Completed-execution counting for budget decisions must only include executions attributable to the same profile scope as the matched budget.
- Keep tool/provider/orchestration surface bounded; this sprint is budget-scope isolation only.

## Exact Surfaces In Scope

- execution-budget schema/profile scope wiring
- execution-budget API contracts and lifecycle responses with additive profile scope field
- budget evaluation matching + counting with thread-profile-aware isolation and global fallback
- unit/integration tests proving profile isolation and deterministic fallback behavior

## Exact Files In Scope

- [store.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/store.py)
- [main.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/main.py)
- [contracts.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/contracts.py)
- [execution_budgets.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/execution_budgets.py)
- [proxy_execution.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/proxy_execution.py)
- [20260325_0037_execution_budget_agent_profile_scope.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/alembic/versions/20260325_0037_execution_budget_agent_profile_scope.py)
- [test_20260325_0037_execution_budget_agent_profile_scope.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_20260325_0037_execution_budget_agent_profile_scope.py)
- [test_execution_budgets.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_execution_budgets.py)
- [test_execution_budgets_main.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_execution_budgets_main.py)
- [test_execution_budget_store.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_execution_budget_store.py)
- [test_execution_budgets_api.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_execution_budgets_api.py)
- [test_proxy_execution_api.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_proxy_execution_api.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)

## In Scope

- Add nullable `agent_profile_id` to `execution_budgets` with FK to `agent_profiles`.
- Update active-scope uniqueness/index strategy to include profile scope:
  - one active budget per `(user_id, agent_profile_id, tool_key, domain_hint)` selector scope
  - preserve deterministic ordering/index contracts
- Update execution-budget create/list/get/lifecycle contracts to expose additive `agent_profile_id`.
- Validate `agent_profile_id` on create when provided (must exist in registry).
- Update budget evaluation to:
  - resolve active thread profile from request thread
  - match profile-scoped budgets first, then global budgets
  - keep existing selector specificity ordering within each scope
  - count only completed executions attributable to the matched profile scope
- Preserve existing proxy execution event and trace contract shapes (additive fields only where necessary).
- Add migration tests for schema/index invariants and rollback.
- Add unit/integration coverage for profile-scoped budget matching, fallback, and blocked/allow decisions.

## Out of Scope

- profile CRUD endpoints
- policy engine redesign beyond budget profile scope filtering
- introducing new providers, connectors, or secret handling changes
- orchestration/worker runtime changes
- web UI changes
- connector/auth expansion

## Required Deliverables

- execution-budget profile-scope migration and store wiring
- budget create/list/get serialization with additive profile scope fields
- profile-aware budget evaluation and deterministic global fallback
- passing unit/integration evidence for profile-scoped budget decisions
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- `execution_budgets` persist optional `agent_profile_id` with FK integrity.
- Budget create/list/get payloads include additive `agent_profile_id` and remain backward-compatible.
- Budget evaluation for proxy execution is profile-isolated:
  - profile-scoped budgets apply to matching thread profiles
  - profile-scoped budgets do not throttle non-matching profiles
  - deterministic fallback to global budgets works when no profile-scoped match exists
- Existing proxy execution result/event/trace contracts remain backward-compatible.
- `./.venv/bin/python -m pytest tests/unit/test_20260325_0037_execution_budget_agent_profile_scope.py -q` passes.
- `./.venv/bin/python -m pytest tests/unit/test_execution_budgets.py tests/unit/test_execution_budgets_main.py tests/unit/test_execution_budget_store.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_execution_budgets_api.py tests/integration/test_proxy_execution_api.py -q` passes.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No provider/connector/orchestration scope expansion enters this sprint.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing response/event/trace payload contracts (additive fields only where necessary)
- keep migration reversible and forward-safe
- keep deterministic ordering contracts (`created_at_asc`, `id_asc`, `specificity_desc`)

## Control Tower Task Cards

### Task 1: Budget Profile-Scope Migration + Store Wiring
Owner: tooling operative  
Write scope:
- `apps/api/alembic/versions/20260325_0037_execution_budget_agent_profile_scope.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/execution_budgets.py`
- `apps/api/src/alicebot_api/proxy_execution.py`

### Task 2: Verification
Owner: tooling operative  
Write scope:
- `tests/unit/test_20260325_0037_execution_budget_agent_profile_scope.py`
- `tests/unit/test_execution_budgets.py`
- `tests/unit/test_execution_budgets_main.py`
- `tests/unit/test_execution_budget_store.py`
- `tests/integration/test_execution_budgets_api.py`
- `tests/integration/test_proxy_execution_api.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays execution-budget-profile-scope scoped
- verify profile isolation and global fallback are deterministic
- verify no provider/connector/orchestration expansion
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact execution-budget profile-scope migration and routing/evaluation deltas
- exact verification command outcomes
- explicit deferred scope (providers/connectors, orchestration, profile CRUD)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to execution-budget profile scope
- profile-scoped budget matching/counting and global fallback are deterministic and correct
- API and proxy-execution behavior remain backward-compatible
- no hidden scope expansion

## Exit Condition

This sprint is complete when execution-budget decisions are profile-scoped and deterministic for the active thread profile, with migration/test evidence and all validation gates green.
