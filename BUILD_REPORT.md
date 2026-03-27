# BUILD_REPORT.md

## Sprint Objective
Implement Phase 4 Sprint 13: Run Observability, Failure Discipline, and Ship Gates by making run lifecycle transitions auditable, retry/failure behavior explicit and persisted, and Phase 4 validation commands deterministic.

## Completed Work
- Added migration `apps/api/alembic/versions/20260327_0040_task_run_retry_failure_controls.py`:
  - added `retry_count`, `retry_cap`, `retry_posture`, `failure_class`, `last_transitioned_at` to `task_runs`
  - migrated legacy run statuses/reasons (`waiting -> waiting_user`, `completed -> done`)
  - fail-closed budget-exhausted paused rows to `failed` with explicit budget failure semantics
  - replaced task-run check constraints with Sprint 13 status/stop-reason/failure/retry enums
  - added transition timestamp index
  - normalized legacy `paused + budget_exhausted` posture mapping to terminal retry posture during upgrade
- Extended run contracts and API models in `apps/api/src/alicebot_api/contracts.py` and `apps/api/src/alicebot_api/main.py`:
  - new run statuses: `queued`, `running`, `waiting_approval`, `waiting_user`, `paused`, `failed`, `done`, `cancelled`
  - explicit stop reasons including `budget_exhausted`, `policy_blocked`, `approval_rejected`, `retry_exhausted`, `fatal_error`
  - explicit failure classes: `transient`, `policy`, `approval`, `budget`, `fatal`
  - explicit retry posture: `none`, `retryable`, `exhausted`, `terminal`, `paused`, `awaiting_approval`, `awaiting_user`
  - create-run input now accepts optional `retry_cap`
- Wired new persistence fields in `apps/api/src/alicebot_api/store.py`:
  - task-run insert/get/list/update/acquire SQL now includes retry/failure/transition metadata
  - store row schema and optional update APIs now carry retry/failure fields
- Reworked run lifecycle logic in `apps/api/src/alicebot_api/task_runs.py`:
  - deterministic transition evidence in checkpoint (`transitions[]` and `last_transition`)
  - terminal states now use `failed`/`done` explicitly
  - waiting path now resolves to `waiting_user`
  - budget exhaustion now fail-closes to `failed` with budget class
  - added failure helper (`mark_task_run_failed`) for worker/runtime exception paths
- Updated approval/execution integration for explicit failure and transition telemetry:
  - `apps/api/src/alicebot_api/approvals.py`: reject path sets `failed` + `approval_rejected` + `failure_class=approval`; approved path requeues
  - `apps/api/src/alicebot_api/proxy_execution.py`: blocked execution fail-closes linked run (`policy_blocked`/`budget_exhausted` classification), emits run diagnostics trace event
- Updated worker failure discipline:
  - `workers/alicebot_worker/tool_execution.py`, `workers/alicebot_worker/task_runs.py`, `workers/alicebot_worker/main.py`
  - worker exceptions now write explicit run failure/retry posture instead of silent drop
  - worker logs include stop reason, failure class, retry count/cap, posture
- Updated web diagnostics surfaces:
  - `apps/web/lib/api.ts` and tests with new run unions and fields
  - `apps/web/app/tasks/page.tsx` fixtures moved to Sprint 13 statuses/diagnostics
  - `apps/web/components/task-run-list.tsx` now surfaces retry posture/count/cap, failure class, transition timestamps/source
  - added `apps/web/app/traces/page.test.tsx` coverage
- Added Phase 4 gate wrappers and runbooks:
  - `scripts/run_phase4_acceptance.py`
  - `scripts/run_phase4_readiness_gates.py`
  - `scripts/run_phase4_validation_matrix.py`
  - `docs/runbooks/phase4-acceptance-suite.md`
  - `docs/runbooks/phase4-readiness-gates.md`
  - `docs/runbooks/phase4-validation-matrix.md`
  - `docs/runbooks/phase4-closeout-packet.md`
- Updated canonical control docs for Sprint 13 truth sync:
  - `README.md`
  - `ROADMAP.md`
  - `.ai/handoff/CURRENT_STATE.md`
- Updated sprint-scoped unit/integration/web tests to reflect deterministic Sprint 13 run semantics.

## Incomplete Work
- None within Sprint 13 packet scope.

## Files Changed
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `ROADMAP.md`
- `apps/api/alembic/versions/20260327_0040_task_run_retry_failure_controls.py`
- `apps/api/src/alicebot_api/approvals.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/proxy_execution.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/task_runs.py`
- `workers/alicebot_worker/main.py`
- `workers/alicebot_worker/task_runs.py`
- `workers/alicebot_worker/tool_execution.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/tasks/page.test.tsx`
- `apps/web/app/traces/page.test.tsx`
- `apps/web/components/task-run-list.tsx`
- `apps/web/components/task-run-list.test.tsx`
- `tests/unit/test_20260327_0040_task_run_retry_failure_controls.py`
- `tests/unit/test_task_runs.py`
- `tests/unit/test_task_run_store.py`
- `tests/unit/test_proxy_execution.py`
- `tests/unit/test_approvals.py`
- `tests/unit/test_worker_main.py`
- `tests/integration/test_task_runs_api.py`
- `tests/integration/test_proxy_execution_api.py`
- `scripts/run_phase4_acceptance.py`
- `scripts/run_phase4_readiness_gates.py`
- `scripts/run_phase4_validation_matrix.py`
- `docs/runbooks/phase4-acceptance-suite.md`
- `docs/runbooks/phase4-readiness-gates.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `docs/runbooks/phase4-closeout-packet.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
- `./.venv/bin/python -m pytest tests/unit/test_20260327_0040_task_run_retry_failure_controls.py tests/unit/test_task_runs.py tests/unit/test_task_runs_main.py tests/unit/test_proxy_execution.py tests/unit/test_proxy_execution_main.py tests/unit/test_worker_main.py -q`
  - PASS (`37 passed`)
- `pnpm --dir apps/web test -- --runInBand app/tasks/page.test.tsx app/traces/page.test.tsx components/task-run-list.test.tsx components/execution-summary.test.tsx lib/api.test.ts`
  - PASS (`37 passed`)
- `./.venv/bin/python -m pytest tests/integration/test_task_runs_api.py tests/integration/test_proxy_execution_api.py tests/integration/test_approval_api.py -q`
  - PASS (`28 passed`)
- `python3 scripts/run_phase4_validation_matrix.py`
  - PASS (`Phase 4 validation matrix result: PASS`)
- `python3 scripts/run_phase3_validation_matrix.py`
  - PASS (`Phase 2 validation matrix result: PASS` in phase3 chain)

## Blockers/Issues
- No functional blockers remain.
- Environment note: non-escalated sandbox runs cannot reach local Postgres (`Operation not permitted` on `localhost:5432`), so DB-backed acceptance commands were rerun with escalated permissions for authoritative results.

## Recommended Next Step
Submit for Control Tower Sprint 13 review/sign-off, then open the sprint PR from `codex/phase4-sprint-13-run-observability-ship-gates`.

## Explicit Deferred Scope
- Connector breadth expansion beyond current narrow rollout
- Auth model expansion/redesign
- Multi-orchestrator runtime experiments
- Broader platform/channel distribution changes
