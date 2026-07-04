# Local Setup and First Result (Pointer)

The canonical setup walkthrough lives at [docs/alpha/quickstart.md](../alpha/quickstart.md).

Short version:

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
make setup
make migrate
make doctor
make dev
```

## Minimal Profile (Alice Lite)

Alice Lite is a lighter local deployment profile of the same system, not a separate product. If you want the smallest possible local footprint:

```bash
./scripts/alice_lite_up.sh
```

This starts the Lite Postgres profile, runs migrations, loads the sample fixture, and runs the API with stdout-only logging. Then, in another terminal:

```bash
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python scripts/bootstrap_alice_lite_workspace.py
./.venv/bin/python -m alicebot_api brief --brief-type general --query "local-first startup path"
./.venv/bin/python scripts/run_alice_lite_smoke.py
```

## Logging

Local and Lite runs log to stdout only by default, and access logs stay off. To opt into bounded file logging instead:

```bash
APP_LOG_MODE=file
APP_LOG_PATH=/var/log/alicebot/api.log
APP_LOG_MAX_BYTES=10485760
APP_LOG_BACKUP_COUNT=5
```

File logging rotates at the configured size and keeps the configured number of backups, so logs cannot grow without bound.

## Importers

To load existing data instead of starting from zero:

```bash
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json
./scripts/load_markdown_sample_data.sh --source fixtures/importers/markdown/workspace_v1.md
./scripts/load_chatgpt_sample_data.sh --source fixtures/importers/chatgpt/workspace_v1.json
```

Repeating a command verifies deterministic dedupe (`status=noop`, duplicate skips). Details: [docs/integrations/importers.md](../integrations/importers.md).
