# Rules

## Truth And Scope

- The active sprint packet is the top scope boundary for implementation work.
- Treat `.ai/active/SPRINT_PACKET.md` as an input/control artifact: do not edit it during implementation unless Control Tower explicitly changes the sprint.
- Never describe planned behavior as already implemented.
- Keep canonical truth files concise, current, and durable.
- Shared runbooks and canonical docs must use machine-independent commands and links; do not use local user-home absolute paths.
- When a sprint changes the operating baseline, update canonical truth docs in the same sprint before handoff.
- Archive stale planning or history material instead of deleting it when traceability still matters.
- Do not widen product scope without an explicit roadmap or sprint change.

## Product And Safety

- Never execute a consequential external action without explicit user approval.
- Treat explainability as a product feature, not an internal debugging aid.
- Treat the repeat magnesium reorder as the v1 release-readiness validation scenario.
- Do not add proactive automation, write-capable connectors, voice, or browser automation without an explicit roadmap change.

## Architecture And Data

- Treat the immutable event store as ground truth; downstream memories, tasks, and summaries are derived or governed views.
- Always compile context per invocation from durable sources.
- Keep prompt assembly, tool schemas, and serialized context ordering deterministic.
- Treat Postgres as the v1 system of record unless measured constraints justify a change.
- Task-step lineage and execution linkage must stay explicit; do not reconstruct them heuristically from broader task history.
- Enforce row-level security on every user-owned table.
- Connector secrets must not be stored on normal metadata tables or exposed on read surfaces; they must use a dedicated protected storage seam.
- Default memory admission to `NOOP`; promote only evidence-backed changes and preserve revision history for non-`NOOP` updates.
- Apply domain and sensitivity filters before semantic retrieval.

## Delivery And Testing

- Build against typed contracts and migration-backed schemas first.
- Keep changes small, module-scoped, and test-backed.
- Never bypass policy, approval, or proxy boundaries to introduce side effects.
- Schema changes are not complete without forward and rollback coverage.
- Every module needs unit tests and at least one integration boundary test.
- Approval boundaries, row-level security, audit logging, and lineage changes require adversarial tests.
- Do not make memory-quality or retrieval-quality release claims without labeled evaluation evidence.
