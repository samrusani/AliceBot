# MCP Integration

Alice's MCP server exposes eleven core tools by default, with the legacy
long-tail surface available behind an environment flag.

## Entrypoints

```bash
./.venv/bin/python -m alicebot_api.mcp_server --help
./.venv/bin/python -m alicebot_api.mcp_server
alicebot-mcp --help
alicebot-mcp
```

`alicebot-mcp` is available after editable install.

## Runtime Scope

MCP uses the same local runtime scope as the CLI:

- `DATABASE_URL`
- `ALICEBOT_AUTH_USER_ID`

With a `sqlite:///` `DATABASE_URL` (or the packaged
`alice-memory mcp --data-dir ~/.alice`), the server bootstraps the user
row automatically on first start.

Optional:

- `ALICE_EMBEDDINGS_BASE_URL`, `ALICE_EMBEDDINGS_MODEL`,
  `ALICE_EMBEDDINGS_API_KEY` — enable semantic vector search in
  `alice_recall` and `alice_context_pack` (full-text-only without them)
- `ALICE_MCP_LEGACY_TOOLS=1` — expose the legacy long-tail tool surface only for an unbound local-operator server; ignored when `ALICE_AGENT_API_KEY` is set

## Default Tool Surface

- `alice_capture` — submit information as source-backed reviewable memory
- `alice_memory_commit` — explicit policy-checked memory write with commit / confirmation / review / reject outcomes
- `alice_recall` — hybrid full-text + vector search with fused ranking
- `alice_resume` — resumption brief for a project, person, or thread
- `alice_context_pack` — scoped context bundle for a task
- `alice_open_loops` — list or manage open loops
- `alice_recent_decisions` — recent decision log
- `alice_memory_review` — review queue inspection
- `alice_memory_correct` — approve, edit, reject, or supersede a memory
- `alice_memory_manage` — lifecycle verbs for committed memories: confirm, undo, forget, expire, redact
- `alice_explain` — provenance and trust explanation

Full schemas with per-parameter descriptions come from `tools/list`.
Details and examples: [docs/alpha/mcp-tools.md](../alpha/mcp-tools.md).

## Legacy Tool Surface

With `ALICE_MCP_LEGACY_TOOLS=1`, the 65 legacy tools are listed alongside
the eleven core tools (76 total). The legacy surface requires Postgres —
on the SQLite backend the legacy tools are listed but their calls fail.
It also requires `ALICE_AGENT_API_KEY` to be unset. Key-bound servers list
and accept only the policy-complete core tools.
The long tail covers briefs, timeline, state-at-time, capture pipelines,
queue/graph/belief/scheduler controls, provider runtime tools, and the
`alice_vnext_*` agentic control-plane contract, including
`alice_vnext_ingest_agent_output` (agent-output capture as untrusted source
evidence) and `alice_vnext_commit_memory` (explicit policy-checked memory
writes with commit / confirmation / review / reject outcomes).

The legacy surface is frozen: existing integrations keep working, new
capabilities land on the core eleven.

For first-run memory expectations and a deterministic way to prove memory
is working, see [../alpha/first-memory.md](../alpha/first-memory.md).
Normal chat is not guaranteed to become trusted memory; explicit memory
instructions should use an explicit commit or capture call.

## Example: Claude Desktop MCP Config

```json
{
  "mcpServers": {
    "alice": {
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

- `docs/integrations/hermes-bridge-operator-guide.md` (recommended provider+MCP path)
- `docs/integrations/hermes.md`
- `docs/integrations/hermes-memory-provider.md`
- `docs/integrations/hermes-skill-pack.md`

Recommended bridge deployment shape:

- provider plus MCP is the default operator path
- MCP-only remains available as fallback when provider install is blocked

One-command bridge demo:

```bash
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

## Contract Guardrails

- the default tool set is intentionally small and stable
- responses are compact by default; diagnostic traces are opt-in via the
  `debug` parameter on read tools
- agent-proposed memory requires review; nothing an agent submits becomes
  trusted memory without passing the commit policy engine
- agent-output ingestion treats agent text as untrusted source evidence

See tests:

- `tests/unit/test_mcp.py`
- `tests/integration/test_mcp_server.py`
- `tests/integration/test_temporal_state_mcp_cli.py`
- `tests/integration/test_openclaw_mcp_integration.py`
