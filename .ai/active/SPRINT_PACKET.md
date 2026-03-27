# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 12: Real Tool Execution + Approval-Resume Loop

## Sprint Type

feature

## Sprint Reason

Sprint 11 established durable `task_runs`, deterministic run lifecycle APIs, and worker single-step ticking. The next non-redundant gap is practical execution value: moving beyond `proxy.echo` with idempotent run-aware tool execution and safe approval-resume progression.

## Sprint Intent

Introduce one narrow real-tool path beyond `proxy.echo` and integrate approval-required pauses/resumes with task runs, while enforcing idempotency and explicit lineage.

## Git Instructions

- Branch Name: `codex/phase4-sprint-12-real-tools-approval-resume`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the first sprint where Phase 4 execution becomes product-useful, not just infrastructural.
- It validates controlled durable execution against real tool semantics and approval boundaries.
- It keeps rollout narrow so safety, idempotency, and auditability can be verified before broader expansion.

## Redundancy Guard

- Already shipped through Sprint 11: durable run records, deterministic run transitions, worker one-step tick, and run review visibility.
- Missing and required now: idempotent real tool execution and approval-resume wiring linked to task runs.
- Explicitly not in this sprint: broad connector write expansion, major retry framework, or Sprint 13 observability/ship-gate breadth.

## Design Truth

- Phase 4 execution model is workflow-style durable execution, not graph-runtime-first.
- `task_runs` remain the execution object; approvals, task steps, and tool executions must explicitly link back to the run.
- Side-effect-capable tool paths require deterministic idempotency keys and duplicate-side-effect prevention.
- Approval-required run steps must transition to `waiting_approval`, then resume deterministically after approval resolution.
- Tool request/result evidence and run-state transitions must remain append-only and audit-ready.
- Tool rollout stays narrow: one low-risk internal path and one draft-first external path.

## Exact Surfaces In Scope

- run-aware tool execution semantics with idempotency
- approval-required run pause + approval-resolution resume integration
- explicit linkage between run, task step, approval, and tool execution
- narrow real-tool path beyond `proxy.echo`
- shell review updates for approval-wait and resumed-run execution history

## Exact Files In Scope

- [20260327_0039_task_run_execution_linkage.py](apps/api/alembic/versions/20260327_0039_task_run_execution_linkage.py)
- [store.py](apps/api/src/alicebot_api/store.py)
- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [main.py](apps/api/src/alicebot_api/main.py)
- [approvals.py](apps/api/src/alicebot_api/approvals.py)
- [tools.py](apps/api/src/alicebot_api/tools.py)
- [executions.py](apps/api/src/alicebot_api/executions.py)
- [proxy_execution.py](apps/api/src/alicebot_api/proxy_execution.py)
- [tasks.py](apps/api/src/alicebot_api/tasks.py)
- [task_runs.py](apps/api/src/alicebot_api/task_runs.py)
- [main.py](workers/alicebot_worker/main.py)
- [task_runs.py](workers/alicebot_worker/task_runs.py)
- [tool_execution.py](workers/alicebot_worker/tool_execution.py)
- [api.ts](apps/web/lib/api.ts)
- [api.test.ts](apps/web/lib/api.test.ts)
- [page.tsx](apps/web/app/tasks/page.tsx)
- [page.tsx](apps/web/app/approvals/page.tsx)
- [page.test.tsx](apps/web/app/tasks/page.test.tsx)
- [task-run-list.tsx](apps/web/components/task-run-list.tsx)
- [task-run-list.test.tsx](apps/web/components/task-run-list.test.tsx)
- [approval-actions.tsx](apps/web/components/approval-actions.tsx)
- [approval-actions.test.tsx](apps/web/components/approval-actions.test.tsx)
- [approval-detail.tsx](apps/web/components/approval-detail.tsx)
- [approval-detail.test.tsx](apps/web/components/approval-detail.test.tsx)
- [execution-summary.tsx](apps/web/components/execution-summary.tsx)
- [execution-summary.test.tsx](apps/web/components/execution-summary.test.tsx)
- [test_20260327_0039_task_run_execution_linkage.py](tests/unit/test_20260327_0039_task_run_execution_linkage.py)
- [test_proxy_execution.py](tests/unit/test_proxy_execution.py)
- [test_proxy_execution_main.py](tests/unit/test_proxy_execution_main.py)
- [test_executions.py](tests/unit/test_executions.py)
- [test_executions_main.py](tests/unit/test_executions_main.py)
- [test_approvals.py](tests/unit/test_approvals.py)
- [test_approvals_main.py](tests/unit/test_approvals_main.py)
- [test_proxy_execution_api.py](tests/integration/test_proxy_execution_api.py)
- [test_approval_api.py](tests/integration/test_approval_api.py)
- [test_task_runs_api.py](tests/integration/test_task_runs_api.py)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Add run-aware execution linkage persistence (run <-> task step <-> approval <-> tool execution).
- Add idempotency-key semantics for side-effect-capable tool execution paths.
- Enforce retry safety so repeated attempts do not duplicate side effects.
- Integrate approval pauses/resumes:
  - transition run to `waiting_approval` when required
  - resume deterministically after approval resolution
- Implement one narrow real-tool path beyond `proxy.echo`:
  - one low-risk internal tool path
  - one draft-first external path
- Keep immutable request/result evidence and traceability for each execution step.
- Surface pending-approval run state and resumed execution history in shell review.
- Provide unit/integration/UI test evidence for idempotency, pause/resume, and run linkage.

## Out of Scope

- broad connector write expansion
- multiple external write-capable tools
- standing autonomy across high-risk actions
- major retry-policy framework expansion (Sprint 13 scope)
- run-observability/ship-gate breadth (Sprint 13 scope)
- multi-brain orchestration model experimentation
- connector/auth/platform/channel expansion
- profile CRUD expansion

## Required Deliverables

- execution-linkage migration and store wiring for run-aware tool execution
- idempotent real-tool execution contracts and runtime enforcement
- deterministic approval pause/resume integration for runs
- narrow real-tool path beyond `proxy.echo` with traceable request/result evidence
- shell review visibility for waiting/resumed run execution
- test evidence for idempotency, linkage, and approval-resume behavior
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- Tool calls beyond `proxy.echo` execute through governed run-aware runtime.
- Duplicate side effects are prevented on retry for side-effect-capable paths.
- Approval-required run steps transition to `waiting_approval` and resume safely after approval.
- Run/task-step/approval/execution linkage is explicit and reviewable.
- Tool request/result evidence remains immutable and traceable.
- `./.venv/bin/python -m pytest tests/unit/test_20260327_0039_task_run_execution_linkage.py tests/unit/test_proxy_execution.py tests/unit/test_proxy_execution_main.py tests/unit/test_executions.py tests/unit/test_executions_main.py tests/unit/test_approvals.py tests/unit/test_approvals_main.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_proxy_execution_api.py tests/integration/test_approval_api.py tests/integration/test_task_runs_api.py -q` passes.
- `pnpm --dir apps/web test -- --runInBand components/approval-actions.test.tsx components/approval-detail.test.tsx components/execution-summary.test.tsx components/task-run-list.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.

## Implementation Constraints

- do not introduce new dependencies
- keep one execution brain (workflow-style task runs)
- preserve append-only evidence surfaces and explicit lineage
- preserve RLS guarantees on touched run/execution linkage seams
- require explicit idempotency discipline for side-effect-capable tool paths
- keep tool rollout narrow and approval-bounded

## Control Tower Task Cards

### Task 1: Run-Execution Linkage Schema + Store
Owner: tooling operative  
Write scope:
- `apps/api/alembic/versions/20260327_0039_task_run_execution_linkage.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/unit/test_20260327_0039_task_run_execution_linkage.py`

### Task 2: Idempotent Tool Execution Semantics
Owner: tooling operative  
Write scope:
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/tools.py`
- `apps/api/src/alicebot_api/proxy_execution.py`
- `apps/api/src/alicebot_api/executions.py`
- `tests/unit/test_proxy_execution.py`
- `tests/unit/test_proxy_execution_main.py`
- `tests/unit/test_executions.py`
- `tests/unit/test_executions_main.py`
- `tests/integration/test_proxy_execution_api.py`

### Task 3: Approval Pause/Resume Run Integration
Owner: tooling operative  
Write scope:
- `apps/api/src/alicebot_api/approvals.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/task_runs.py`
- `apps/api/src/alicebot_api/tasks.py`
- `tests/unit/test_approvals.py`
- `tests/unit/test_approvals_main.py`
- `tests/integration/test_approval_api.py`
- `tests/integration/test_task_runs_api.py`

### Task 4: Narrow Real-Tool Path + Review UI
Owner: tooling operative  
Write scope:
- `workers/alicebot_worker/main.py`
- `workers/alicebot_worker/task_runs.py`
- `workers/alicebot_worker/tool_execution.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/approvals/page.tsx`
- `apps/web/components/task-run-list.tsx`
- `apps/web/components/task-run-list.test.tsx`
- `apps/web/components/approval-actions.tsx`
- `apps/web/components/approval-actions.test.tsx`
- `apps/web/components/approval-detail.tsx`
- `apps/web/components/approval-detail.test.tsx`
- `apps/web/components/execution-summary.tsx`
- `apps/web/components/execution-summary.test.tsx`

### Task 5: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays Sprint 12 real-tool/approval-resume scoped
- verify side-effect paths are idempotent and approval-bounded
- verify one execution brain model remains intact
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact idempotency/linkage/approval-resume/UI deltas
- exact verification command outcomes
- explicit deferred scope (broad connector writes, broad retries, Sprint 13 observability breadth)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to Sprint 12 scope
- idempotency and duplicate-side-effect prevention are correct
- approval pause/resume linkage to runs and executions is deterministic
- UI shows pending/resumed execution state without regressions
- no hidden scope expansion

## Exit Condition

This sprint is complete when one narrow real-tool path beyond `proxy.echo` executes with idempotent, approval-bounded, run-linked behavior, and all required tests/gates pass without broad scope expansion.
