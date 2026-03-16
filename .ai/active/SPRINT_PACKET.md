# SPRINT_PACKET.md

## Sprint Title

Sprint 5O: Read-Only Gmail Connection and Single-Message Ingestion V0

## Sprint Type

feature

## Sprint Reason

Sprint 5N proved the Gmail-adjacent document seam locally by ingesting RFC822 email artifacts into the existing chunk substrate. The next safe step is the first live read-only Gmail slice, but only enough to connect one account and ingest one visible Gmail message through that same RFC822-to-chunk seam. This opens connector work without collapsing into search, sync, Calendar, UI, or write-capable behavior.

## Sprint Intent

Add the first live read-only Gmail connector seam by supporting user-scoped Gmail connection metadata plus ingestion of one selected Gmail message into the existing artifact-ingestion pipeline as an RFC822-style artifact, without adding write actions, background sync, Calendar, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5o-gmail-connection-single-message-ingestion`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C through 5J shipped the durable artifact, chunk, lexical, semantic, and hybrid compile substrate.
- Sprint 5N shipped narrow local RFC822 parsing on that same artifact-ingestion seam.
- The product brief requires read-only Gmail connectors in v1.
- The narrowest safe connector step is not mailbox sync or UI; it is a user-scoped read-only Gmail connection plus one explicit message ingestion path that reuses the already-accepted RFC822 extraction seam.

## In Scope

- Add schema and migration support for:
  - `gmail_accounts`
- Define typed contracts for:
  - Gmail account create or connect requests
  - Gmail account list and detail responses
  - single-message Gmail ingestion requests
  - single-message Gmail ingestion responses
- Implement a narrow Gmail connector seam that:
  - stores one user-scoped read-only Gmail account connection record with only the metadata needed for later reads
  - uses one explicit Gmail read-only auth/config path only
  - fetches one selected Gmail message by explicit provider message id
  - converts that message into the existing artifact registration plus RFC822-style ingestion pipeline
  - persists the resulting artifact under one visible task workspace
  - reuses the existing `task_artifacts` and `task_artifact_chunks` contracts
  - preserves per-user isolation throughout account read and message ingestion flows
- Implement the minimal API or service paths needed for:
  - connecting one Gmail account
  - listing Gmail accounts
  - reading one Gmail account
  - ingesting one Gmail message into one visible task workspace
- Add unit and integration tests for:
  - Gmail account persistence
  - deterministic account listing
  - single-message Gmail ingestion through the existing artifact seam
  - rejection of cross-user workspace access
  - rejection of unsupported or missing Gmail messages
  - stable response shape

## Out of Scope

- No Gmail message search.
- No mailbox sync or backfill jobs.
- No attachment ingestion.
- No write-capable Gmail actions.
- No Calendar connector scope.
- No OAuth UX or web callback UI beyond the minimal backend contract needed to represent a connected account.
- No compile contract changes.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Migration for `gmail_accounts`.
- Stable contracts for Gmail account connect/list/detail and single-message ingestion.
- Minimal read-only Gmail account persistence seam.
- Minimal explicit single-message Gmail ingestion path that feeds the existing artifact and RFC822 chunk seams.
- Unit and integration coverage for persistence, isolation, ingestion routing, and response stability.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can persist one user-scoped read-only Gmail account connection record.
- A client can list and read Gmail account records deterministically.
- A client can ingest one selected Gmail message into one visible task workspace through the existing artifact-ingestion seam.
- Gmail message ingestion results in durable `task_artifacts` and `task_artifact_chunks` rows compatible with existing retrieval and compile behavior.
- Cross-user account and workspace access is rejected deterministically.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No Gmail search, mailbox sync, attachments, write actions, Calendar, compile-contract, runner, or UI scope enters the sprint.

## Implementation Constraints

- Keep connector work narrow and boring.
- Reuse the existing rooted workspace, artifact, and RFC822 chunk seams rather than creating a parallel email-content store.
- Keep Gmail handling explicitly read-only.
- Support one explicit selected-message ingestion path only; do not introduce account-wide sync or search in the same sprint.
- Preserve existing retrieval and compile contracts by feeding the already-shipped chunk substrate.

## Suggested Work Breakdown

1. Add `gmail_accounts` schema and migration.
2. Define Gmail account and single-message ingestion contracts.
3. Implement deterministic Gmail account create, list, and detail behavior.
4. Implement explicit selected-message Gmail ingestion into the existing artifact and RFC822 ingestion seam.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact Gmail account and single-message ingestion contract changes introduced
- the Gmail message-to-artifact conversion rule used
- exact commands run
- unit and integration test results
- one example Gmail account response
- one example single-message ingestion response
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to read-only Gmail connection metadata and single-message ingestion
- Gmail message ingestion reuses the existing rooted workspace, artifact, and RFC822 chunk seams
- persistence, isolation, and ingestion determinism are test-backed
- no hidden Gmail search, mailbox sync, attachments, write actions, Calendar, compile-contract, runner, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the repo can persist deterministic user-scoped read-only Gmail account records and ingest one selected Gmail message into the existing artifact/chunk seam with passing Postgres-backed tests, while still deferring broader Gmail connector behavior, Calendar, and UI.
