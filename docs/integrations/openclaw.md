# Use Alice with OpenClaw

This guide is the canonical OpenClaw integration path for Alice.

## One-Command Demo

Run the full import + recall + resume + idempotent replay demo:

```bash
./scripts/use_alice_with_openclaw.sh
```

The command prints a JSON report.

Key fields:

- `before.recall_returned_count`: expected to be `0` for the generated demo user
- `import.first.status`: expected `ok`
- `import.second.status`: expected `noop` (idempotent replay)
- `after.recall_source_labels`: expected to include `OpenClaw`
- `after.resume_last_decision_source_label`: expected `OpenClaw`
- `after.resume_next_action_source_label`: expected `OpenClaw`
- `checks`: all values expected `true`

## Import-Only Commands

Import the primary OpenClaw fixture:

```bash
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_v1.json
```

Import the directory-contract fixture:

```bash
./scripts/load_openclaw_sample_data.sh --source fixtures/openclaw/workspace_dir_v1
```

## Before/After Value

Before import, recall/resume on the scoped thread usually return no imported continuity signals.
After import:

- recall returns OpenClaw-backed continuity objects
- resume returns last-decision and next-action objects sourced from OpenClaw
- provenance labels show `OpenClaw` with `source_kind=openclaw_import`

## Determinism and Idempotency Contract

- importer dedupe keys are deterministic for stable payloads
- replaying the same source for the same user does not create duplicates
- repeated replay returns `status=noop` with duplicates counted in `skipped_duplicates`

## Fixture Sources

- file fixture: `fixtures/openclaw/workspace_v1.json`
- directory fixture: `fixtures/openclaw/workspace_dir_v1/`
