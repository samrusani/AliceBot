# BUILD_REPORT.md

## Sprint Objective
Implement Phase 4 Sprint 11 durable run backbone by adding `task_runs` persistence, deterministic task-run lifecycle APIs, worker single-step run ticking, and basic `/tasks` run review visibility without introducing real external side effects.

## Completed Work
- Added migration `20260327_0038_task_runs` with durable `task_runs` schema, deterministic constraints, RLS policy, grants, and indexes.
- Extended store seam with task-run create/read/list/update/acquire methods, including safe run acquisition (`FOR UPDATE SKIP LOCKED`).
- Added task-run contracts and lifecycle logic for create/get/list/tick/pause/resume/cancel with deterministic transition enforcement.
- Added task-run API endpoints in `apps/api/src/alicebot_api/main.py` for lifecycle operations.
- Added worker single-step tick skeleton with safe acquisition and persisted checkpoint/counter progression.
- Added `/tasks` run review UI (`live`/`fixture`/`unavailable`) and web API client/test coverage.
- Resolved review-gate blockers:
  - Added required control-doc truth markers in `PRODUCT_BRIEF.md` and `RULES.md`.
  - Added Vitest compatibility wrapper so packet web command with `--runInBand` succeeds.

## Incomplete Work
- None within this sprint’s implementation and acceptance scope.

## Files Changed
- `apps/api/alembic/versions/20260327_0038_task_runs.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/task_runs.py`
- `workers/alicebot_worker/main.py`
- `workers/alicebot_worker/task_runs.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/tasks/page.test.tsx`
- `apps/web/components/task-run-list.tsx`
- `apps/web/components/task-run-list.test.tsx`
- `apps/web/package.json`
- `apps/web/test/run-vitest.mjs`
- `tests/unit/test_20260327_0038_task_runs.py`
- `tests/unit/test_task_run_store.py`
- `tests/unit/test_task_runs.py`
- `tests/unit/test_task_runs_main.py`
- `tests/unit/test_worker_main.py`
- `tests/integration/test_task_runs_api.py`
- `PRODUCT_BRIEF.md`
- `RULES.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
- `./.venv/bin/python -m pytest tests/unit/test_20260327_0038_task_runs.py tests/unit/test_task_run_store.py tests/unit/test_task_runs.py tests/unit/test_task_runs_main.py tests/unit/test_worker_main.py -q`
  - PASS (`18 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_task_runs_api.py -q`
  - PASS (`3 passed`)
- `pnpm --dir apps/web test -- --runInBand app/tasks/page.test.tsx components/task-run-list.test.tsx lib/api.test.ts`
  - PASS (`31 passed`)
- `python3 scripts/check_control_doc_truth.py`
  - PASS
- `python3 scripts/run_phase3_validation_matrix.py`
  - PASS (all matrix steps PASS)

## Blockers / Issues
- No active blockers.
- Note: full validation matrix requires local Postgres access; sandbox-only execution can produce false failures without escalation.

## Recommended Next Step
Proceed with Control Tower sign-off and sprint PR merge flow.
