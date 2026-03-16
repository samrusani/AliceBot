# SPRINT_PACKET.md

## Sprint Title

Sprint 5N: RFC822 Email Artifact Parsing V0

## Sprint Type

feature

## Sprint Reason

Sprint 5L and Sprint 5M proved the richer-document-parsing seam can widen safely without changing the rooted workspace, durable chunk, retrieval, or compile contracts. The next safe slice is RFC822 email ingestion only, which prepares the path for later read-only Gmail work without opening live connector, auth, or UI scope yet.

## Sprint Intent

Extend the existing artifact-ingestion seam so registered RFC822 email artifacts can be ingested into the existing durable `task_artifact_chunks` substrate through deterministic local parsing of message headers and text bodies, without changing retrieval contracts, compile contracts, live connector scope, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5n-rfc822-email-artifact-parsing-v0`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration.
- Sprint 5D shipped deterministic local text-artifact ingestion into durable chunk rows.
- Sprint 5E through 5J shipped lexical retrieval, semantic retrieval, and hybrid compile-path artifact retrieval on top of those persisted chunk rows.
- Sprint 5L extended the same ingestion seam to narrow PDF text extraction.
- Sprint 5M extended the same ingestion seam to narrow DOCX text extraction.
- The next narrow richer-document move is RFC822 email parsing, which advances the Gmail-adjacent path while still staying on the existing rooted artifact and chunk substrate instead of opening a live connector.

## In Scope

- Extend schema and contracts only as narrowly needed to support RFC822 ingestion metadata, for example:
  - `task_artifacts.ingestion_status` reuse if no new status is required
  - optional deterministic extraction metadata on artifact detail or ingestion responses if needed
- Define typed contracts for:
  - email artifact-ingestion requests if they differ from the current generic artifact-ingestion path
  - artifact-ingestion responses updated for email extraction metadata if needed
  - artifact detail or chunk summary metadata updated for email ingestion if needed
- Extend the existing ingestion seam so it:
  - accepts already-registered visible RFC822 email artifacts
  - resolves rooted local file paths from persisted workspace plus artifact relative path
  - supports one explicit local email parsing path only
  - parses deterministic text from message headers plus plain-text body parts
  - handles multipart messages narrowly and predictably
  - rejects unsupported body forms when no extractable text body is present
  - normalizes extracted text before chunking
  - persists ordered chunk rows into the existing `task_artifact_chunks` table
  - updates artifact ingestion status deterministically
- Add unit and integration tests for:
  - supported RFC822 ingestion
  - deterministic chunk ordering and chunk boundaries from extracted email text
  - rooted path enforcement during email ingestion
  - rejection of malformed or textless email artifacts when no extractable text is present
  - per-user isolation
  - stable response shape

## Out of Scope

- No live Gmail API or OAuth work.
- No Calendar connector scope.
- No HTML-to-text rendering beyond a narrow explicit rule if strictly needed.
- No attachment extraction.
- No OCR.
- No changes to lexical retrieval contracts.
- No changes to semantic retrieval contracts.
- No compile contract changes.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Narrow ingestion support for visible RFC822 email artifacts using the existing artifact and chunk seams.
- Stable contract updates only where email extraction metadata is necessary.
- Unit and integration coverage for email extraction, rooted-path safety, deterministic chunk persistence, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can ingest one supported visible RFC822 email artifact into durable ordered chunk rows using the existing artifact-ingestion seam.
- Email ingestion reads only files rooted under the persisted task workspace boundary.
- Extracted email text is normalized and chunked deterministically into the existing `task_artifact_chunks` contract.
- Malformed or textless email artifacts are rejected deterministically rather than silently producing misleading chunks.
- Existing lexical, semantic, and hybrid artifact retrieval contracts continue to operate over the persisted chunk rows without contract changes.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No live Gmail connector, Calendar connector, OAuth, attachment extraction, compile-contract, runner, or UI scope enters the sprint.

## Implementation Constraints

- Keep richer parsing narrow and boring.
- Reuse the existing rooted `task_workspaces`, `task_artifacts`, and `task_artifact_chunks` seams rather than creating a parallel email store.
- Support deterministic local RFC822 parsing only; do not introduce live connector behavior in the same sprint.
- Prefer plain-text body extraction; if multipart handling is needed, keep the accepted body selection rule explicit and deterministic.
- Preserve existing retrieval and compile contracts by feeding the already-shipped chunk substrate.

## Suggested Work Breakdown

1. Define any minimal RFC822-ingestion contract updates needed.
2. Implement deterministic rooted email parsing in the existing artifact-ingestion seam.
3. Normalize extracted email text and persist ordered chunk rows into the existing chunk store.
4. Add deterministic failure behavior for malformed or textless email artifacts.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact RFC822-ingestion contract changes introduced, if any
- the email extraction path and chunking rule used
- the header/body selection rule used
- exact commands run
- unit and integration test results
- one example email artifact-ingestion response
- one example chunk list response produced from an email artifact
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to RFC822 email artifact parsing through the existing ingestion seam
- email ingestion reuses the existing rooted workspace, artifact, and chunk contracts
- extraction determinism, chunk ordering, rooted-path safety, and isolation are test-backed
- no hidden live Gmail connector, Calendar connector, OAuth, attachment extraction, compile-contract, runner, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the repo can ingest supported visible RFC822 email artifacts into deterministic durable chunk rows through the existing artifact-ingestion seam, verify the full path with Postgres-backed tests, and still defer live connector work, broader email handling, and UI.
