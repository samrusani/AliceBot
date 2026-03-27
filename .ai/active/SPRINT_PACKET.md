# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 11: Durable Run Backbone (Task Runs + Worker Tick Skeleton)

## Sprint Type

feature

## Sprint Reason

Phase 4 starts from an accepted Phase 3 Sprint 9 baseline. The major missing capability is durable execution: workers are scaffold-only and there is no persisted run model that can safely advance tasks across interruptions.

## Sprint Intent

Introduce a workflow-style durable run backbone (`task_runs`), deterministic one-step worker ticking, and basic run review visibility, without introducing real external side effects yet.

## Git Instructions

- Branch Name: `codex/phase4-sprint-11-execution-backbone`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the first execution sprint in Phase 4 and the prerequisite for Sprint 12/13 tool and observability work.
- It establishes one execution brain (workflow-style task runs) aligned with existing task/task-step abstractions.
- It creates restart-safe progression foundations while keeping side effects bounded.

## Redundancy Guard

- Already shipped through Phase 3 Sprint 9: continuity, memory/open-loop seams, approvals/budgets, traces, bounded connector ingestion, and profile-isolated routing/runtime controls.
- Missing and required now: durable run records + deterministic worker tick loop behind tasks.
- Explicitly not in this sprint: real external side effects, connector write breadth, broad retry strategy, or multiple orchestration models.

## Design Truth

- Phase 4 execution model is workflow-style durable execution, not graph-runtime-first.
- `task_runs` are the execution object linked to a `task_id`; task steps remain lineage/evidence records.
- Worker ticking is deterministic and bounded to one safe step per tick in Sprint 11.
- Run progression must persist checkpoint state, counters, and explicit stop reason.
- Side effects remain approval-bounded and narrow; Sprint 11 does not introduce real non-echo external actions.

## Exact Surfaces In Scope

- `task_runs` schema + store methods
- task-run lifecycle contracts and bounded API endpoints
- worker run acquisition + single-step tick skeleton
- run checkpoint/counter/stop-reason persistence
- basic task-run review visibility in shell

## Exact Files In Scope

- [20260327_0038_task_runs.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/alembic/versions/20260327_0038_task_runs.py)
- [store.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/store.py)
- [contracts.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/contracts.py)
- [main.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/main.py)
- [tasks.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/tasks.py)
- [task_runs.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/task_runs.py)
- [main.py](/Users/samirusani/Desktop/Codex/AliceBot/workers/alicebot_worker/main.py)
- [task_runs.py](/Users/samirusani/Desktop/Codex/AliceBot/workers/alicebot_worker/task_runs.py)
- [api.ts](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/lib/api.ts)
- [api.test.ts](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/lib/api.test.ts)
- [page.tsx](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/app/tasks/page.tsx)
- [page.test.tsx](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/app/tasks/page.test.tsx)
- [task-run-list.tsx](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/components/task-run-list.tsx)
- [task-run-list.test.tsx](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/components/task-run-list.test.tsx)
- [test_20260327_0038_task_runs.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_20260327_0038_task_runs.py)
- [test_task_run_store.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_task_run_store.py)
- [test_task_runs.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_task_runs.py)
- [test_task_runs_main.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_task_runs_main.py)
- [test_worker_main.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_worker_main.py)
- [test_task_runs_api.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_task_runs_api.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)

## In Scope

- Add `task_runs` persistence model with deterministic statuses, counters, checkpoint, and stop reason.
- Preserve RLS and explicit linkage to existing task/task-step seams.
- Add run lifecycle API seams:
  - create
  - get
  - list by task
  - tick
  - pause
  - resume
  - cancel
- Enforce deterministic lifecycle transitions and fail-clean invalid transitions.
- Add worker skeleton behavior:
  - safe run acquisition
  - one-step tick
  - persisted checkpoint/counter updates
  - safe stop on budget exhaustion or wait states
- Add basic run review UI visibility in `/tasks` with live/fixture/unavailable behavior.
- Provide migration + unit + integration + UI test evidence for the above.

## Out of Scope

- real non-echo external side effects
- Gmail/Calendar write actions
- broad retry policy framework
- Sprint 12 tool-execution expansion work
- Sprint 13 observability/ship-gate expansion work
- multi-brain orchestration model experimentation
- connector/auth/platform/channel expansion
- profile CRUD expansion

## Required Deliverables

- task-runs migration + store wiring
- task-run contracts/endpoints with deterministic transitions
- worker single-step tick skeleton with persisted checkpoint/counters
- task-run review visibility in shell
- test evidence for migration/store/API/worker/UI seams
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- `task_runs` records can be created/read/updated with deterministic status transitions.
- Worker can acquire and tick one run safely, persisting checkpoint and counters.
- Budget exhaustion moves run into a safe non-running state with explicit stop reason.
- Restart-safe continuation from persisted checkpoint state is possible.
- Run state is visible via API and basic `/tasks` review.
- No real external side effects beyond existing `proxy.echo` are introduced.
- `./.venv/bin/python -m pytest tests/unit/test_20260327_0038_task_runs.py tests/unit/test_task_run_store.py tests/unit/test_task_runs.py tests/unit/test_task_runs_main.py tests/unit/test_worker_main.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_task_runs_api.py -q` passes.
- `pnpm --dir apps/web test -- --runInBand app/tasks/page.test.tsx components/task-run-list.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.

## Implementation Constraints

- do not introduce new dependencies
- keep one execution brain (workflow-style task runs)
- preserve append-only evidence surfaces and explicit lineage
- preserve RLS guarantees on new run tables
- keep side-effect surfaces bounded to existing behavior in Sprint 11

## Control Tower Task Cards

### Task 1: `task_runs` Schema + Store
Owner: tooling operative  
Write scope:
- `apps/api/alembic/versions/20260327_0038_task_runs.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/unit/test_20260327_0038_task_runs.py`
- `tests/unit/test_task_run_store.py`

### Task 2: Contracts + API Lifecycle
Owner: tooling operative  
Write scope:
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/tasks.py`
- `apps/api/src/alicebot_api/task_runs.py`
- `tests/unit/test_task_runs.py`
- `tests/unit/test_task_runs_main.py`
- `tests/integration/test_task_runs_api.py`

### Task 3: Worker Tick Skeleton
Owner: tooling operative  
Write scope:
- `workers/alicebot_worker/main.py`
- `workers/alicebot_worker/task_runs.py`
- `tests/unit/test_worker_main.py`

### Task 4: Run Review UI
Owner: tooling operative  
Write scope:
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/tasks/page.test.tsx`
- `apps/web/components/task-run-list.tsx`
- `apps/web/components/task-run-list.test.tsx`

### Task 5: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays Sprint 11 execution-backbone scoped
- verify no real external side effects were introduced
- verify one execution brain model remains intact
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact schema/store/API/worker/UI deltas for task runs
- exact verification command outcomes
- explicit deferred scope (real external tools, connector writes, broad retries, Sprint 12/13 expansion)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to Sprint 11 execution backbone
- task-run lifecycle transitions and worker tick behavior are deterministic
- checkpoint/counter/stop-reason persistence is correct
- UI run visibility works without breaking existing task review surfaces
- no hidden scope expansion

## Exit Condition

This sprint is complete when workflow-style `task_runs` are durable, tickable, checkpointed, budget-aware, and reviewable in API/shell, with all required tests/gates passing and no real external side effects introduced.
