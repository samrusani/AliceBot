# Alice

Alice is a local-first memory and continuity engine for AI agents.

`P9-S33` shipped the public-core baseline. `P9-S34` shipped the deterministic local CLI for continuity flows on top of that baseline. `P9-S35` shipped a narrow MCP transport for the same continuity contract. `P9-S36` ships the first OpenClaw adapter/import path on top of those shipped surfaces.

## Canonical Local Startup Path (`P9-S33`)

1. Copy environment defaults:
   `cp .env.example .env`
2. Create a virtualenv and install dependencies:
   `python3 -m venv .venv && ./.venv/bin/python -m pip install -e '.[dev]'`
3. Start local infrastructure:
   `docker compose up -d`
4. Apply migrations:
   `./scripts/migrate.sh`
5. Load deterministic sample data:
   `./scripts/load_sample_data.sh`
6. Start the API:
   `./scripts/api_dev.sh`

The sample fixture path is `fixtures/public_sample_data/continuity_v1.json` and defaults through `PUBLIC_SAMPLE_DATA_PATH`.

## CLI Invocation Path (`P9-S34`)

CLI works from the local editable install:

```bash
./.venv/bin/python -m alicebot_api --help
```

Optional console-script entrypoint (after editable install):

```bash
alicebot --help
```

If `ALICEBOT_AUTH_USER_ID` is set (default in `.env.example`), CLI commands run in that user scope. Otherwise CLI defaults to `00000000-0000-0000-0000-000000000001`.

## CLI Continuity Commands

Run these against the `P9-S33` sample dataset after startup:

```bash
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api capture "Decision: Keep Alice local-first for CLI verification." --explicit-signal decision
./.venv/bin/python -m alicebot_api recall --query local-first
./.venv/bin/python -m alicebot_api resume
./.venv/bin/python -m alicebot_api open-loops
./.venv/bin/python -m alicebot_api review queue --status correction_ready --limit 20
./.venv/bin/python -m alicebot_api review show <continuity_object_id>
./.venv/bin/python -m alicebot_api review apply <continuity_object_id> --action supersede --replacement-title "Decision: Updated title" --replacement-body-json '{"decision_text":"Updated title"}' --replacement-provenance-json '{"thread_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}' --replacement-confidence 0.97
```

The CLI output is deterministic text (stable section order and provenance snippets) to support `P9-S35` MCP parity.

## MCP Invocation Path (`P9-S35`)

Run the MCP server from the same local runtime used by CLI:

```bash
./.venv/bin/python -m alicebot_api.mcp_server --help
./.venv/bin/python -m alicebot_api.mcp_server
```

Optional console-script entrypoint (after editable install):

```bash
alicebot-mcp --help
alicebot-mcp
```

MCP uses the same local auth/config scope as CLI:

- `DATABASE_URL` selects the local database
- `ALICEBOT_AUTH_USER_ID` selects the user scope (or `--user-id`)
- if unset, scope defaults to `00000000-0000-0000-0000-000000000001`

Initial ADR-003 MCP tools:

- `alice_capture`
- `alice_recall`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_context_pack`

## OpenClaw Adapter Path (`P9-S36`)

`P9-S36` delivers the first OpenClaw adapter path:

- import one sample or real OpenClaw workspace / durable-memory export
- preserve import provenance and dedupe posture
- prove Alice recall and resumption over imported OpenClaw material
- optionally prove shipped MCP tools working over that imported data

Run the local OpenClaw sample import:

```bash
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json
```

Sample proof commands against imported scope:

```bash
./.venv/bin/python -m alicebot_api recall --thread-id cccccccc-cccc-4ccc-8ccc-cccccccccccc --project "Alice Public Core" --query "MCP tool surface" --limit 5
./.venv/bin/python -m alicebot_api resume --thread-id cccccccc-cccc-4ccc-8ccc-cccccccccccc --max-recent-changes 5 --max-open-loops 5
```

Dedupe posture is deterministic: re-running the same import returns `status=noop` with `skipped_duplicates=5`.

### Compatible Client Example (Claude Desktop MCP)

`claude_desktop_config.json` example:

```json
{
  "mcpServers": {
    "alice-core": {
      "command": "/ABSOLUTE/PATH/TO/AliceBot/.venv/bin/python",
      "args": ["-m", "alicebot_api.mcp_server"],
      "cwd": "/ABSOLUTE/PATH/TO/AliceBot",
      "env": {
        "DATABASE_URL": "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot",
        "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001"
      }
    }
  }
}
```

## Essential Verification Commands

- API health: `curl -sS http://127.0.0.1:8000/healthz`
- Backend tests: `./.venv/bin/python -m pytest tests/unit tests/integration`
- Web tests: `pnpm --dir apps/web test`

## Repo Structure

- `apps/api`: FastAPI runtime and continuity core seams
- `apps/web`: operator shell
- `fixtures/public_sample_data`: deterministic public-core sample dataset
- `fixtures/openclaw`: deterministic OpenClaw adapter fixture dataset
- `scripts`: startup, migration, and sample-data load scripts
- `docs`: product, architecture, ADRs, and Phase 9 planning docs

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
- [docs/adr/ADR-004-openclaw-integration-boundary.md](docs/adr/ADR-004-openclaw-integration-boundary.md)

## Legacy Compatibility Marker

Repository lineage remains continuous through Phase 3 Sprint 9.

Canonical gate entrypoints: `scripts/run_phase4_*.py` are the control-plane canonical MVP release gates.
