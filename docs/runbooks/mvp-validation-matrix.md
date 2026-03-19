# MVP Validation Matrix Runbook

## Objective
Run one deterministic command that executes MVP readiness prerequisites plus bounded backend and web verification matrices, then emits a clear `PASS` or `NO_GO`.

## Prerequisites
- Python dependencies installed for backend integration tests (`python3 -m venv .venv` and `./.venv/bin/python -m pip install -e '.[dev]'`).
- Local Postgres available at configured admin/app URLs for integration tests and readiness gates.
- Web dependencies installed (`npm --prefix apps/web install`).

## Exact Command
```bash
python3 scripts/run_mvp_validation_matrix.py
```

The runner executes this deterministic step order:
1. `readiness_gates`
   - `python3 scripts/run_mvp_readiness_gates.py`
2. `backend_integration_matrix`
   - `python3 -m pytest -q tests/integration/test_continuity_api.py tests/integration/test_responses_api.py tests/integration/test_approval_api.py tests/integration/test_proxy_execution_api.py tests/integration/test_tasks_api.py tests/integration/test_traces_api.py tests/integration/test_memory_review_api.py tests/integration/test_entities_api.py tests/integration/test_task_artifacts_api.py tests/integration/test_gmail_accounts_api.py tests/integration/test_calendar_accounts_api.py`
3. `web_validation_matrix`
   - `npm --prefix apps/web run test:mvp:validation-matrix`

Expected behavior:
- Prints per-step status with command, duration, exit code, and coverage.
- Prints explicit `Failing steps: ...` when any step fails.
- Returns exit code `0` only when all steps pass.
- Returns non-zero and final `MVP validation matrix result: NO_GO` when any step fails.

## Runtime Class
- Typical: medium-to-long local run (roughly 5-20 minutes, machine-dependent).
- Slowest segments are DB-backed backend integration and full web Vitest matrix.

## Optional Deterministic Negative Check
```bash
python3 scripts/run_mvp_validation_matrix.py --induce-step backend_integration_matrix
```

`--induce-step` choices:
- `readiness_gates`
- `backend_integration_matrix`
- `web_validation_matrix`

This intentionally forces one chosen step to fail and verifies deterministic no-go signaling plus failing-step reporting.

## Failure Triage Flow
1. Check `Failing steps` in output.
2. Re-run only the failing command shown in that step to inspect detailed test output.
3. Resolve the failing seam/surface.
4. Re-run `python3 scripts/run_mvp_validation_matrix.py` to regenerate full matrix evidence.
