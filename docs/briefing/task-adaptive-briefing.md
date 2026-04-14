# Task-Adaptive Briefing

`P12-S5` adds a dedicated briefing layer that compiles deterministic, explainable context packs for four workloads:

- `user_recall`
- `resume`
- `worker_subtask`
- `agent_handoff`

## Boundaries

- Durable continuity memory stays in the existing continuity capture, continuity object, contradiction, trust, and retrieval systems.
- Compiled task briefs are persisted separately in `task_briefs`.
- The briefing layer reads shipped retrieval and resumption behavior instead of replacing those systems.

## Mode Behavior

- `user_recall`: broad recall pack built from the highest-ranked retrieval results.
- `resume`: resumption-focused pack that preserves the shipped decision, open-loop, recent-change, and next-action behavior.
- `worker_subtask`: compact pack that prioritizes current objective, active constraints, and only the smallest critical context slice.
- `agent_handoff`: medium-sized pack that carries focus, open loops, and recent changes into a receiving agent.

## Determinism And Explainability

Each task brief records:

- the selected mode
- the resolved provider and model-pack strategy labels
- the token budget used
- per-section selection rules
- per-section truncation counts
- a deterministic digest for the compiled payload

The digest is computed from the current branch brief payload without persistence metadata, so repeated compilation for the same input yields the same digest. Control Tower still owns what persisted briefing payload shape remains canonical for `P12-S5`.

## Token Budgeting

The compiler resolves token budget in this order:

1. explicit request token budget
2. workspace-selected model-pack `briefing_max_tokens` when a `workspace_id` is provided
3. mode default budget adjusted by the resolved briefing strategy

The resolved briefing strategy can come from an explicit request override, or from the workspace-selected model pack:

- `balanced`
- `compact`
- `detailed`

Sections greedily include ordered items until the section budget is exhausted. Worker briefs intentionally use a smaller compact budget than generic recall briefs.

## Surfaces

- API, pending Control Tower confirmation that `P12-S5` should expose generation and comparison endpoints in the same sprint:
  - `POST /v0/task-briefs/compile`
  - `GET /v0/task-briefs/{task_brief_id}`
  - `POST /v0/task-briefs/compare`
- CLI:
  - `task-briefs compile`
  - `task-briefs show`
  - `task-briefs compare`
- MCP:
  - `alice_task_brief`
  - `alice_task_brief_show`
  - `alice_task_brief_compare`

## Model-Pack Strategy Fields

Model packs now persist briefing defaults through:

- `briefing_strategy`
- `briefing_max_tokens`

These fields let hosted model-pack catalog entries carry compact, balanced, or detailed briefing defaults without changing the underlying retrieval pipeline. Control Tower still owns which provider/model-pack strategy fields remain required versus optional in the settled Phase 12 contract.
When the caller provides a `workspace_id`, task-brief compilation can resolve those defaults from the selected workspace model pack or the workspace binding.
