# Alice

Alice is a local-first memory and continuity engine for AI agents.

Phase 9 is complete. The repo is waiting for Phase 10 planning docs before another build sprint is activated.

## What v0.1 Ships

- local-first runtime (`docker compose`, Postgres, API)
- continuity CLI (`python -m alicebot_api` / `alicebot`)
- MCP server (`python -m alicebot_api.mcp_server` / `alicebot-mcp`)
- shipped importer paths: OpenClaw, Markdown, ChatGPT export
- reproducible evaluation harness (`./scripts/run_phase9_eval.sh`)

## Quickstart

Run this path on a clean checkout:

```bash
cp .env.example .env
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
APP_RELOAD=false ./scripts/api_dev.sh
```

In another terminal:

```bash
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api recall --query local-first --limit 5
./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5
```

Detailed guide: [docs/quickstart/local-setup-and-first-result.md](docs/quickstart/local-setup-and-first-result.md)

## Integration Docs

- CLI: [docs/integrations/cli.md](docs/integrations/cli.md)
- MCP: [docs/integrations/mcp.md](docs/integrations/mcp.md)
- Importers: [docs/integrations/importers.md](docs/integrations/importers.md)
- Walkthrough: [docs/examples/phase9-command-walkthrough.md](docs/examples/phase9-command-walkthrough.md)

## Evaluation And Release

- Eval harness: `./scripts/run_phase9_eval.sh`
- Baseline: `eval/baselines/phase9_s37_baseline.json`
- Latest report path: `eval/reports/phase9_eval_latest.json`
- Release checklist: [docs/release/v0.1.0-release-checklist.md](docs/release/v0.1.0-release-checklist.md)
- Release tag plan: [docs/release/v0.1.0-tag-plan.md](docs/release/v0.1.0-tag-plan.md)
- Release runbook: [docs/runbooks/phase9-public-release-runbook.md](docs/runbooks/phase9-public-release-runbook.md)

## Canonical Docs

- Product: [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Roadmap: [ROADMAP.md](ROADMAP.md)
- Rules: [RULES.md](RULES.md)
- Current state: [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md)
- Historical planning and control docs: [docs/archive/planning/2026-04-08-context-compaction/README.md](docs/archive/planning/2026-04-08-context-compaction/README.md)
