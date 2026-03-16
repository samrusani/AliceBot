# SPRINT_PACKET.md

## Sprint Title

Sprint 5J: Deterministic Hybrid Artifact Merge in Context Compilation

## Sprint Type

feature

## Sprint Reason

Milestone 5 now has compile-path lexical artifact retrieval and compile-path semantic artifact retrieval as separate sections. The next safe step is to merge those two existing artifact candidate paths into one governed compile-time artifact section with explicit deterministic deduplication and provenance rules, while still deferring reranking, connectors, and UI.

## Sprint Intent

Complete the first hybrid artifact retrieval slice by merging the already-implemented lexical and semantic artifact chunk candidate sets inside `POST /v0/context/compile`, using explicit deterministic deduplication and selection rules without adding reranking or model-driven embedding generation.

## Git Instructions

- Branch Name: `codex/sprint-5j-hybrid-artifact-merge`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration.
- Sprint 5D shipped deterministic local artifact ingestion into durable chunk rows.
- Sprint 5E shipped lexical artifact-chunk retrieval.
- Sprint 5F shipped compile-path lexical artifact chunk inclusion.
- Sprint 5G shipped durable artifact-chunk embedding persistence.
- Sprint 5H shipped direct semantic artifact retrieval.
- Sprint 5I shipped compile-path semantic artifact retrieval as a separate context section.
- The next narrow Milestone 5 seam is deterministic hybrid artifact merge, so compile can return one governed artifact section before any reranking or richer document behavior is introduced.

## In Scope

- Define typed contracts for:
  - hybrid artifact chunk items in the compiled context pack
  - source provenance metadata for each included artifact chunk
  - hybrid artifact retrieval summary metadata
  - hybrid artifact retrieval trace payloads
- Extend the compile path so it can:
  - gather the existing lexical artifact chunk candidates
  - optionally gather the existing semantic artifact chunk candidates
  - merge both candidate sets into one artifact section
  - deduplicate by durable artifact chunk identity
  - preserve source provenance when a chunk is selected by both paths
  - apply explicit deterministic selection rules and limits
  - record hybrid include/exclude and deduplication decisions in `trace_events`
- Define explicit merge behavior, for example:
  - lexical-first precedence when both sources compete for the same limit budget
  - stable tie-breaking after source precedence
  - predictable handling when a chunk appears in both candidate sets
- Ensure compile behavior:
  - excludes non-ingested artifacts
  - scopes strictly by user ownership
  - remains deterministic for the same stored data and inputs
  - leaves memory, entity, and non-artifact sections unchanged
- Add unit and integration tests for:
  - deterministic merge ordering
  - deduplication behavior
  - dual-source provenance behavior
  - limit enforcement across merged artifact candidates
  - exclusion of non-ingested artifacts
  - per-user isolation through the compile path
  - response-shape stability for the merged artifact section

## Out of Scope

- No reranking across merged artifact candidates.
- No weighted or learned fusion logic.
- No model or external API calls to generate query embeddings.
- No richer document parsing beyond the already-shipped local text ingestion seam.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Stable compile-response contract updates for merged hybrid artifact output.
- Deterministic hybrid merge logic over the existing lexical and semantic artifact retrieval paths.
- Trace coverage for merge, deduplication, and exclusion decisions.
- Unit and integration coverage for hybrid artifact behavior, ordering, validation, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- `POST /v0/context/compile` can return one merged artifact section derived from the existing lexical and semantic artifact retrieval paths.
- The merged section deduplicates artifact chunks by durable identity and preserves source provenance.
- Merge behavior uses explicit deterministic rules and limits.
- Non-ingested artifacts are excluded from the merged section.
- Hybrid artifact merge decisions are persisted in `trace_events`.
- Result ordering is deterministic for the same stored data and inputs.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No reranking, connector, runner, UI, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep hybrid artifact behavior narrow and boring.
- Reuse the existing lexical and semantic artifact retrieval seams rather than introducing a third retrieval stack.
- Make source precedence explicit in contracts, code, and tests.
- Do not introduce weighted scoring, reranking, or learned fusion in this sprint.
- Keep memory, entity, and non-artifact sections unchanged.

## Suggested Work Breakdown

1. Define hybrid artifact output and trace contracts.
2. Implement deterministic merge and deduplication over existing lexical and semantic artifact candidates.
3. Add source provenance and hybrid summary metadata.
4. Record hybrid merge decisions in `trace_events`.
5. Preserve existing retrieval seams while returning one merged artifact section.
6. Add unit and integration tests.
7. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact hybrid artifact merge contract changes introduced
- the merge precedence and deduplication rule used
- exact commands run
- unit and integration test results
- one example compile request and response showing merged artifact output
- one example of hybrid artifact retrieval trace events inside one compile run
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to deterministic hybrid artifact merge in the compile path
- hybrid artifact behavior reuses the existing lexical and semantic retrieval seams
- merge ordering, deduplication, provenance, exclusion rules, trace visibility, and isolation are deterministic and test-backed
- no hidden reranking, connector, runner, UI, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can return one deterministic merged artifact section in `POST /v0/context/compile`, derived from the existing lexical and semantic artifact retrieval paths with trace-visible merge decisions and passing Postgres-backed tests, while still deferring reranking, connectors, and UI.
