# Task-Adaptive Briefing (Legacy Compatibility)

Task briefs compile deterministic, explainable context packs for `user_recall`,
`resume`, `worker_subtask`, and `agent_handoff`. The feature is not part of the
default v0.11 surface.

## Mount contract

- HTTP and CLI task-brief adapters require `ALICE_LEGACY_SURFACES=1` at process
  start.
- MCP `alice_task_brief`, `alice_task_brief_show`, and
  `alice_task_brief_compare` require both `ALICE_LEGACY_SURFACES=1` and
  `ALICE_MCP_LEGACY_TOOLS=1` on a keyless local server.
- Key-bound MCP never exposes these tools.
- This compatibility surface is deprecated for removal before `1.0`.

## Deterministic contract

Each brief records its mode, explicit strategy, token budget, section selection
rules, truncation counts, and a deterministic digest. Token budget resolves from
an explicit request first, then the mode default adjusted by the requested
`balanced`, `compact`, or `detailed` strategy.

Model-pack fields and workspace model-pack binding behavior were removed in
v0.11. The briefing layer still reads the surviving retrieval/resumption
services and does not replace the canonical memory system.

## Compatibility routes

- `POST /v0/task-briefs/compile`
- `GET /v0/task-briefs/{task_brief_id}`
- `POST /v0/task-briefs/compare`

These routes are absent from default OpenAPI and return `404` unless the legacy
surface flag is enabled before application construction.
