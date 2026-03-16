# SPRINT_PACKET.md

## Sprint Title

Sprint 5L: PDF Artifact Parsing V0

## Sprint Type

feature

## Sprint Reason

Sprint 5K re-synchronized project truth through Sprint 5J, and the agreed next delivery focus is richer document parsing on top of the shipped rooted workspace, durable chunk, and hybrid artifact compile baseline. The narrowest safe next slice is PDF ingestion only, not a broad “rich documents” sprint that mixes PDF, DOCX, OCR, connectors, or UI.

## Sprint Intent

Extend the existing artifact-ingestion seam so registered PDF artifacts can be ingested into the existing durable `task_artifact_chunks` substrate through deterministic text extraction, without changing retrieval contracts, compile contracts, connectors, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5l-pdf-artifact-parsing-v0`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration.
- Sprint 5D shipped deterministic local text-artifact ingestion into durable chunk rows.
- Sprint 5E through 5J shipped lexical retrieval, semantic retrieval, and hybrid compile-path artifact retrieval on top of those persisted chunk rows.
- Sprint 5K re-synchronized the truth artifacts and explicitly set richer document parsing as the next narrow move.
- The safest next step is PDF extraction only, feeding the already-shipped chunk and retrieval seams without expanding into OCR, DOCX, connectors, or UI.

## In Scope

- Extend schema and contracts only as narrowly needed to support PDF ingestion metadata, for example:
  - `task_artifacts.ingestion_status` reuse if no new status is required
  - optional deterministic extraction metadata on artifact detail or ingestion responses if needed
- Define typed contracts for:
  - PDF artifact-ingestion requests if they differ from the current generic artifact-ingestion path
  - artifact-ingestion responses updated for PDF extraction metadata if needed
  - artifact detail or chunk summary metadata updated for PDF ingestion if needed
- Extend the existing ingestion seam so it:
  - accepts already-registered visible PDF artifacts
  - resolves rooted local file paths from persisted workspace plus artifact relative path
  - supports one explicit PDF extraction path only
  - extracts deterministic text from PDFs without OCR
  - normalizes extracted text before chunking
  - persists ordered chunk rows into the existing `task_artifact_chunks` table
  - updates artifact ingestion status deterministically
- Add unit and integration tests for:
  - supported PDF ingestion
  - deterministic chunk ordering and chunk boundaries from extracted PDF text
  - rooted path enforcement during PDF ingestion
  - rejection of scanned-image or textless PDFs when no extractable text is present
  - per-user isolation
  - stable response shape

## Out of Scope

- No DOCX ingestion.
- No OCR.
- No image extraction.
- No changes to lexical retrieval contracts.
- No changes to semantic retrieval contracts.
- No compile contract changes.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Narrow ingestion support for visible PDF artifacts using the existing artifact and chunk seams.
- Stable contract updates only where PDF extraction metadata is necessary.
- Unit and integration coverage for PDF extraction, rooted-path safety, deterministic chunk persistence, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can ingest one supported visible PDF artifact into durable ordered chunk rows using the existing artifact-ingestion seam.
- PDF ingestion reads only files rooted under the persisted task workspace boundary.
- Extracted text is normalized and chunked deterministically into the existing `task_artifact_chunks` contract.
- Textless or unsupported PDFs are rejected deterministically rather than silently producing misleading chunks.
- Existing lexical, semantic, and hybrid artifact retrieval contracts continue to operate over the persisted chunk rows without contract changes.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No DOCX, OCR, connector, runner, compile-contract, or UI scope enters the sprint.

## Implementation Constraints

- Keep richer parsing narrow and boring.
- Reuse the existing rooted `task_workspaces`, `task_artifacts`, and `task_artifact_chunks` seams rather than creating a parallel document store.
- Support PDF text extraction only; do not introduce OCR fallback in the same sprint.
- Preserve existing retrieval and compile contracts by feeding the already-shipped chunk substrate.
- Keep extraction and chunking deterministic and testable from local files alone.

## Suggested Work Breakdown

1. Define any minimal PDF-ingestion contract updates needed.
2. Implement deterministic rooted PDF text extraction in the existing artifact-ingestion seam.
3. Normalize extracted text and persist ordered chunk rows into the existing chunk store.
4. Add deterministic failure behavior for textless PDFs.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact PDF-ingestion contract changes introduced, if any
- the PDF extraction path and chunking rule used
- exact commands run
- unit and integration test results
- one example PDF artifact-ingestion response
- one example chunk list response produced from a PDF artifact
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to PDF artifact parsing through the existing ingestion seam
- PDF ingestion reuses the existing rooted workspace, artifact, and chunk contracts
- extraction determinism, chunk ordering, rooted-path safety, and isolation are test-backed
- no hidden DOCX, OCR, connector, runner, compile-contract, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the repo can ingest supported visible PDF artifacts into deterministic durable chunk rows through the existing artifact-ingestion seam, verify the full path with Postgres-backed tests, and still defer broader document parsing, connectors, and UI.
