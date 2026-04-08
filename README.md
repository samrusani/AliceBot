# Alice

Alice is a local-first memory and continuity engine for AI agents.

`P9-S33` through `P9-S37` shipped the public core, deterministic CLI, deterministic MCP transport, OpenClaw adapter path, broader importer coverage, and reproducible local evaluation harness. `P9-S38` packages those shipped surfaces into launch-ready docs and release assets without widening product scope.

## What v0.1 Ships

- local-first runtime (`docker compose`, Postgres, API)
- continuity CLI (`python -m alicebot_api` / `alicebot`)
- MCP server (`python -m alicebot_api.mcp_server` / `alicebot-mcp`)
- shipped importer paths:
  - OpenClaw (`openclaw_import`)
  - Markdown (`markdown_import`)
  - ChatGPT export (`chatgpt_import`)
- reproducible evaluation harness (`./scripts/run_phase9_eval.sh`)

## Quickstart: First Useful Result

Run this exact path on a clean checkout:

```bash
cp .env.example .env
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
```

Start the API:

```bash
APP_RELOAD=false ./scripts/api_dev.sh
```

In another terminal, verify health and run continuity commands:

```bash
curl -sS http://127.0.0.1:8000/healthz
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api recall --query local-first --limit 5
./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5
```

This is the canonical quickstart used for launch docs and release verification.

Detailed guide: [docs/quickstart/local-setup-and-first-result.md](docs/quickstart/local-setup-and-first-result.md)

## Integration Docs

- CLI: [docs/integrations/cli.md](docs/integrations/cli.md)
- MCP: [docs/integrations/mcp.md](docs/integrations/mcp.md)
- Importers: [docs/integrations/importers.md](docs/integrations/importers.md)
- Command walkthrough examples: [docs/examples/phase9-command-walkthrough.md](docs/examples/phase9-command-walkthrough.md)

## Evaluation Evidence

Run the shipped harness:

```bash
EVAL_USER_ID="$(./.venv/bin/python -c 'import uuid; print(uuid.uuid4())')"
EVAL_USER_EMAIL="phase9-eval-${EVAL_USER_ID}@example.com"
./scripts/run_phase9_eval.sh --user-id "${EVAL_USER_ID}" --user-email "${EVAL_USER_EMAIL}" --display-name "Phase9 Eval" --report-path eval/reports/phase9_eval_latest.json
```

Evidence artifacts:

- baseline: `eval/baselines/phase9_s37_baseline.json`
- latest report path: `eval/reports/phase9_eval_latest.json`

## Release Assets

- release checklist: [docs/release/v0.1.0-release-checklist.md](docs/release/v0.1.0-release-checklist.md)
- release tag plan: [docs/release/v0.1.0-tag-plan.md](docs/release/v0.1.0-tag-plan.md)
- release runbook: [docs/runbooks/phase9-public-release-runbook.md](docs/runbooks/phase9-public-release-runbook.md)
- contribution policy: [CONTRIBUTING.md](CONTRIBUTING.md)
- security policy: [SECURITY.md](SECURITY.md)
- license: [LICENSE](LICENSE)

## Repo Structure

- `apps/api`: FastAPI runtime and continuity core seams
- `apps/web`: operator shell
- `fixtures/public_sample_data`: deterministic public-core sample dataset
- `fixtures/openclaw`: deterministic OpenClaw fixture dataset
- `fixtures/importers`: deterministic markdown/chatgpt importer fixtures
- `eval`: Phase 9 evaluation reports and baselines
- `scripts`: startup, migration, import, and evaluation command paths
- `docs`: quickstart, integrations, architecture, runbooks, and release assets

## Canonical Docs

- [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [RULES.md](RULES.md)
- [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- [docs/phase9-product-spec.md](docs/phase9-product-spec.md)
- [docs/phase9-sprint-33-38-plan.md](docs/phase9-sprint-33-38-plan.md)
- [docs/phase9-public-core-boundary.md](docs/phase9-public-core-boundary.md)
- [docs/phase9-bootstrap-notes.md](docs/phase9-bootstrap-notes.md)
- [docs/adr/ADR-003-mcp-tool-surface-contract.md](docs/adr/ADR-003-mcp-tool-surface-contract.md)
- [docs/adr/ADR-004-openclaw-integration-boundary.md](docs/adr/ADR-004-openclaw-integration-boundary.md)
- [docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md](docs/adr/ADR-005-import-provenance-and-dedupe-strategy.md)
- [docs/adr/ADR-007-public-evaluation-harness-scope.md](docs/adr/ADR-007-public-evaluation-harness-scope.md)

## Legacy Compatibility Marker

Repository lineage remains continuous through Phase 3 Sprint 9.

Canonical gate entrypoints: `scripts/run_phase4_*.py` are the control-plane canonical MVP release gates.
