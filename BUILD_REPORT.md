# BUILD_REPORT.md

## Sprint Objective
Implement Sprint 7G MVP extensive validation matrix: one deterministic command that runs readiness prerequisite + bounded backend seams + bounded web operator-shell suites and returns explicit `PASS`/`NO_GO`.

## Completed Work
- Added `scripts/run_mvp_validation_matrix.py` with deterministic step order:
  - `readiness_gates` (`python3 scripts/run_mvp_readiness_gates.py`)
  - `backend_integration_matrix` (bounded seam-focused integration test list)
  - `web_validation_matrix` (explicit Vitest matrix for `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, `/traces`)
- Added explicit failing-step signaling and final result contract:
  - Per-step `PASS`/`FAIL`, command, duration, exit code, coverage
  - `Failing steps: ...` line on non-pass runs
  - exit code `0` only when all steps pass
- Added deterministic induced-failure support:
  - `--induce-step {readiness_gates|backend_integration_matrix|web_validation_matrix}`
  - forced exit code `97` on selected step for no-go contract verification
- Added `tests/integration/test_mvp_validation_matrix.py`:
  - sequence/coverage contract assertions
  - exit-code contract assertions
  - induced failure propagation and output-shape assertions
- Added web matrix command to `apps/web/package.json`:
  - `test:mvp:validation-matrix`
  - explicit bounded suite list (no autodiscovery)
- Added `docs/runbooks/mvp-validation-matrix.md`:
  - prerequisites, exact command, runtime class, deterministic negative check, triage flow
- Updated `docs/runbooks/mvp-readiness-gates.md` to document readiness as matrix prerequisite step.

## Incomplete Work
- None within Sprint 7G scope.

## Exact Matrix Steps Executed
1. `readiness_gates`
2. `backend_integration_matrix`
3. `web_validation_matrix`

## Exact Commands And Environment Assumptions
Commands used:
- `python3 -m pytest -q tests/integration/test_mvp_validation_matrix.py tests/integration/test_mvp_readiness_gates.py`
- `python3 scripts/run_mvp_validation_matrix.py`
- `python3 scripts/run_mvp_validation_matrix.py --induce-step backend_integration_matrix`

Environment assumptions:
- Local Postgres reachable on configured admin/app URLs (required by readiness/backend steps).
- Python dependencies installed in project environment.
- Web dependencies installed for `apps/web` (`npm --prefix apps/web install`).

## Per-Step Outcome Table (Latest Normal Matrix Run)

| Step | Status | Duration (s) | Exit Status |
|---|---|---:|---:|
| `readiness_gates` | `PASS` | `3.404` | `0` |
| `backend_integration_matrix` | `PASS` | `27.834` | `0` |
| `web_validation_matrix` | `PASS` | `2.302` | `0` |

Normal command result:
- `python3 scripts/run_mvp_validation_matrix.py` -> `MVP validation matrix result: PASS` (process exit `0`)

## Induced-Failure Verification Summary
- Command: `python3 scripts/run_mvp_validation_matrix.py --induce-step backend_integration_matrix`
- Result:
  - `readiness_gates`: `PASS`
  - `backend_integration_matrix`: `FAIL` (`exit_code=97`, `induced_failure: true`)
  - `web_validation_matrix`: `PASS`
  - explicit output: `Failing steps: backend_integration_matrix`
  - final output: `MVP validation matrix result: NO_GO`
  - process exit: non-zero (`1`)

## Files Changed
- `/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_validation_matrix.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_mvp_validation_matrix.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/apps/web/package.json`
- `/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-validation-matrix.md`
- `/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-readiness-gates.md`
- `/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md`
- `/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md`

## Tests Run
- `python3 -m pytest -q tests/integration/test_mvp_validation_matrix.py tests/integration/test_mvp_readiness_gates.py` -> `9 passed`
- `python3 scripts/run_mvp_validation_matrix.py` -> `PASS` (all 3 matrix steps passed)
- `python3 scripts/run_mvp_validation_matrix.py --induce-step backend_integration_matrix` -> `NO_GO` (single deterministic induced failure surfaced)

## Blockers/Issues
- Sandboxed localhost DB access fails with `psycopg.OperationalError: ... Operation not permitted`; DB-backed matrix commands required unsandboxed execution for evidence collection.
- Runner output includes upstream readiness/Alembic logs, which are expected but verbose.

## Explicit Deferred Criteria Not Covered By This Sprint
- No new endpoints, migrations, or schema changes.
- No connector capability expansion or write-capability changes.
- No auth/orchestration/worker-runtime expansion.
- No new web routes or UI redesign.

## Recommended Next Step
Run `python3 scripts/run_mvp_validation_matrix.py` in reviewer CI on merge gate and use `docs/runbooks/mvp-validation-matrix.md` as the canonical triage flow for any non-pass step.
