# MCP Integration

The shipped MCP server (`P9-S35`) exposes a deliberately small deterministic tool surface over local Alice continuity seams.

## Entrypoints

```bash
./.venv/bin/python -m alicebot_api.mcp_server --help
./.venv/bin/python -m alicebot_api.mcp_server
alicebot-mcp --help
alicebot-mcp
```

`alicebot-mcp` is available after editable install.

## Runtime Scope

MCP uses the same local runtime scope as CLI:

- `DATABASE_URL`
- `ALICEBOT_AUTH_USER_ID`

## Shipped Tool Surface

- `alice_capture`
- `alice_recall`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_context_pack`

## Example: Claude Desktop MCP Config

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

## Hermes

For Hermes Agent-specific setup, prompts, and troubleshooting:

- `docs/integrations/hermes.md`

## Contract Guardrails

- tool set is intentionally narrow and stable
- tool output is deterministic for parity testing
- MCP does not widen core product semantics

See tests:

- `tests/unit/test_mcp.py`
- `tests/integration/test_mcp_server.py`
- `tests/integration/test_openclaw_mcp_integration.py`
