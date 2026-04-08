# CLI Integration

The shipped CLI surface (`P9-S34`) runs against the same local runtime used by API and MCP.

## Entrypoints

```bash
./.venv/bin/python -m alicebot_api --help
alicebot --help
```

`alicebot` is available after editable install (`pip install -e '.[dev]'`).

## User Scope

- default user scope comes from `ALICEBOT_AUTH_USER_ID`
- fallback default if unset: `00000000-0000-0000-0000-000000000001`

## Core Commands

```bash
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api capture "Decision: Keep Alice local-first for verification." --explicit-signal decision
./.venv/bin/python -m alicebot_api recall --query local-first --limit 5
./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5
./.venv/bin/python -m alicebot_api open-loops
```

## Review and Correction Commands

```bash
./.venv/bin/python -m alicebot_api review queue --status correction_ready --limit 20
./.venv/bin/python -m alicebot_api review show <continuity_object_id>
./.venv/bin/python -m alicebot_api review apply <continuity_object_id> --action supersede --replacement-title "Decision: Updated title" --replacement-body-json '{"decision_text":"Updated title"}' --replacement-provenance-json '{"thread_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}' --replacement-confidence 0.97
```

## Determinism Contract

- output format is deterministic for stable automated validation
- provenance snippets remain visible in recall/resume responses
- correction flow updates future recall/resume results

See tests:

- `tests/integration/test_mcp_cli_parity.py`
- `tests/integration/test_mcp_server.py`
