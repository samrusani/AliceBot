# Hermes MCP Integration

This guide connects Hermes Agent to Alice MCP and verifies the exact tool path
for:

- `alice_recall`
- `alice_resume`
- `alice_open_loops`

## Prerequisites

- Hermes Agent with MCP support (`hermes mcp --help` works).
- Alice local runtime is available (`./.venv/bin/python -m alicebot_api.mcp_server --help` works).
- Postgres is reachable from the machine where Hermes runs.

## Config (`~/.hermes/config.yaml`)

Use `mcp_servers` in Hermes config.

### Option A: local command (direct Python)

```yaml
mcp_servers:
  alice_core:
    command: "/ABS/PATH/TO/AliceBot/.venv/bin/python"
    args: ["-m", "alicebot_api.mcp_server"]
    env:
      DATABASE_URL: "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
      ALICEBOT_AUTH_USER_ID: "00000000-0000-0000-0000-000000000001"
      PYTHONPATH: "/ABS/PATH/TO/AliceBot/apps/api/src:/ABS/PATH/TO/AliceBot/workers"
    tools:
      include: [alice_recall, alice_resume, alice_open_loops]
      resources: false
      prompts: false
```

### Option B: `npx` command (via `alice-cli` package)

```yaml
mcp_servers:
  alice_core:
    command: "npx"
    args: ["-y", "--package", "/ABS/PATH/TO/AliceBot/packages/alice-cli", "alice", "mcp"]
    env:
      NPM_CONFIG_CACHE: "/tmp/alice-npm-cache"
      ALICEBOT_PYTHON: "/ABS/PATH/TO/AliceBot/.venv/bin/python"
      DATABASE_URL: "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
      ALICEBOT_AUTH_USER_ID: "00000000-0000-0000-0000-000000000001"
      PYTHONPATH: "/ABS/PATH/TO/AliceBot/apps/api/src:/ABS/PATH/TO/AliceBot/workers"
    tools:
      include: [alice_recall, alice_resume, alice_open_loops]
      resources: false
      prompts: false
```

`alice mcp` shells out to `${ALICEBOT_PYTHON} -m alicebot_api.mcp_server`.

If you have a published CLI version with `mcp` support, you can replace args
with:

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

## Verify Tool Calls (Hermes Runtime Path)

Run the smoke script:

```bash
./scripts/run_hermes_mcp_smoke.py
```

Expected JSON output includes:

- `registered_tools` containing:
  - `mcp_alice_core_alice_recall`
  - `mcp_alice_core_alice_resume`
  - `mcp_alice_core_alice_open_loops`
- non-zero `recall_items`
- `open_loop_count` >= `1`

## Sample Hermes Prompts

Hermes prefixes MCP tools as `mcp_<server>_<tool>`. With server name
`alice_core`, the names are:

- `mcp_alice_core_alice_recall`
- `mcp_alice_core_alice_resume`
- `mcp_alice_core_alice_open_loops`

Prompts:

```text
Use mcp_alice_core_alice_recall with {"query":"Hermes docs","limit":5} and summarize the top 3 memories.
```

```text
Use mcp_alice_core_alice_resume with {"thread_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","max_recent_changes":5,"max_open_loops":5}. Return only decisions, next action, and blockers.
```

```text
Use mcp_alice_core_alice_open_loops with {"thread_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","limit":10}. Group results by waiting_for, blocker, stale, next_action.
```

## Alice Workflow Skill Pack

To make Alice tool usage more consistent in Hermes sessions, install the
Hermes-native Alice skill pack:

- `docs/integrations/hermes-skill-pack.md`

The pack includes:

- `alice-continuity-recall`
- `alice-resumption`
- `alice-open-loop-review`
- `alice-explain-provenance`
- `alice-correction-loop`

Skills decide when and how to call tools. MCP tools perform deterministic
continuity reads and writes.

## Troubleshooting

### `Connection failed` in `hermes mcp test`

- Confirm `command` points to an existing executable.
- Use absolute paths for `command` and `PYTHONPATH`.
- Run the server command directly:
  - `"/ABS/PATH/TO/AliceBot/.venv/bin/python" -m alicebot_api.mcp_server --help`

### Tool list is missing `alice_recall`/`alice_resume`/`alice_open_loops`

- Check `tools.include` values are unprefixed tool names:
  - `alice_recall`, `alice_resume`, `alice_open_loops`
- Run `/reload-mcp` in Hermes after config changes.
- Re-run `hermes mcp test alice_core`.

### Tools register but calls fail at runtime

- Validate `DATABASE_URL` is reachable and points to a migrated DB.
- Validate `ALICEBOT_AUTH_USER_ID` is a UUID string.
- Run `./scripts/run_hermes_mcp_smoke.py` to isolate server/runtime issues.

### `npx` path fails

- Check `npx --version`.
- Ensure `args` contains a valid local package path or a published package.
- If npm cache permissions are locked down, set `NPM_CONFIG_CACHE` to a writable path.
- If `npx` is blocked in your environment, use Option A (local command).

## Demo Screenshots

`hermes mcp test` against Alice:

![Hermes MCP test with Alice](assets/hermes/hermes-mcp-test.png)

Hermes runtime tool-call smoke result:

![Hermes runtime smoke result](assets/hermes/hermes-runtime-smoke.png)

## Test Record

Validated on `2026-04-09`:

- `HERMES_HOME=/tmp/alice-hermes-home ./.venv/bin/hermes mcp test alice_core` (local command config)
- `HERMES_HOME=/tmp/alice-hermes-home ./.venv/bin/hermes mcp test alice_core` (`npx --package ... alice mcp` config)
- `./scripts/run_hermes_mcp_smoke.py`
