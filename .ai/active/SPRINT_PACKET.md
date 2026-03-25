# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 6: Profile-Scoped Policy Evaluation and Routing

## Sprint Type

feature

## Sprint Reason

Sprint 5 establishes profile-scoped memory and context isolation. The next non-redundant gap is governance: policy evaluation and routing still operate on user-wide active policy sets without profile boundaries.

## Sprint Intent

Scope policy evaluation to the active thread profile so governed routing decisions are isolated per agent profile while preserving backward-compatible global-policy behavior.

## Git Instructions

- Branch Name: `codex/phase3-sprint6-profile-policy-routing-scope`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the next non-redundant seam after profile identity, prompting, registry, and memory isolation.
- It prevents cross-profile policy bleed in approval/routing decisions.
- It creates a clean foundation for later per-profile provider/tool routing.

## Redundancy Guard

- Already shipped in Sprint 1: thread-level profile identity + metadata propagation.
- Already shipped in Sprint 2: web profile selection/visibility.
- Already shipped in Sprint 3: profile-aware response prompting.
- Already shipped in Sprint 4: durable profile registry + thread FK.
- Already shipped in Sprint 5: profile-scoped memory/context isolation.
- Missing and required now: profile-scoped policy evaluation inputs and deterministic matching.

## Design Truth

- Policies may be either profile-scoped or global.
- Global policy behavior remains backward-compatible via `agent_profile_id = NULL`.
- Policy evaluation for a thread must load only:
  - global active policies
  - active policies matching that thread’s `agent_profile_id`
- Ordering remains deterministic and explicit.

## Exact Surfaces In Scope

- policy schema/profile attribution migration
- store-layer policy create/list/evaluate reads with profile scope
- policy evaluation/routing context filtered by thread profile
- unit/integration tests for scoped matching and backward-compatible global policies

## Exact Files In Scope

- [store.py](apps/api/src/alicebot_api/store.py)
- [main.py](apps/api/src/alicebot_api/main.py)
- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [policy.py](apps/api/src/alicebot_api/policy.py)
- [tools.py](apps/api/src/alicebot_api/tools.py)
- [20260325_0035_policy_agent_profile_scope.py](apps/api/alembic/versions/20260325_0035_policy_agent_profile_scope.py)
- [test_20260325_0035_policy_agent_profile_scope.py](tests/unit/test_20260325_0035_policy_agent_profile_scope.py)
- [test_policy.py](tests/unit/test_policy.py)
- [test_policy_store.py](tests/unit/test_policy_store.py)
- [test_policy_api.py](tests/integration/test_policy_api.py)
- [test_approval_api.py](tests/integration/test_approval_api.py)
- [test_responses_api.py](tests/integration/test_responses_api.py)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Add `agent_profile_id` to `policies`:
  - nullable (NULL means global policy)
  - FK to `agent_profiles(id)` when non-null
  - deterministic evaluation index including priority/order fields
- Update policy create path to accept optional `agent_profile_id`.
- Update policy serialization/read paths to include `agent_profile_id`.
- Update policy evaluation context loading to filter by active thread profile domain:
  - include global policies
  - include policies scoped to thread profile
  - exclude policies scoped to other profiles
- Keep decision/effect semantics unchanged once a policy is selected.
- Add migration tests for FK/nullability/order invariants.
- Add integration tests proving:
  - profile-mismatched policy rows are excluded from evaluation
  - profile-matched and global policies are considered deterministically
  - approval/routing outcomes follow scoped policy sets

## Out of Scope

- profile CRUD endpoints
- per-profile provider/model routing
- tool allowlist profile scoping beyond policy layer
- web UI changes
- connector/auth/orchestration expansion

## Required Deliverables

- policy profile-scope migration and runtime wiring
- scoped policy evaluation evidence for approval/routing flows
- passing unit/integration evidence for profile-scoped governance behavior
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- Policies can be created as global (`agent_profile_id = NULL`) or profile-scoped.
- Policy evaluation for a thread excludes policies bound to other profiles.
- Profile-matched policies and global policies evaluate deterministically with stable order.
- Existing policy effect semantics and response envelopes remain backward-compatible.
- `./.venv/bin/python -m pytest tests/unit/test_20260325_0035_policy_agent_profile_scope.py -q` passes.
- `./.venv/bin/python -m pytest tests/unit/test_policy.py tests/unit/test_policy_store.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_policy_api.py tests/integration/test_approval_api.py -q` passes.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No provider/tool-orchestration scope expansion enters this sprint.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing policy/approval API payload contracts (additive fields only)
- keep migration reversible and forward-safe
- keep policy ordering deterministic with current priority/order rules

## Control Tower Task Cards

### Task 1: Policy Scope Migration + Store Wiring
Owner: tooling operative  
Write scope:
- `apps/api/alembic/versions/20260325_0035_policy_agent_profile_scope.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/policy.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/tools.py`

### Task 2: Verification
Owner: tooling operative  
Write scope:
- `tests/unit/test_20260325_0035_policy_agent_profile_scope.py`
- `tests/unit/test_policy.py`
- `tests/unit/test_policy_store.py`
- `tests/integration/test_policy_api.py`
- `tests/integration/test_approval_api.py`
- `tests/integration/test_responses_api.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays policy-scope evaluation scoped
- verify no provider/tool-orchestration expansion
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact policy-profile-scope migration and evaluation deltas
- exact verification command outcomes
- explicit deferred scope (provider/tool routing/orchestration/profile CRUD)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to policy evaluation profile isolation
- policy scope filtering and deterministic ordering are correct
- API behavior remains backward-compatible
- no hidden scope expansion

## Exit Condition

This sprint is complete when policy evaluation and routing decisions are profile-scoped and deterministic for the active thread profile, with migration/test evidence and all validation gates green.
