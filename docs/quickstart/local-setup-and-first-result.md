# Local Setup and First Useful Result

This quickstart is the canonical local path for the shipped `v0.2.0` pre-1.0 surface.

## Prerequisites

- Python `3.12+`
- Docker + Docker Compose
- Node + pnpm (required for web tests)
- Hermes runtime modules available in `.venv` for bridge smoke commands (`agent` and `tools` imports)

## 1) Prepare Environment and Install

```bash
cp .env.example .env
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
```

## 2) Start Local Runtime

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
```

## 3) Start API

```bash
APP_RELOAD=false ./scripts/api_dev.sh
```

## 4) Verify Health

Run in another terminal:

```bash
curl -sS http://127.0.0.1:8000/healthz
```

Expected: JSON with `"status": "ok"`.

## 5) Get First Useful Result (CLI)

```bash
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api recall --query local-first --limit 5
./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5
./.venv/bin/python -m alicebot_api open-loops --limit 5
```

- `recall` returns deterministic continuity items with provenance snippets.
- `resume` returns deterministic brief fields (`last_decision`, `next_action`, recent changes/open loops).

## 6) Optional: Prove Shipped Importer Paths

```bash
./scripts/use_alice_with_openclaw.sh
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_dir_v1
./scripts/load_markdown_sample_data.sh --source fixtures/importers/markdown/workspace_v1.md
./scripts/load_chatgpt_sample_data.sh --source fixtures/importers/chatgpt/workspace_v1.json
```

Repeat the same command to verify deterministic dedupe posture (`status=noop`, duplicate skips).
OpenClaw details: `docs/integrations/openclaw.md`.

## 7) Required Validation Commands for Release Readiness

```bash
python3 scripts/check_control_doc_truth.py
./.venv/bin/python -m pytest tests/unit tests/integration -q
pnpm --dir apps/web test
./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py
./.venv/bin/python scripts/run_hermes_mcp_smoke.py
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

## Scope Guard

This quickstart documents shipped behavior through Phase 11 and Bridge `B1` through `B4`.
It does not promise `v1.0.0` compatibility/support guarantees or unshipped feature scope.
