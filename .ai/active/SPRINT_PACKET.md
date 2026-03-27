# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 13: Run Observability, Failure Discipline, and Ship Gates

## Sprint Type

feature

## Sprint Reason

Sprint 12 delivered run-aware tool execution, idempotency, and approval-resume linkage. The next non-redundant gap is release confidence: explicit run transition evidence, bounded retry/failure behavior, and deterministic Phase 4 gate commands.

## Sprint Intent

Make durable execution auditable and ship-ready by exposing complete run lifecycle evidence, enforcing explicit retry/failure semantics, and codifying Phase 4 go/no-go scripts and runbooks.

## Git Instructions

- Branch Name: `codex/phase4-sprint-13-run-observability-ship-gates`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It closes the last release-readiness gap between "execution works" and "execution is measurable and explainable."
- It creates deterministic ship-gate evidence instead of ad-hoc manual checks.
- It keeps scope narrow and avoids repeating Sprint 12 implementation seams.

## Redundancy Guard

- Already shipped in Sprint 12:
  - run-aware execution linkage
  - idempotent tool execution replay safety
  - approval pause/resume lifecycle linkage
- Required now (Sprint 13):
  - run transition and stop-reason observability
  - bounded retries and explicit failure categorization
  - deterministic Phase 4 acceptance/readiness/validation gates
- Explicitly out of Sprint 13:
  - new connector breadth
  - auth model expansion
  - multi-orchestrator runtime experiments

## Design Truth

- Phase 4 execution remains workflow-style durable runs, not graph-runtime-first.
- Runs must emit ordered transitions with explicit stop reasons:
  - `queued`
  - `running`
  - `waiting_approval`
  - `waiting_user`
  - `paused`
  - `failed`
  - `done`
  - `cancelled`
- Retry behavior must be capped, persisted, and reviewable.
- Failure classes must be explicit and stable:
  - `transient`
  - `policy`
  - `approval`
  - `budget`
  - `fatal`

## Exact Surfaces In Scope

- run transition and stop-reason traceability
- retry caps and retry posture persistence
- failure class persistence and API exposure
- run diagnostics visibility in API and web shell
- deterministic Phase 4 gate runner scripts and runbooks
- canonical control-doc synchronization to current sprint truth

## Exact Files In Scope

- `apps/api/alembic/versions/20260327_0040_task_run_retry_failure_controls.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/approvals.py`
- `apps/api/src/alicebot_api/executions.py`
- `apps/api/src/alicebot_api/proxy_execution.py`
- `apps/api/src/alicebot_api/tasks.py`
- `apps/api/src/alicebot_api/task_runs.py`
- `apps/api/src/alicebot_api/traces.py`
- `workers/alicebot_worker/main.py`
- `workers/alicebot_worker/task_runs.py`
- `workers/alicebot_worker/tool_execution.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/tasks/page.test.tsx`
- `apps/web/app/traces/page.tsx`
- `apps/web/app/traces/page.test.tsx`
- `apps/web/components/task-run-list.tsx`
- `apps/web/components/task-run-list.test.tsx`
- `apps/web/components/execution-summary.tsx`
- `apps/web/components/execution-summary.test.tsx`
- `tests/unit/test_20260327_0040_task_run_retry_failure_controls.py`
- `tests/unit/test_task_runs.py`
- `tests/unit/test_task_runs_main.py`
- `tests/unit/test_proxy_execution.py`
- `tests/unit/test_proxy_execution_main.py`
- `tests/unit/test_executions.py`
- `tests/unit/test_executions_main.py`
- `tests/unit/test_approvals.py`
- `tests/unit/test_approvals_main.py`
- `tests/unit/test_worker_main.py`
- `tests/integration/test_proxy_execution_api.py`
- `tests/integration/test_approval_api.py`
- `tests/integration/test_task_runs_api.py`
- `scripts/run_phase4_acceptance.py`
- `scripts/run_phase4_readiness_gates.py`
- `scripts/run_phase4_validation_matrix.py`
- `docs/runbooks/phase4-acceptance-suite.md`
- `docs/runbooks/phase4-readiness-gates.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `docs/runbooks/phase4-closeout-packet.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add run transition evidence with explicit transition and stop-reason payloads.
- Persist retry count, retry cap, and next-step posture on runs.
- Persist and expose failure classes (`transient`, `policy`, `approval`, `budget`, `fatal`).
- Ensure blocked/paused/waiting runs remain inspectable and never collapse into silent success.
- Add diagnostics visibility in shell for stop reason and retry posture.
- Add deterministic Phase 4 gate scenarios:
  - `run_progression_with_pause`
  - `restart_safe_resume`
  - `budget_exhaustion_fail_closed`
  - `draft_first_tool_execution`
  - `approval_resume_execution`
- Add Phase 4 gate entrypoint scripts and runbooks.
- Refresh canonical truth docs (`README.md`, `ROADMAP.md`, `.ai/handoff/CURRENT_STATE.md`) to reflect post-Sprint-12 baseline and Sprint-13 plan.

## Out of Scope

- broad connector write expansion
- major new tool-surface expansion beyond Sprint 12 narrow paths
- new external channels/platform distribution
- auth-model redesign
- orchestration model experimentation
- profile CRUD expansion

## Required Deliverables

- retry/failure migration and runtime wiring
- run observability and diagnostics in API and web shell
- bounded retry/failure semantics with explicit categories
- Phase 4 acceptance/readiness/validation scripts and runbooks
- deterministic scenario evidence for Phase 4 ship gates
- refreshed canonical docs aligned to new baseline
- sprint build/review reports scoped to Sprint 13 only

## Acceptance Criteria

- Run transition and stop-reason evidence is deterministic and visible for all non-happy-path and terminal run states.
- Retry caps are enforced and persisted state is reviewable.
- Failure classes are explicit and stable in API/trace/review surfaces.
- Phase 4 scenario commands report deterministic PASS/FAIL outcomes.
- `./.venv/bin/python -m pytest tests/unit/test_20260327_0040_task_run_retry_failure_controls.py tests/unit/test_task_runs.py tests/unit/test_task_runs_main.py tests/unit/test_proxy_execution.py tests/unit/test_proxy_execution_main.py tests/unit/test_worker_main.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_task_runs_api.py tests/integration/test_proxy_execution_api.py tests/integration/test_approval_api.py -q` passes.
- `pnpm --dir apps/web test -- --runInBand app/tasks/page.test.tsx app/traces/page.test.tsx components/task-run-list.test.tsx components/execution-summary.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` passes.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` explicitly reflect Phase 4 Sprint 12 delivered state plus Sprint 13 active gate focus.

## Implementation Constraints

- do not introduce new dependencies
- keep one execution brain (workflow-style task runs)
- preserve append-only evidence and explicit lineage
- preserve RLS guarantees on touched run/execution/trace seams
- keep failure/retry semantics deterministic and explicit
- keep Sprint 12 narrow tool rollout unchanged

## Control Tower Task Cards

### Task 1: Retry/Failure Schema + Store

Owner: tooling operative

Write scope:

- `apps/api/alembic/versions/20260327_0040_task_run_retry_failure_controls.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/task_runs.py`
- `tests/unit/test_20260327_0040_task_run_retry_failure_controls.py`
- `tests/unit/test_task_runs.py`

### Task 2: Run Observability + Failure Classification

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/traces.py`
- `apps/api/src/alicebot_api/proxy_execution.py`
- `apps/api/src/alicebot_api/executions.py`
- `tests/unit/test_executions.py`
- `tests/unit/test_executions_main.py`
- `tests/unit/test_proxy_execution.py`
- `tests/unit/test_proxy_execution_main.py`
- `tests/integration/test_proxy_execution_api.py`

### Task 3: Worker Retry/Failure Discipline

Owner: tooling operative

Write scope:

- `workers/alicebot_worker/main.py`
- `workers/alicebot_worker/task_runs.py`
- `workers/alicebot_worker/tool_execution.py`
- `tests/unit/test_worker_main.py`

### Task 4: Diagnostics UI + Gate Runners

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/approvals.py`
- `tests/unit/test_approvals.py`
- `tests/unit/test_approvals_main.py`
- `tests/integration/test_approval_api.py`
- `tests/integration/test_task_runs_api.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/tasks/page.test.tsx`
- `apps/web/app/traces/page.tsx`
- `apps/web/app/traces/page.test.tsx`
- `apps/web/components/task-run-list.tsx`
- `apps/web/components/task-run-list.test.tsx`
- `apps/web/components/execution-summary.tsx`
- `apps/web/components/execution-summary.test.tsx`
- `scripts/run_phase4_acceptance.py`
- `scripts/run_phase4_readiness_gates.py`
- `scripts/run_phase4_validation_matrix.py`
- `docs/runbooks/phase4-acceptance-suite.md`
- `docs/runbooks/phase4-readiness-gates.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `docs/runbooks/phase4-closeout-packet.md`

### Task 5: Canonical Truth Sync + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify sprint stays Sprint 13 observability/failure/ship-gate scoped
- verify no duplicate implementation of Sprint 12 seams
- verify retry/failure behavior is deterministic and bounded
- verify Phase 4 gate scenarios are executable and coherent
- verify one-execution-brain model remains intact
- verify documentation truth is synchronized with delivered baseline

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact observability/retry/failure/gate-chain deltas
- exact verification command outcomes
- explicit deferred scope (connector/auth/platform expansion)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed bounded to Sprint 13 scope
- run transitions, stop reasons, retry posture, and failure classes are deterministic and reviewable
- Phase 4 gate scenarios and validation chain are measurable and coherent
- shell diagnostics expose stop reason and retry posture without regressions
- canonical docs align with delivered repo reality
- no hidden scope expansion

## Exit Condition

This sprint is complete when durable runs expose complete transition/stop/failure evidence, retries are bounded and explicit, Phase 4 gate commands pass deterministically, and canonical docs reflect the delivered baseline without drift.
