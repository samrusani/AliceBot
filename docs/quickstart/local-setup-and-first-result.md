# Local Setup and First Useful Result

This quickstart is the canonical Alice Lite path for the completed `v0.4.0` pre-1.0 public release.
Alice Lite is a lighter local/dev deployment profile, not a separate product.
It keeps the shipped continuity semantics and the shipped one-call continuity surface intact.

## Prerequisites

- Python `3.12+`
- Docker + Docker Compose

## 1) Prepare Environment and Install

```bash
cp .env.example .env
cp .env.lite.example .env.lite
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
```

`.env.lite` switches the entrypoint rate limiter to in-memory mode, keeps reload off for a lighter local footprint, keeps logs on stdout, and disables access logs by default.

## 2) Start Alice Lite

```bash
./scripts/alice_lite_up.sh
```

This command starts the Lite Postgres profile, runs migrations, loads the sample fixture, and runs the API.
The default local/Lite logging posture is stdout only. It does not create a local file log in `/tmp`.

If a local file sink is explicitly required, keep it bounded:

```bash
APP_LOG_MODE=file \
APP_LOG_PATH=/var/log/alicebot/api.log \
APP_LOG_MAX_BYTES=10485760 \
APP_LOG_BACKUP_COUNT=5 \
./scripts/api_dev.sh
```

For managed environments, keep `APP_LOG_MODE=stdout` and let `systemd`/`journald` own retention instead of writing an application-managed local log file.

## 3) Verify Health

Run in another terminal:

```bash
curl -sS http://127.0.0.1:8000/healthz
```

Expected: JSON with `"status": "ok"`.

## 4) Bootstrap the Sample Workspace and Get a First Result

```bash
./.venv/bin/python scripts/bootstrap_alice_lite_workspace.py
```

This runs the simulated local magic-link flow, creates a sample workspace, completes workspace bootstrap, and calls `POST /v1/continuity/brief` against the seeded sample thread.

## 5) Get the Same First Result from the CLI

```bash
./.venv/bin/python -m alicebot_api brief --brief-type general --query "local-first startup path"
```

The `brief` command is the shipped one-call continuity entrypoint for local CLI use.

## 6) Inspect Runtime Status

```bash
./.venv/bin/python -m alicebot_api status
```

## 7) Optional: Capture and Explain

```bash
./.venv/bin/python -m alicebot_api capture "Remember that the Q3 board pack is due on Thursday."
./.venv/bin/python -m alicebot_api explain <continuity_object_id>
```

## 8) Optional: Prove Shipped Importer Paths

```bash
./scripts/use_alice_with_openclaw.sh
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_dir_v1
./scripts/load_markdown_sample_data.sh --source fixtures/importers/markdown/workspace_v1.md
./scripts/load_chatgpt_sample_data.sh --source fixtures/importers/chatgpt/workspace_v1.json
```

Repeat the same command to verify deterministic dedupe posture (`status=noop`, duplicate skips).
OpenClaw details: `docs/integrations/openclaw.md`.

## 9) Lite Smoke Verification

```bash
./.venv/bin/python scripts/run_alice_lite_smoke.py
```

This verifies the Lite health endpoint and the CLI one-call continuity brief output.

## 10) Required Validation Commands for Release Readiness

```bash
python3 scripts/check_control_doc_truth.py
./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q
./.venv/bin/python -m pytest tests/unit/test_phase13_alice_lite_assets.py -q
./.venv/bin/python -m pytest tests/unit/test_logging_config.py tests/integration/test_api_logging_smoke.py -q
./.venv/bin/python scripts/run_alice_lite_smoke.py
```

For the wider repo validation surface beyond Alice Lite, keep using the existing web and Hermes test flows separately.

## Scope Guard

This quickstart documents the Alice Lite deployment profile on top of the shipped Phase 13 and Bridge `B1` through `B4` baseline.
It does not define a second product, a semantic fork, or unshipped `v1.0.0` scope.
