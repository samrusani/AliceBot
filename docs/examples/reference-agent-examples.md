# Reference Agent Examples

These examples show the narrow default adoption path for a generic external agent: call Alice one time through `POST /v1/continuity/brief`, then use the returned bundle inside your runtime.

## Files

- Python: `docs/examples/generic_python_agent.py`
- TypeScript: `docs/examples/generic_typescript_agent.ts`

Both examples:

- call `POST /v1/continuity/brief`
- accept `ALICE_API_BASE_URL` and `ALICE_SESSION_TOKEN`
- optionally accept `ALICE_THREAD_ID`, `ALICE_QUERY`, and `ALICE_BRIEF_TYPE`
- print a compact JSON summary that a host runtime can consume directly

## Runtime Notes

- the Python example runs with the repository virtualenv shown below
- the TypeScript example assumes a Node runtime that supports `--experimental-strip-types`

## Run The Python Example

```bash
ALICE_API_BASE_URL="http://127.0.0.1:8000" \
ALICE_SESSION_TOKEN="<session-token>" \
./.venv/bin/python docs/examples/generic_python_agent.py
```

## Run The TypeScript Example

```bash
ALICE_API_BASE_URL="http://127.0.0.1:8000" \
ALICE_SESSION_TOKEN="<session-token>" \
node --experimental-strip-types docs/examples/generic_typescript_agent.ts
```

## Reproducible Demo

Run both examples against the shipped response contract demo server:

```bash
./.venv/bin/python scripts/run_reference_agent_examples_demo.py
```

The demo serves a shared canonical continuity-brief fixture from `fixtures/reference_integrations/continuity_brief_agent_handoff_v1.json` so the example output stays tied to a checked-in contract shape instead of an ad hoc inline payload.

Expected JSON output:

- `status` = `pass`
- `python_example.returncode` = `0`
- `typescript_example.returncode` = `0`
- both example outputs include the same `brief_type`, `summary`, and `next_suggested_action`

## When To Use Something Else

- use `alice_brief` instead of HTTP when your host runtime is already speaking MCP
- use `docs/integrations/hermes.md` when Hermes owns orchestration
- use `docs/integrations/openclaw.md` when imported OpenClaw memory is part of the adoption path
