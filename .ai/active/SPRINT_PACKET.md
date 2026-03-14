# SPRINT_PACKET.md

## Sprint Title

Sprint 5F: Artifact Chunk Compile Integration V0

## Sprint Type

feature

## Sprint Reason

Milestone 5 now has deterministic workspace boundaries, explicit artifact records, local text-artifact ingestion, and lexical chunk retrieval. The next safe step is to make those retrieved chunks available to the existing context compiler so document-aware responses can build on durable artifact data instead of isolated read APIs.

## Sprint Intent

Extend the existing context-compile path so it can optionally retrieve and include relevant artifact chunks using the shipped lexical artifact-chunk retrieval seam, without yet adding embeddings, semantic retrieval, Gmail/Calendar connectors, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5f-artifact-chunk-compile-integration-v0`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration.
- Sprint 5D shipped deterministic local artifact ingestion into durable chunk rows.
- Sprint 5E shipped deterministic lexical retrieval over those chunk rows.
- The next narrow Milestone 5 seam is compile-path integration of those persisted chunk results only, so document-aware context can land without jumping into semantic retrieval, connector work, or richer parsing.

## In Scope

- Define typed contracts for:
  - optional artifact-retrieval input on compile requests
  - artifact-chunk result items inside the compiled context pack
  - artifact-retrieval summary metadata inside compile responses
  - artifact-retrieval trace payloads
- Extend the compile path so it can:
  - accept an explicit artifact retrieval request scoped to one visible task or one visible artifact
  - reuse the existing lexical artifact-chunk retrieval seam
  - include retrieved artifact chunks in a separate context-pack section
  - record artifact chunk include/exclude decisions in `trace_events`
  - preserve deterministic output for the same stored data and inputs
- Ensure compile behavior:
  - leaves current continuity, memory, entity, and other context sections intact
  - does not merge artifact chunks with memory/entity sections
  - excludes non-ingested artifacts
  - scopes strictly by user ownership
  - uses deterministic ordering and explicit per-section limits
- Add unit and integration tests for:
  - compile request validation for artifact retrieval input
  - deterministic artifact-chunk section ordering
  - exclusion of non-ingested artifacts
  - trace logging for included and excluded artifact chunks
  - per-user isolation through the compile path
  - response-shape stability for the new artifact-chunk section

## Out of Scope

- No embeddings for artifact chunks.
- No semantic retrieval or reranking for artifact chunks.
- No compile-path merge between artifact chunks and memory/entity sections.
- No PDF, DOCX, OCR, or rich document parsing beyond the already-shipped text ingestion seam.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Stable compile-request and compile-response contract updates for artifact chunk retrieval input and output.
- Compile-path integration with the existing lexical artifact-chunk retrieval seam.
- Trace coverage for artifact retrieval decisions inside compile runs.
- Unit and integration coverage for compile-path artifact behavior, ordering, exclusion rules, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- `POST /v0/context/compile` can optionally accept artifact retrieval input and return a separate artifact-chunk section in the context pack.
- Compile-path artifact retrieval uses only durable `task_artifact_chunks` rows already persisted in the repo.
- Non-ingested artifacts are excluded from compile-path artifact results.
- Artifact include/exclude decisions are persisted in `trace_events`.
- Result ordering is deterministic within the artifact-chunk section.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No embeddings, semantic retrieval, connector, runner, UI, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep compile integration narrow and boring.
- Reuse the existing artifact retrieval seam; do not read raw files during compile.
- Keep artifact chunks in a separate response section from memory/entity context.
- Do not introduce semantic retrieval, embeddings, or ranking in this sprint.
- Keep scope explicit: one task or one artifact retrieval scope per compile request.

## Suggested Work Breakdown

1. Define compile contract updates for optional artifact retrieval input and output.
2. Integrate the existing lexical artifact-chunk retrieval seam into the compile path.
3. Add artifact result summaries and trace-event payloads.
4. Preserve current context sections while adding a separate artifact-chunk section.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact compile contract changes introduced
- the artifact retrieval matching and ordering rule used
- exact commands run
- unit and integration test results
- one example compile request and response showing the artifact-chunk section
- one example of artifact-retrieval trace events inside one compile run
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to compile-path artifact chunk integration
- artifact retrieval reuses durable chunk rows and the existing lexical retrieval seam
- ordering, exclusion rules, trace visibility, and isolation are test-backed
- no hidden embeddings, semantic retrieval, connector, runner, UI, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can optionally include retrieved artifact chunks inside `POST /v0/context/compile`, trace those inclusion decisions, and verify the full path with Postgres-backed tests, while still deferring semantic retrieval, embeddings, connector work, and UI.
