# Hermes MCP Integration (Fallback Path)

This document covers **MCP-only fallback** setup for Hermes.

For the recommended deployment shape (provider plus MCP), use:

- `docs/integrations/hermes-bridge-operator-guide.md`

## When To Use This Path

Use MCP-only when the Alice provider plugin cannot be installed yet.

- Keep `memory.provider: builtin`.
- Attach Alice through `mcp_servers`.
- Migrate to provider plus MCP when possible.

## Prerequisites

- Hermes Agent with MCP support (`hermes mcp --help` works).
- Alice local runtime is available (`./.venv/bin/python -m alicebot_api.mcp_server --help` works).
- Postgres is reachable from the machine where Hermes runs.

## Config (`~/.hermes/config.yaml`)

### Option A: local command (direct Python)

```yaml
memory:
  provider: builtin

mcp_servers:
  alice_core:
    command: "/path/to/alicebot/.venv/bin/python"
    args: ["-m", "alicebot_api.mcp_server"]
    env:
      DATABASE_URL: "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
      ALICEBOT_AUTH_USER_ID: "00000000-0000-0000-0000-000000000001"
      PYTHONPATH: "/path/to/alicebot/apps/api/src:/path/to/alicebot/workers"
    tools:
      include:
        - alice_recall
        - alice_resume
        - alice_open_loops
        - alice_capture_candidates
        - alice_commit_captures
        - alice_review_queue
        - alice_review_apply
      resources: false
      prompts: false
```

### Option B: `npx` command (via `alice-cli` package)

```yaml
memory:
  provider: builtin

mcp_servers:
  alice_core:
    command: "npx"
    args: ["-y", "--package", "/path/to/alicebot/packages/alice-cli", "alice", "mcp"]
    env:
      NPM_CONFIG_CACHE: "/tmp/alice-npm-cache"
      ALICEBOT_PYTHON: "/path/to/alicebot/.venv/bin/python"
      DATABASE_URL: "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
      ALICEBOT_AUTH_USER_ID: "00000000-0000-0000-0000-000000000001"
      PYTHONPATH: "/path/to/alicebot/apps/api/src:/path/to/alicebot/workers"
    tools:
      include:
        - alice_recall
        - alice_resume
        - alice_open_loops
        - alice_capture_candidates
        - alice_commit_captures
        - alice_review_queue
        - alice_review_apply
      resources: false
      prompts: false
```

If you use a published CLI package with `mcp` support, replace args with:

```yaml
args: ["-y", "@aliceos/alice-cli", "mcp"]
```

## Verify Connection

```bash
hermes mcp test alice_core
```

Expected:

- `Connected`
- `Tools discovered`
- includes `alice_recall`, `alice_resume`, `alice_open_loops`

## Verify Runtime Tool Calls

```bash
./.venv/bin/python scripts/run_hermes_mcp_smoke.py
```

Expected JSON output includes:

- registered MCP tool names for recall/resume/open-loops and B2/B3 capture/review tools
- non-zero `recall_items`
- non-zero `capture_candidate_count`
- non-zero `capture_review_queued_count`
- `review_apply_resolved_action` = `confirm`

## One-Command Demo

For the full bridge demo command (provider smoke + MCP smoke):

```bash
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

## Migrate To Recommended Path

When provider install is available, move from MCP-only to provider plus MCP:

1. Install provider plugin: `./scripts/install_hermes_alice_memory_provider.py`
2. Run `hermes memory setup` and select `alice`
3. Set `memory.provider: alice`
4. Keep MCP server configured for deep workflows
5. Re-run `./.venv/bin/python scripts/run_hermes_bridge_demo.py`

## Related Docs

- `docs/integrations/hermes-bridge-operator-guide.md`
- `docs/integrations/hermes-memory-provider.md`
- `docs/integrations/hermes-skill-pack.md`
