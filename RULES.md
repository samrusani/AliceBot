# Rules

## Product Scope

- Treat Alice as a memory and continuity layer first, not a broad autonomous platform.
- Keep the public contract focused on capture, recall, resume, correction, and open loops until the roadmap changes.
- Do not widen channels, hosted deployment, or connector write breadth without explicit planning updates.

## System Behavior

- Compile context from durable stored truth, not transcript replay.
- Keep public interop surfaces narrow, deterministic, and schema-driven.
- Preserve append-only continuity, correction history, and explicit provenance.
- Importers must map or reject unknown external states; never silently coerce them.

## Docs And Control

- Public docs are product surface and must match runnable commands, tests, and evidence.
- Keep `ROADMAP.md` future-facing, `.ai/handoff/CURRENT_STATE.md` current-state only, and `RULES.md` limited to durable guidance.
- Archive superseded planning and control snapshots instead of keeping them in live files.
- Do not create a fake active sprint when the repo is between planning cycles.

## Release Discipline

- New public surfaces require smoke validation, not only unit tests.
- Public quality claims require committed evidence artifacts.
- Stateful release-gating commands must document deterministic preconditions.
