# OpenClaw Reference Integration

Use OpenClaw when you need to import existing workspace memory into Alice and then consume that imported state through the normal Alice continuity surfaces.

This path is import plus augmentation, not a second runtime.

- OpenClaw data is imported once into Alice continuity objects.
- Imported items keep explicit `OpenClaw` provenance.
- After import, use the same Alice brief, recall, resume, CLI, and MCP surfaces you already use for native Alice data.

## One-Command Demo

Run the end-to-end import, replay, recall, and resume demo:

```bash
./scripts/use_alice_with_openclaw.sh
```

Expected JSON output:

- `status` = `pass`
- `before.recall_returned_count` = `0` for the generated demo user
- `import.first.status` = `ok`
- `import.second.status` = `noop`
- `after.recall_source_labels` includes `OpenClaw`
- `after.resume_last_decision_source_label` = `OpenClaw`
- `after.resume_next_action_source_label` = `OpenClaw`
- `checks` values are all `true`

## What Import Changes

Import augments Alice continuity retrieval. It does not replace:

- one-call continuity
- provider registration
- model-pack bindings

After import, these surfaces will include OpenClaw-backed continuity when it is relevant to the request:

- API: `POST /v1/continuity/brief`
- CLI: `alice brief`
- MCP: `alice_brief`
- targeted lookups: `alice_recall`, `alice_resume`

## Import Commands

Import the file-contract fixture:

```bash
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json
```

Import the directory-contract fixture:

```bash
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_dir_v1
```

## Before And After

Before import, scoped recall and resume usually return no OpenClaw-backed continuity for that user.

After import:

- recall returns imported continuity objects with `source_kind=openclaw_import`
- resume returns last-decision and next-action items with `source_label=OpenClaw`
- one-call continuity can include those imported objects in the same response bundle as native Alice continuity

## Replay And Dedupe Contract

- dedupe keys are deterministic for stable payloads
- replaying the same source for the same user does not create duplicates
- repeated replay returns `status=noop`
- duplicate skips are counted in `skipped_duplicates`

## Pairing With Generic Agents

OpenClaw is usually paired with the generic API or MCP integration path.

Typical flow:

1. Import OpenClaw data into Alice.
2. Query Alice through `POST /v1/continuity/brief` or `alice_brief`.
3. Let the agent act on Alice output while preserving OpenClaw provenance in the response.

Generic starter examples:

- `docs/examples/generic_python_agent.py`
- `docs/examples/generic_typescript_agent.ts`

## Fixture Sources

- file fixture: `fixtures/openclaw/workspace_v1.json`
- directory fixture: `fixtures/openclaw/workspace_dir_v1/`

## Related Docs

- `docs/integrations/importers.md`
- `docs/integrations/one-call-continuity.md`
- `docs/integrations/reference-paths.md`
