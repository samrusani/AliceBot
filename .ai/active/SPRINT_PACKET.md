# SPRINT_PACKET.md

## Sprint Title

Sprint 5E: Artifact Chunk Retrieval V0

## Sprint Type

feature

## Sprint Reason

Milestone 5 now has deterministic workspace boundaries, explicit artifact records, and durable chunk ingestion. The next safe step is to retrieve those ingested chunks through a narrow deterministic read path before adding embeddings, ranking, rich-document parsing, connectors, or UI.

## Sprint Intent

Add a narrow retrieval seam over existing `task_artifact_chunks` so clients can request relevant ingested text chunks for one task or artifact using deterministic lexical matching only, without yet adding embeddings, compile-path integration, connectors, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5e-artifact-chunk-retrieval-v0`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A established rooted task-workspace provisioning.
- Sprint 5C established explicit task-artifact registration.
- Sprint 5D established deterministic local text-artifact ingestion into durable chunk rows.
- The next narrow Milestone 5 seam is retrieval over those persisted chunks only, so later document-aware context work can build on a stable read contract instead of raw file access.

## In Scope

- Define typed contracts for:
  - artifact-chunk retrieval requests
  - artifact-chunk retrieval result items
  - retrieval summary metadata
- Implement a narrow retrieval seam that:
  - searches only durable `task_artifact_chunks`
  - scopes retrieval by the current user plus one explicit task or one explicit artifact
  - accepts one explicit text query
  - uses deterministic lexical matching only
  - returns deterministic ordered chunk results with explicit match metadata
  - excludes artifacts that are not yet ingested
- Implement the minimal API or service paths needed for:
  - retrieving chunks for one task
  - retrieving chunks for one artifact when the caller wants a narrower scope
- Add unit and integration tests for:
  - deterministic retrieval ordering
  - scoped retrieval by task and by artifact
  - empty-result behavior
  - exclusion of non-ingested artifacts
  - per-user isolation
  - stable response shape

## Out of Scope

- No embeddings for artifact chunks.
- No semantic retrieval or reranking.
- No compile-path integration of artifact chunks yet.
- No PDF, DOCX, OCR, or rich document parsing beyond the already-shipped text ingestion seam.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Stable chunk-retrieval request and response contracts.
- Minimal deterministic lexical retrieval path over existing `task_artifact_chunks`.
- Unit and integration coverage for ordering, scoping, exclusion rules, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can retrieve relevant ingested chunk records for one visible task using one explicit text query.
- A client can retrieve relevant ingested chunk records for one visible artifact using one explicit text query.
- Retrieval uses only durable `task_artifact_chunks` rows already persisted in the repo.
- Retrieval excludes artifacts whose ingestion is not complete.
- Result ordering is deterministic and documented.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No embeddings, semantic retrieval, compile integration, connector, runner, UI, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep retrieval narrow and boring.
- Reuse existing task-artifact and chunk seams; do not read raw files during retrieval.
- Use deterministic lexical matching only in this sprint.
- Keep scope explicit: one task or one artifact per request.
- Do not merge artifact-chunk retrieval into the main context compiler in the same sprint.

## Suggested Work Breakdown

1. Define chunk-retrieval request and response contracts.
2. Implement deterministic lexical matching over existing chunk rows.
3. Add explicit task-scoped and artifact-scoped retrieval paths.
4. Enforce exclusion of non-ingested artifacts and current-user isolation.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact retrieval contracts introduced
- the lexical matching rule and ordering rule used
- exact commands run
- unit and integration test results
- one example task-scoped retrieval response
- one example artifact-scoped retrieval response
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to artifact chunk retrieval over durable chunk rows
- retrieval is deterministic, lexical-only, and scope-limited to one task or one artifact
- ordering, exclusion rules, and isolation are test-backed
- no hidden embeddings, semantic retrieval, compile integration, connector, runner, UI, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can retrieve relevant ingested artifact chunks through a deterministic lexical read path scoped to one task or one artifact, verify the full path with Postgres-backed tests, and still defer semantic retrieval, compile integration, and connector work.
