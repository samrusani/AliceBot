# SPRINT_PACKET.md

## Sprint Title

Sprint 5Q: Gmail Refresh Token Lifecycle V0

## Sprint Type

feature

## Sprint Reason

Sprint 5P fixed the immediate plaintext-token risk, but the Gmail seam still depends on a single stored access token with no refresh lifecycle. Before broader Gmail auth, search, sync, Calendar, or UI work, the next safe step is to support refresh-token-backed credential renewal on the existing protected credential seam.

## Sprint Intent

Extend the hardened Gmail connector seam so it can persist and use a narrow refresh-token credential shape to renew Gmail access tokens on demand for the existing single-message ingestion path, without opening search, sync, write actions, Calendar, or UI scope.

## Git Instructions

- Branch Name: `codex/sprint-5q-gmail-refresh-token-lifecycle`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5O shipped the first narrow read-only Gmail account and single-message ingestion seam.
- Sprint 5P hardened credential storage by removing plaintext tokens from the normal `gmail_accounts` table surface.
- The accepted review for Sprint 5P explicitly called out refresh-token lifecycle as the next narrow Gmail auth milestone if broader connector use is needed.
- The next safe step is not Gmail search or sync; it is reliable credential renewal on the already-shipped single-message seam.

## In Scope

- Extend schema and migration support only as needed to support a narrow Gmail refresh-token credential shape inside the protected credential seam, for example:
  - refresh-token fields inside the protected credential blob
  - optional token-expiry metadata if needed for deterministic renewal decisions
- Define typed contract changes for:
  - Gmail account connect requests if a refresh-token-capable credential payload is required
  - Gmail account responses if narrow non-secret token metadata must be surfaced
  - Gmail ingestion error shapes if renewal failures need explicit typed responses
- Implement a narrow Gmail credential-renewal seam that:
  - persists refresh-token-capable Gmail credentials through the existing protected credential mechanism
  - renews access tokens through one explicit Gmail token-refresh path only
  - updates the protected credential record deterministically after successful renewal
  - lets the existing single-message Gmail ingestion path obtain a usable access token through the renewal path when required
  - preserves secret-free account reads and per-user isolation
- Add unit and integration tests for:
  - refresh-token credential persistence
  - successful access-token renewal before single-message ingestion
  - deterministic failure when refresh credentials are missing or invalid
  - absence of secret material in Gmail account responses
  - per-user isolation
  - stable response shape

## Out of Scope

- No Gmail search.
- No mailbox sync or backfill jobs.
- No attachment ingestion.
- No write-capable Gmail actions.
- No Calendar connector scope.
- No OAuth UI or callback handling.
- No external secret-manager integration yet.
- No compile contract changes.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Narrow protected-credential support for Gmail refresh-token lifecycle.
- Stable Gmail account contracts that remain secret-free on reads.
- Updated single-message Gmail ingestion path that can renew access tokens through the protected credential seam when needed.
- Unit and integration coverage for renewal success, renewal failure, response stability, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- The protected Gmail credential seam can persist a refresh-token-capable credential shape without reintroducing plaintext secrets to the normal `gmail_accounts` table surface.
- Gmail account list and detail responses remain secret-free.
- The existing single-message Gmail ingestion path can renew and use a fresh access token through the protected credential seam when needed.
- Missing or invalid refresh credentials fail deterministically and do not corrupt Gmail account, task workspace, or artifact state.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No Gmail search, sync, attachments, write actions, Calendar, external secret-manager, compile-contract, runner, or UI scope enters the sprint.

## Implementation Constraints

- Keep the auth-lifecycle extension narrow and boring.
- Reuse the existing `gmail_accounts` plus `gmail_account_credentials` seam rather than creating a second connector store.
- Preserve secret-free Gmail account reads.
- Support one explicit renewal path only; do not introduce account-wide sync, search, or OAuth UI in the same sprint.
- Preserve the existing single-message Gmail ingestion seam outside the credential-renewal addition.

## Suggested Work Breakdown

1. Extend the protected Gmail credential shape and any required migration metadata.
2. Update Gmail connect contracts for refresh-token-capable writes while keeping reads secret-free.
3. Implement deterministic token-renewal logic in the Gmail service seam.
4. Route single-message Gmail ingestion through the renewal-capable credential lookup path.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact Gmail refresh-token credential changes introduced
- the token-renewal rule and renewal trigger used
- exact commands run
- unit and integration test results
- one example Gmail account response proving secret-free reads remain intact
- one example Gmail ingestion response through the renewal-capable path
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to Gmail refresh-token lifecycle support
- secret-free account reads remain intact
- single-message Gmail ingestion still works through the protected credential seam
- renewal success and failure behavior are deterministic and test-backed
- no hidden Gmail search, sync, attachments, write actions, Calendar, external secret-manager, compile-contract, runner, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the repo can renew Gmail access tokens through the protected credential seam for the existing single-message ingestion path, keep Gmail account reads secret-free, and verify the full path with Postgres-backed tests while broader Gmail and Calendar behavior remains deferred.
