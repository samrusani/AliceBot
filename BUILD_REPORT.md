# BUILD_REPORT.md

## Sprint Objective
Implement Phase 4 Sprint 12: add run-aware real tool execution beyond `proxy.echo`, enforce idempotent side-effect execution, and wire approval pause/resume transitions to durable `task_runs` with explicit run/task-step/approval/execution linkage.

## Completed Work
- Added migration `20260327_0039_task_run_execution_linkage.py` to link `task_runs` with approvals/tool executions and persist idempotency keys.
  - Added `approvals.task_run_id` FK.
  - Added `tool_executions.task_run_id` and `tool_executions.idempotency_key`.
  - Added partial unique index for idempotent replay safety: `(user_id, task_run_id, approval_id, idempotency_key)`.
  - Extended task-run status/stop-reason constraints to include `waiting_approval`.
- Extended store contracts and SQL in `store.py` for run-aware approval/execution persistence and idempotency lookup.
  - Added approval/task-run linkage updates.
  - Added tool execution idempotency lookup seam.
  - Added optional `task_run_id` and `idempotency_key` persistence fields.
  - Fixed `INSERT_TOOL_SQL` placeholder regression encountered during integration verification.
- Implemented idempotent execution semantics and narrow real-tool rollout in `proxy_execution.py`.
  - Added two new handlers: `proxy.thread_audit` (internal low-risk) and `proxy.calendar.draft_event` (draft-first external).
  - Added side-effect idempotency key derivation and replay path before dispatch.
  - Added run-linkage resolution and execution->run checkpoint sync.
  - Preserved existing trace limits envelope compatibility for established API expectations.
- Added approval-run integration in `approvals.py` and `task_runs.py`.
  - Run transitions to `waiting_approval` on governed pending-approval steps.
  - Approval resolution deterministically resumes linked runs (`approved -> queued`, `rejected -> completed`) with checkpoint evidence.
- Updated API surface (`contracts.py`, `main.py`, `executions.py`) for optional task-run linkage/idempotency fields and endpoint propagation.
- Added worker seam for run-aware execution dispatch.
  - New `workers/alicebot_worker/tool_execution.py`.
  - `workers/alicebot_worker/task_runs.py` now attempts execution when task/run state is ready.
- Updated web shell review wiring for run linkage and resumed execution visibility.
  - `apps/web/lib/api.ts`, `apps/web/components/approval-actions.tsx`, `apps/web/components/approval-detail.tsx`, `apps/web/components/execution-summary.tsx`, `apps/web/components/task-run-list.tsx`, `apps/web/app/tasks/page.tsx`.
  - Kept backward-compatible request behavior by omitting `task_run_id` when absent.
- Added minimal web test-command compatibility shim so the exact sprint packet command with `--runInBand` executes under vitest.
  - Updated `apps/web/package.json` test script to call `node test/run-vitest.mjs`.
  - Added `apps/web/test/run-vitest.mjs` to strip `--runInBand` and forward remaining args to `vitest run`.
- Added migration unit coverage in `tests/unit/test_20260327_0039_task_run_execution_linkage.py`.
- Applied post-review safety fixes:
  - approval resolution now resumes linked runs only from `waiting_approval` (terminal runs are not reopened).
  - run sync after execution no longer forces blocked outcomes to `completed`; blocked outcomes pause the run with explicit stop reason mapping.

## Incomplete Work
- None inside Sprint 12 scope.

## Files Changed
- `apps/api/alembic/versions/20260327_0039_task_run_execution_linkage.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/approvals.py`
- `apps/api/src/alicebot_api/executions.py`
- `apps/api/src/alicebot_api/proxy_execution.py`
- `apps/api/src/alicebot_api/task_runs.py`
- `workers/alicebot_worker/task_runs.py`
- `workers/alicebot_worker/tool_execution.py`
- `apps/web/lib/api.ts`
- `apps/web/package.json`
- `apps/web/test/run-vitest.mjs`
- `apps/web/app/tasks/page.tsx`
- `apps/web/components/approval-actions.tsx`
- `apps/web/components/approval-detail.tsx`
- `apps/web/components/execution-summary.tsx`
- `apps/web/components/task-run-list.tsx`
- `tests/unit/test_20260327_0039_task_run_execution_linkage.py`
- `tests/unit/test_proxy_execution.py`
- `tests/unit/test_approvals.py`
- `tests/integration/test_approval_api.py`
- `tests/integration/test_proxy_execution_api.py`
- `BUILD_REPORT.md`

## Tests Run
- `./.venv/bin/python -m pytest tests/unit/test_20260327_0039_task_run_execution_linkage.py tests/unit/test_proxy_execution.py tests/unit/test_proxy_execution_main.py tests/unit/test_executions.py tests/unit/test_executions_main.py tests/unit/test_approvals.py tests/unit/test_approvals_main.py -q`
  - PASS (`50 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_proxy_execution_api.py tests/integration/test_approval_api.py tests/integration/test_task_runs_api.py -q`
  - PASS (`28 passed`)
- `pnpm --dir apps/web test -- --runInBand components/approval-actions.test.tsx components/approval-detail.test.tsx components/execution-summary.test.tsx components/task-run-list.test.tsx lib/api.test.ts`
  - PASS (`39 passed`)
- `python3 scripts/run_phase3_validation_matrix.py`
  - PASS (all matrix steps PASS: control docs, gate contracts, readiness gates, backend integration matrix, web validation matrix)

## Blockers/Issues
- No remaining sprint blockers.
- Note: sandboxed runs without escalation cannot access local Postgres and produce false-negative integration/matrix failures (`Operation not permitted`); escalated run was used for authoritative matrix results.

## Recommended Next Step
Proceed to Control Tower review for Sprint 12 and preserve deferred scope boundaries in follow-up sprint planning.

## Explicit Deferred Scope
- Broad connector write expansion.
- Multi-tool external write-capable rollout beyond the two narrow Sprint 12 paths.
- Major retry-policy framework expansion (Sprint 13 scope).
- Sprint 13 observability/ship-gate breadth work.
