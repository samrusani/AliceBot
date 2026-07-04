# One-Call Continuity

One continuity call is the default integration path for external agents:

- API: `POST /v1/continuity/brief`
- CLI: `alice brief`
- MCP: `alice_brief` (legacy surface; requires `ALICE_MCP_LEGACY_TOOLS=1`)

This surface composes the shipped recall, resumption, contradiction, trust, and task-briefing systems into one response bundle so callers do not need tool choreography.

## Defaults

- default `brief_type`: `general`
- timeline highlights: included by default
- `coding_context` and `operator_context` keep the same response shape as other brief types and differ by selection strategy only

## Supported Brief Types

- `general`
- `resume`
- `agent_handoff`
- `coding_context`
- `operator_context`

## Response Bundle

Every one-call brief returns:

- `summary`
- `relevant_facts`
- `recent_changes`
- `open_loops`
- `conflicts`
- `timeline_highlights`
- `next_suggested_action`
- `provenance_bundle`
- `trust_posture`

## API

`POST /v1/continuity/brief` uses the authenticated `v1` API surface.

Example:

```bash
curl -X POST http://localhost:8000/v1/continuity/brief \
  -H "Authorization: Bearer $ALICE_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "brief_type": "general",
    "thread_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "query": "deploy",
    "max_relevant_facts": 6,
    "max_recent_changes": 5,
    "max_open_loops": 5,
    "max_conflicts": 5,
    "max_timeline_highlights": 5
  }'
```

## CLI

After an editable install (`pip install -e '.[dev]'`), the `alice` entrypoint is available:

```bash
alice brief --brief-type general --query deploy
```

If you are running directly from the repository Python runtime:

```bash
./.venv/bin/python -m alicebot_api brief --brief-type general --query deploy
```

## MCP

The default MCP surface is the nine core tools (see [docs/integrations/mcp.md](mcp.md)); `alice_resume` and `alice_context_pack` cover most continuity lookups there. The `alice_brief` tool lives on the legacy surface and requires the MCP server to run with `ALICE_MCP_LEGACY_TOOLS=1`.

Example:

```json
{
  "name": "alice_brief",
  "arguments": {
    "brief_type": "coding_context",
    "thread_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "query": "deploy"
  }
}
```

## When To Use Other Surfaces

- use `alice_recall` (core) when you only need ranked facts
- use `alice_resume` (core) when you only need a resumption brief
- use `alice_task_brief` (legacy, needs `ALICE_MCP_LEGACY_TOOLS=1`) when you explicitly want persisted task-adaptive briefing output
