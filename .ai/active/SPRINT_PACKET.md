# SPRINT_PACKET.md

## Sprint Title

Sprint 5D: Local Artifact Ingestion V0

## Sprint Type

feature

## Sprint Reason

Milestone 5 now has deterministic task-workspace boundaries and explicit task-artifact records. The next safe step is to ingest registered local artifacts into durable chunk records, so later document retrieval can operate on explicit ingested data instead of raw filesystem reads.

## Sprint Intent

Add a narrow, explicit local artifact-ingestion seam that reads registered text artifacts from rooted task workspaces, chunks them deterministically, and persists durable artifact-chunk records, without yet adding document retrieval, embeddings, connectors, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5d-artifact-ingestion-v0`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration on top of those workspaces.
- The roadmap says document work should build on the existing artifact/workspace boundary.
- The narrowest next step is ingestion only: turn registered local artifacts into durable chunk records before any retrieval or connector work begins.

## In Scope

- Add schema and migration support for:
  - `task_artifact_chunks`
  - any narrow `task_artifacts.ingestion_status` expansion required to represent successful ingestion deterministically
- Define typed contracts for:
  - artifact-ingestion requests
  - artifact-ingestion responses
  - artifact-chunk list responses
  - artifact detail responses updated for ingestion status if needed
- Implement a narrow ingestion seam that:
  - accepts one already-registered visible artifact
  - resolves its rooted local file path from the persisted workspace boundary plus artifact relative path
  - supports only a small explicit text input set, for example `text/plain` and `text/markdown`
  - reads file contents deterministically
  - normalizes line endings and chunks text deterministically by one explicit rule
  - persists ordered chunk rows linked to the artifact
  - updates artifact ingestion status deterministically
- Implement the minimal API or service paths needed for:
  - ingesting one artifact
  - listing chunks for one artifact
- Add unit and integration tests for:
  - supported text artifact ingestion
  - deterministic chunk ordering and chunk content boundaries
  - rooted path enforcement during ingestion
  - unsupported media-type or file-shape rejection
  - per-user isolation
  - stable response shape

## Out of Scope

- No compile-path or search retrieval over artifact chunks yet.
- No embeddings for artifact chunks.
- No document ranking or chunk selection.
- No PDF, DOCX, OCR, or rich document parsing beyond the narrow supported text set.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Migration for `task_artifact_chunks` and any narrow ingestion-status update.
- Stable artifact-ingestion and artifact-chunk read contracts.
- Minimal deterministic local artifact-ingestion path over registered task artifacts.
- Unit and integration coverage for rooted-path safety, supported-format ingestion, chunk ordering, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can ingest one supported registered local artifact into durable ordered chunk records.
- Ingestion reads only files rooted under the persisted task workspace boundary.
- Chunking behavior is deterministic and documented.
- Unsupported artifact types are rejected deterministically.
- Artifact chunk reads are deterministic and user-scoped.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No retrieval, embeddings, connector, runner, UI, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep ingestion narrow and boring.
- Reuse existing `task_workspaces` and `task_artifacts` boundaries; do not scan directories implicitly.
- Support only a small explicit text-artifact set in this sprint.
- Keep chunking deterministic and simple enough to test precisely.
- Do not introduce retrieval or embedding behavior in the same sprint.

## Suggested Work Breakdown

1. Add `task_artifact_chunks` schema and migration.
2. Define ingestion and chunk-read contracts.
3. Implement deterministic rooted file resolution from artifact metadata.
4. Implement narrow supported-format ingestion and deterministic chunk persistence.
5. Implement artifact chunk list reads.
6. Add unit and integration tests.
7. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact chunk schema and ingestion contract changes introduced
- the supported file types and chunking rule used
- exact commands run
- unit and integration test results
- one example artifact-ingestion response
- one example artifact-chunk list response
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to local artifact ingestion and chunk persistence
- ingestion reuses explicit task-workspace and artifact records rather than filesystem scanning
- rooted-path safety, chunk determinism, ordering, and isolation are test-backed
- no hidden retrieval, embedding, connector, runner, UI, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can ingest supported registered local artifacts into deterministic durable chunk records, expose stable chunk reads, and verify the full path with Postgres-backed tests, while still deferring document retrieval, embeddings, and connector work.
