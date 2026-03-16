# SPRINT_PACKET.md

## Sprint Title

Sprint 5P: Gmail Credential Hardening

## Sprint Type

repair

## Sprint Reason

Sprint 5O successfully opened the first live read-only Gmail seam, but it left a known security debt: Gmail access tokens are still persisted in plaintext on `gmail_accounts`. Before any broader Gmail auth lifecycle, search, sync, Calendar, or UI work, that gap needs to be closed.

## Sprint Intent

Harden the narrow Gmail connector seam by replacing plaintext credential storage with an explicit protected credential mechanism and by removing credential exposure from normal account surfaces, without widening into Gmail search, sync, write actions, Calendar, or UI.

## Git Instructions

- Branch Name: `codex/sprint-5p-gmail-credential-hardening`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5O shipped the first narrow read-only Gmail account and single-message ingestion seam.
- The accepted review explicitly calls out plaintext Gmail credential storage as acceptable only for that narrow prototype slice and recommends hardening before broader connector rollout.
- Connector security is the immediate risk, not more Gmail breadth.
- The narrowest safe next step is credential hardening only, keeping the current single-message Gmail ingestion seam otherwise intact.

## In Scope

- Add schema and migration support only as needed to remove plaintext credential storage from `gmail_accounts`, for example:
  - protected credential blob or reference fields
  - optional token metadata fields if needed for the narrow hardened seam
- Define typed contract changes for:
  - Gmail account connect requests if a hardened credential payload shape is required
  - Gmail account responses with secrets removed
  - any narrow Gmail ingestion error shape changes needed for hardened credential lookup failures
- Implement a narrow Gmail credential seam that:
  - persists Gmail credentials through one explicit protected storage mechanism
  - does not return secrets through account list or detail responses
  - lets the existing single-message Gmail ingestion path resolve credentials through the hardened mechanism
  - preserves deterministic account reads and per-user isolation
- Add unit and integration tests for:
  - protected credential persistence
  - absence of secret material in Gmail account responses
  - successful single-message Gmail ingestion using the hardened credential path
  - deterministic failure when required credentials are missing or invalid
  - per-user isolation
  - stable response shape

## Out of Scope

- No Gmail search.
- No mailbox sync or backfill jobs.
- No attachment ingestion.
- No write-capable Gmail actions.
- No Calendar connector scope.
- No OAuth UX or callback UI.
- No compile contract changes.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Migration removing plaintext credential storage from the live Gmail seam in favor of a protected credential mechanism.
- Stable Gmail account contracts that no longer expose secret material.
- Updated single-message Gmail ingestion path that resolves credentials through the hardened mechanism.
- Unit and integration coverage for credential protection, ingestion continuity, failure handling, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- Gmail account records no longer persist plaintext access tokens in the normal application table surface.
- Gmail account list and detail responses do not expose secret material.
- The existing single-message Gmail ingestion path continues to work through the hardened credential mechanism.
- Missing or invalid credentials fail deterministically and do not corrupt task workspace or artifact state.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No Gmail search, sync, attachments, write actions, Calendar, compile-contract, runner, or UI scope enters the sprint.

## Implementation Constraints

- Keep the repair narrow and boring.
- Do not broaden the Gmail feature surface while fixing credential storage.
- Prefer one explicit protected credential mechanism over ad hoc masking or partial hiding.
- Preserve the current Gmail account and single-message ingestion seams as much as possible outside the security fix.
- If credential hardening needs one minimal rule added to `RULES.md`, keep it scoped to connector-secret handling only.

## Suggested Work Breakdown

1. Add the schema/migration changes required for protected Gmail credential storage.
2. Update Gmail account contracts so secrets are accepted only on write and never returned on read.
3. Route single-message Gmail ingestion through the hardened credential lookup path.
4. Add deterministic failure handling for missing or invalid protected credentials.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact Gmail credential contract and schema changes introduced
- the protected credential storage mechanism used
- exact commands run
- unit and integration test results
- one example Gmail account response proving secret removal
- one example Gmail ingestion response through the hardened path
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to Gmail credential hardening
- plaintext credential persistence is removed from the normal `gmail_accounts` surface
- Gmail account reads no longer expose secrets
- the existing single-message Gmail ingestion path still works through the hardened seam
- no hidden Gmail search, sync, attachments, write actions, Calendar, compile-contract, runner, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the repo no longer stores plaintext Gmail credentials in the normal application table surface, the existing read-only single-message Gmail ingestion seam still works through the hardened credential path, and the full path is verified with Postgres-backed tests while broader Gmail and Calendar connector work remains deferred.
