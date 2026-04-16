# BUILD_REPORT

## sprint objective

Eliminate the disk-exhaustion risk from unbounded local logging by making local/Lite startup default to stdout, disabling access logs by default in that profile, retaining bounded file logging only as an explicit opt-in, and documenting the recommended `systemd`/`journald` posture.

## completed work

- Added explicit runtime logging settings to `alicebot_api.config`.
- Added `alicebot_api.logging_config` to build explicit uvicorn logging config.
- Added `alicebot_api.local_server` so the local launcher runs uvicorn with explicit logging behavior instead of implicit defaults.
- Changed `scripts/api_dev.sh` to default to `APP_LOG_MODE=stdout` and `APP_ACCESS_LOG=false`.
- Changed `scripts/alice_lite_up.sh` to enforce the same local/Lite logging defaults.
- Added bounded rotating file logging for explicit `APP_LOG_MODE=file` usage, with required `APP_LOG_PATH`, `APP_LOG_MAX_BYTES`, and `APP_LOG_BACKUP_COUNT`.
- Updated `.env.example` and `.env.lite.example` to make the logging posture explicit.
- Updated local/deployment docs to recommend stdout plus `systemd`/`journald`, and documented bounded file logging as opt-in only.
- Added unit and integration coverage for logging config, local/Lite launcher behavior, docs markers, and `/tmp` log-file safety.

## incomplete work

- None.

## files changed

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`
- `CURRENT_STATE.md`
- `PRODUCT_BRIEF.md`
- `ROADMAP.md`
- `RULES.md`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/logging_config.py`
- `apps/api/src/alicebot_api/local_server.py`
- `scripts/api_dev.sh`
- `scripts/alice_lite_up.sh`
- `scripts/check_control_doc_truth.py`
- `.env.example`
- `.env.lite.example`
- `docs/quickstart/local-setup-and-first-result.md`
- `docs/runbooks/v0.4.0-public-release-runbook.md`
- `tests/unit/test_config.py`
- `tests/unit/test_phase13_alice_lite_assets.py`
- `tests/unit/test_logging_config.py`
- `tests/unit/test_hotfix_logging_assets.py`
- `tests/integration/test_api_logging_smoke.py`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_config.py tests/unit/test_logging_config.py tests/unit/test_hotfix_logging_assets.py tests/unit/test_phase13_alice_lite_assets.py tests/integration/test_api_logging_smoke.py tests/integration/test_healthcheck.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_logging_config.py tests/unit/test_phase13_alice_lite_assets.py tests/integration/test_api_logging_smoke.py tests/integration/test_healthcheck.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_config.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_config.py tests/unit/test_hotfix_logging_assets.py -q`
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`

## blockers/issues

- No implementation blocker remained.
- Control Tower defaults were not finalized in the packet; this hotfix retains file logging as an opt-in mode with bounded rotation defaults of `10485760` bytes and `5` backups.

## recommended next step

Run review on the hotfix diff, then merge as a defect-only patch once approval is explicit.
