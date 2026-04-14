# Current State

This file is a synced repo-root copy for planning visibility.
Canonical handoff state lives at [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md).

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- `v0.2.0` is released.
- Phase 12 Sprint 1 (`P12-S1`) is shipped.
- Phase 12 Sprint 2 (`P12-S2`) is shipped.
- Phase 12 Sprint 3 (`P12-S3`) is shipped.
- Phase 12 Sprint 4 (`P12-S4`) is shipped.
- Phase 12 Sprint 5 (`P12-S5`) is the active execution sprint.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The codebase already includes semantic retrieval, embeddings, entities/entity edges, trusted-fact promotion, retrieval evaluation fixtures, deterministic resumption briefs, daily briefs, chief-of-staff briefing flows, and the shipped `P12-S1` hybrid retrieval/reranking foundation with retrieval traces.
- The codebase also includes the shipped `P12-S2` memory mutation candidate and operation foundation, the shipped `P12-S3` contradiction/trust foundation, and the shipped `P12-S4` public eval harness.

## Not Yet First-Class In Repo

## Phase Transition Note
- Phase 12 is active.
- `P12-S1` is complete and establishes the retrieval baseline.
- `P12-S2` is complete and establishes the mutation baseline.
- `P12-S3` is complete and establishes the contradiction/trust baseline.
- `P12-S4` is complete and establishes the public-eval baseline.
- `P12-S5` is the active sprint and should build briefing behavior on top of shipped retrieval, mutation, contradiction, and eval baselines without reopening those systems.
- The current `P12-S5` branch implements task-adaptive brief generation, comparison, and model-pack briefing defaults, pending Control Tower merge approval.

## Immediate Control Tower Decisions Needed
- Decide briefing modes and payload schema for user recall, resume, worker subtask, and agent handoff.
- Decide provider/model-pack fields for briefing strategy and max brief tokens.
- Decide whether `P12-S5` needs CLI-only, API, and MCP surfaces simultaneously or can stage them.
