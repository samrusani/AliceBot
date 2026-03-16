# Roadmap

## Current Position

- The accepted repo state is current through Sprint 5J.
- Milestone 5 now ships the rooted local workspace and artifact baseline end to end: workspace provisioning, artifact registration, narrow text ingestion, durable chunk storage, lexical artifact retrieval, compile-path artifact inclusion, artifact-chunk embeddings, direct semantic artifact retrieval, compile-path semantic artifact retrieval, and deterministic hybrid lexical-plus-semantic artifact merge in compile.
- This roadmap is future-facing from that shipped baseline; historical sprint-by-sprint detail lives in accepted build and review artifacts, not here.

## Next Delivery Focus

### Open Richer Document Parsing On Top Of The Shipped Artifact Retrieval Baseline

- Extend ingestion beyond the current `text/plain` and `text/markdown` seam without changing the rooted `task_workspaces` and durable `task_artifact_chunks` contracts.
- Keep retrieval building on persisted chunk rows and persisted embeddings; new parsing work should feed the existing compile-path lexical/semantic/hybrid artifact retrieval seam rather than inventing a parallel context path.
- Keep the next sprint narrow: richer document parsing first, then reassess connectors only after the parsing seam is accepted.

### Preserve Current Compile, Governance, And Task Guarantees

- Keep approvals, execution budgets, task/task-step state, and trace visibility deterministic as Milestone 5 continues.
- Preserve the shipped compile contract of one merged artifact section with explicit source provenance, deterministic lexical-first precedence, and trace-visible inclusion and exclusion decisions.
- Do not widen the current no-external-I/O proxy surface or introduce runner, connector, or UI scope until those areas are explicitly opened.

## After The Next Narrow Sprint

- Open read-only connector work only after richer document parsing remains deterministic under the current artifact and governance seams.
- Revisit workflow UI only after backend document and connector seams are accepted and the truth artifacts stay current.
- Revisit broader task orchestration only after the current explicit task-step seams remain stable under workspace, artifact, document, and connector flows.
- Continue to defer broader tool execution breadth and production auth/deployment hardening until the current governed surface remains stable.

## Dependencies

- Live truth docs must stay synchronized with accepted repo state so sprint planning does not start from stale assumptions.
- Rich document parsing should build on the shipped rooted local workspace, durable artifact chunk, and hybrid compile retrieval contracts.
- Connector work should remain read-only, approval-aware, and downstream of the document parsing seam.
- Runner-style orchestration should stay deferred until the repo no longer depends on narrow current-step assumptions for safety and explainability.

## Ongoing Risks

- Memory extraction and retrieval quality remain the largest product risk.
- Auth beyond database user context is still missing.
- Milestone 5 can drift if richer document parsing, connectors, UI, and orchestration work are mixed into one sprint instead of landing as narrow seams on top of the shipped artifact retrieval baseline.
