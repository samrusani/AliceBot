# Current State

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- `v0.2.0` is released.
- Phase 12 Sprint 1 (`P12-S1`) is shipped.
- Phase 12 Sprint 2 (`P12-S2`) is shipped.
- Phase 12 Sprint 3 (`P12-S3`) is the active execution sprint.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The codebase already includes semantic retrieval, embeddings, entities/entity edges, trusted-fact promotion, retrieval evaluation fixtures, deterministic resumption briefs, daily briefs, chief-of-staff briefing flows, and the shipped `P12-S1` hybrid retrieval/reranking foundation with retrieval traces.
- The codebase also includes the shipped `P12-S2` memory mutation candidate and operation foundation.

## Not Yet First-Class In Repo
- public multi-suite eval harness for recall/resumption/correction/contradiction/open-loops
- task-adaptive brief compiler separated from current briefing surfaces

## Phase Transition Note
- Phase 12 is active.
- `P12-S1` is complete and establishes the retrieval baseline.
- `P12-S2` is complete and establishes the mutation baseline.
- `P12-S3` is the active sprint and should build contradiction and trust handling on top of shipped retrieval and mutation behavior.
- The current `P12-S3` branch implements contradiction cases and trust-signal storage, pending Control Tower merge approval.

## Immediate Control Tower Decisions Needed
- Decide contradiction object attachment scope: continuity objects, memories, or both.
- Decide trust-signal storage and ranking integration policy.
- Decide the final contradiction and trust API surface shape for Phase 12.
