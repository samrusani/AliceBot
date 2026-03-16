# SPRINT_PACKET.md

## Sprint Title

Sprint 5M: DOCX Artifact Parsing V0

## Sprint Type

feature

## Sprint Reason

Sprint 5L proved the richer-document-parsing seam can widen safely without changing the rooted workspace, durable chunk, retrieval, or compile contracts. The next safe slice is DOCX ingestion only, not broader PDF compatibility, OCR, connectors, or UI.

## Sprint Intent

Extend the existing artifact-ingestion seam so registered DOCX artifacts can be ingested into the existing durable `task_artifact_chunks` substrate through deterministic local text extraction, without changing retrieval contracts, compile contracts, connectors, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5m-docx-artifact-parsing-v0`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration.
- Sprint 5D shipped deterministic local text-artifact ingestion into durable chunk rows.
- Sprint 5E through 5J shipped lexical retrieval, semantic retrieval, and hybrid compile-path artifact retrieval on top of those persisted chunk rows.
- Sprint 5L extended the same ingestion seam to narrow PDF text extraction without changing retrieval or compile contracts.
- The next narrow richer-document move is a separate DOCX ingestion seam, which increases format coverage without widening into OCR, connector, or UI scope.

## In Scope

- Extend schema and contracts only as narrowly needed to support DOCX ingestion metadata, for example:
  - `task_artifacts.ingestion_status` reuse if no new status is required
  - optional deterministic extraction metadata on artifact detail or ingestion responses if needed
- Define typed contracts for:
  - DOCX artifact-ingestion requests if they differ from the current generic artifact-ingestion path
  - artifact-ingestion responses updated for DOCX extraction metadata if needed
  - artifact detail or chunk summary metadata updated for DOCX ingestion if needed
- Extend the existing ingestion seam so it:
  - accepts already-registered visible DOCX artifacts
  - resolves rooted local file paths from persisted workspace plus artifact relative path
  - supports one explicit DOCX extraction path only
  - extracts deterministic text from DOCX package contents without OCR or image extraction
  - normalizes extracted text before chunking
  - persists ordered chunk rows into the existing `task_artifact_chunks` table
  - updates artifact ingestion status deterministically
- Add unit and integration tests for:
  - supported DOCX ingestion
  - deterministic chunk ordering and chunk boundaries from extracted DOCX text
  - rooted path enforcement during DOCX ingestion
  - rejection of malformed or textless DOCX files when no extractable text is present
  - per-user isolation
  - stable response shape

## Out of Scope

- No broader PDF compatibility work.
- No OCR.
- No image extraction from DOCX.
- No changes to lexical retrieval contracts.
- No changes to semantic retrieval contracts.
- No compile contract changes.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Narrow ingestion support for visible DOCX artifacts using the existing artifact and chunk seams.
- Stable contract updates only where DOCX extraction metadata is necessary.
- Unit and integration coverage for DOCX extraction, rooted-path safety, deterministic chunk persistence, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can ingest one supported visible DOCX artifact into durable ordered chunk rows using the existing artifact-ingestion seam.
- DOCX ingestion reads only files rooted under the persisted task workspace boundary.
- Extracted text is normalized and chunked deterministically into the existing `task_artifact_chunks` contract.
- Malformed or textless DOCX files are rejected deterministically rather than silently producing misleading chunks.
- Existing lexical, semantic, and hybrid artifact retrieval contracts continue to operate over the persisted chunk rows without contract changes.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No PDF-compatibility expansion, OCR, connector, runner, compile-contract, or UI scope enters the sprint.

## Implementation Constraints

- Keep richer parsing narrow and boring.
- Reuse the existing rooted `task_workspaces`, `task_artifacts`, and `task_artifact_chunks` seams rather than creating a parallel document store.
- Support DOCX text extraction only; do not introduce OCR, image extraction, or document-layout reconstruction in the same sprint.
- Preserve existing retrieval and compile contracts by feeding the already-shipped chunk substrate.
- Keep extraction and chunking deterministic and testable from local files alone.

## Suggested Work Breakdown

1. Define any minimal DOCX-ingestion contract updates needed.
2. Implement deterministic rooted DOCX text extraction in the existing artifact-ingestion seam.
3. Normalize extracted text and persist ordered chunk rows into the existing chunk store.
4. Add deterministic failure behavior for malformed or textless DOCX files.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact DOCX-ingestion contract changes introduced, if any
- the DOCX extraction path and chunking rule used
- exact commands run
- unit and integration test results
- one example DOCX artifact-ingestion response
- one example chunk list response produced from a DOCX artifact
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to DOCX artifact parsing through the existing ingestion seam
- DOCX ingestion reuses the existing rooted workspace, artifact, and chunk contracts
- extraction determinism, chunk ordering, rooted-path safety, and isolation are test-backed
- no hidden PDF-compatibility expansion, OCR, connector, runner, compile-contract, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the repo can ingest supported visible DOCX artifacts into deterministic durable chunk rows through the existing artifact-ingestion seam, verify the full path with Postgres-backed tests, and still defer broader document parsing, connectors, and UI.
