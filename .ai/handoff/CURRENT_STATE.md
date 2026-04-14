# Current State

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- `v0.2.0` is released.
- Phase 12 Sprint 1 (`P12-S1`) is shipped.
- Phase 12 Sprint 2 (`P12-S2`) is shipped.
- Phase 12 Sprint 3 (`P12-S3`) is shipped.
- Phase 12 Sprint 4 (`P12-S4`) is the active execution sprint.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The codebase already includes semantic retrieval, embeddings, entities/entity edges, trusted-fact promotion, retrieval evaluation fixtures, deterministic resumption briefs, daily briefs, chief-of-staff briefing flows, and the shipped `P12-S1` hybrid retrieval/reranking foundation with retrieval traces.
- The codebase also includes the shipped `P12-S2` memory mutation candidate and operation foundation.

## Not Yet First-Class In Repo
- task-adaptive brief compiler separated from current briefing surfaces

## Phase Transition Note
- Phase 12 is active.
- `P12-S1` is complete and establishes the retrieval baseline.
- `P12-S2` is complete and establishes the mutation baseline.
- `P12-S3` is complete and establishes the contradiction/trust baseline.
- `P12-S4` is the active sprint and should benchmark shipped retrieval, mutation, and contradiction behavior without reopening those systems.
- The current `P12-S4` branch implements the public eval harness, fixture catalog, and checked-in baseline artifact, pending Control Tower merge approval.

## Immediate Control Tower Decisions Needed
- Decide public eval suite taxonomy and baseline artifact format.
- Decide what eval artifacts are committed versus generated locally.
- Decide whether `P12-S4` stays CLI-first or keeps the current branch `/v1/evals/*` API surface.
