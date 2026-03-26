# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 9: Budget Context Invariance Hardening

## Sprint Type

hardening

## Sprint Reason

Sprint 8 completed profile-scoped execution-budget isolation. The remaining non-redundant correctness gap is context invariance: malformed or unresolvable thread/profile context can degrade budget counting/match isolation behavior.

## Sprint Intent

Make budget decisioning fail-closed and profile-safe when thread context is malformed/unresolvable, and make counted execution history strictly profile-attributable.

## Git Instructions

- Branch Name: `codex/phase3-sprint9-budget-context-invariance`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It directly closes the only explicit residual risk called out in Sprint 8 review.
- It hardens separate-agent isolation semantics under malformed state, not just happy-path contracts.
- It preserves momentum toward MVP/Phase 3 completion without reopening schema breadth.

## Redundancy Guard

- Already shipped in Sprint 1: thread-level profile identity + metadata propagation.
- Already shipped in Sprint 2: web profile selection/visibility.
- Already shipped in Sprint 3: profile-aware response prompting.
- Already shipped in Sprint 4: durable profile registry + thread FK.
- Already shipped in Sprint 5: profile-scoped memory/context isolation.
- Already shipped in Sprint 6: profile-scoped policy evaluation/routing.
- Already shipped in Sprint 7: profile-scoped model/provider routing for `/v0/responses`.
- Already shipped in Sprint 8: profile-scoped execution-budget matching + counted execution isolation for normal context.
- Missing and required now: deterministic fail-closed handling and invariance guarantees for malformed/unresolvable thread context.

## Design Truth

- Budget decisioning must resolve runtime thread/profile context deterministically before counting/match finalization.
- If request thread context is missing/unresolvable at execution time, decisioning is fail-closed with explicit deterministic reasoning (no unscoped fallback counting).
- Historical execution rows with malformed/unresolvable thread context are excluded from profile-scoped counted history.
- Matching precedence remains unchanged for valid context:
  - profile-scoped active budgets first
  - global active budgets second
  - existing selector specificity ordering retained within scope
- Keep scope strictly bounded to invariance hardening; no provider, connector, or orchestration expansion.

## Exact Surfaces In Scope

- execution-budget decisioning invariance for malformed/unresolvable runtime context
- proxy execution fail-closed behavior when decision context is invalid
- additive trace/decision diagnostics for invalid context handling
- unit/integration regression coverage for malformed request and malformed history rows

## Exact Files In Scope

- [contracts.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/contracts.py)
- [execution_budgets.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/execution_budgets.py)
- [proxy_execution.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/proxy_execution.py)
- [test_execution_budgets.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_execution_budgets.py)
- [test_proxy_execution.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_proxy_execution.py)
- [test_proxy_execution_main.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_proxy_execution_main.py)
- [test_proxy_execution_api.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_proxy_execution_api.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)

## In Scope

- Harden budget evaluation context resolution:
  - resolve request thread/profile deterministically before budget counting
  - explicitly handle missing/unresolvable thread context as fail-closed path
- Harden counted execution filtering:
  - exclude historical executions with malformed/unresolvable thread context from scoped counts
  - preserve deterministic ordering/rolling-window behavior for valid rows
- Add additive diagnostics on blocked fail-closed decisions to make reason visible in traces/results.
- Preserve backward compatibility for existing proxy response envelopes and trace event ordering.
- Add unit coverage for:
  - invalid runtime thread context behavior
  - malformed execution-history row behavior
  - deterministic blocked reason contracts
- Add integration coverage proving proxy execution blocks deterministically when context invariants are violated.

## Out of Scope

- schema/migration changes
- execution-budget CRUD redesign
- policy engine redesign
- introducing new providers, connectors, or secret handling changes
- orchestration/worker runtime changes
- web UI changes
- connector/auth expansion

## Required Deliverables

- fail-closed invariance handling for malformed/unresolvable budget runtime context
- deterministic counting behavior under malformed history conditions
- passing unit/integration evidence for invariance hardening behavior
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- Budget decisioning does not execute with unresolvable request thread/profile context.
- Malformed/unresolvable historical execution rows do not contaminate scoped budget counts.
- Proxy execution returns deterministic blocked outcomes for invalid-context invariance failures.
- Existing proxy execution event/result/trace contracts remain backward-compatible (additive diagnostics only).
- `./.venv/bin/python -m pytest tests/unit/test_execution_budgets.py tests/unit/test_proxy_execution.py tests/unit/test_proxy_execution_main.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_proxy_execution_api.py -q` passes.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No provider/connector/orchestration scope expansion enters this sprint.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing response/event/trace payload contracts (additive fields only where necessary)
- keep deterministic ordering contracts (`created_at_asc`, `id_asc`, `specificity_desc`, rolling-window semantics)
- no new DB migration in this sprint unless an explicit Control Tower scope change is issued

## Control Tower Task Cards

### Task 1: Runtime Invariance Hardening
Owner: tooling operative  
Write scope:
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/execution_budgets.py`
- `apps/api/src/alicebot_api/proxy_execution.py`

### Task 2: Verification
Owner: tooling operative  
Write scope:
- `tests/unit/test_execution_budgets.py`
- `tests/unit/test_proxy_execution.py`
- `tests/unit/test_proxy_execution_main.py`
- `tests/integration/test_proxy_execution_api.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays budget-context-invariance scoped
- verify fail-closed behavior for invalid context is deterministic
- verify no provider/connector/orchestration expansion
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact invariance-hardening decisioning deltas
- exact verification command outcomes
- explicit deferred scope (schema expansion, providers/connectors, orchestration, profile CRUD)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to budget context invariance hardening
- malformed-context fail-closed behavior is deterministic and correct
- profile-scoped counting remains isolated under malformed-history pressure
- API and proxy-execution behavior remain backward-compatible
- no hidden scope expansion

## Exit Condition

This sprint is complete when proxy execution budget decisioning is fail-closed under invalid context and profile-scoped counting remains deterministic under malformed-history conditions, with test evidence and validation gates green.
