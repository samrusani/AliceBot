# Local Setup and First Useful Result

This quickstart is the canonical `P9-S38` path for external technical testers.

## Prerequisites

- Python `3.12+`
- Docker + Docker Compose
- Node + pnpm (only required if you run web tests)

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
```

- `recall` should return deterministic continuity items with provenance snippets.
- `resume` should return deterministic brief fields (`last_decision`, `next_action`, recent changes/open loops).

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

## 7) Optional: Generate Evaluation Evidence

```bash
EVAL_USER_ID="$(./.venv/bin/python -c 'import uuid; print(uuid.uuid4())')"
EVAL_USER_EMAIL="phase9-eval-${EVAL_USER_ID}@example.com"
./scripts/run_phase9_eval.sh --user-id "${EVAL_USER_ID}" --user-email "${EVAL_USER_EMAIL}" --display-name "Phase9 Eval" --report-path eval/reports/phase9_eval_latest.json
```

- baseline reference: `eval/baselines/phase9_s37_baseline.json`
- generated report: `eval/reports/phase9_eval_latest.json`

## 8) Required Validation Commands for Sprint Acceptance

```bash
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
```

## Scope Guard

This quickstart documents only shipped local runtime behavior (`P9-S33` to `P9-S37`).
It does not promise hosted deployment, new importer families, or MCP tool expansion.
