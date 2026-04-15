# One-Call Continuity

Phase 13 makes one continuity call the default integration path for external agents:

- API: `POST /v1/continuity/brief`
- CLI: `alice brief`
- MCP: `alice_brief`

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

If you installed the Node wrapper package:

```bash
alice brief --brief-type general --query deploy
```

If you are running directly from the repository Python runtime:

```bash
./.venv/bin/python -m alicebot_api brief --brief-type general --query deploy
```

## MCP

`alice_brief` is now the default MCP continuity lookup for external agents.

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

- use `alice_recall` when you only need ranked facts
- use `alice_resume` when you only need the legacy resumption layout
- use `alice_task_brief` when you explicitly want persisted task-adaptive briefing output
