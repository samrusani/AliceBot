# SPRINT_PACKET.md

## Sprint Title

Sprint 5T: External Secret-Manager Integration For Gmail Credentials

## Sprint Type

feature

## Sprint Reason

Sprint 5S confirmed the repo is on track and synchronized the truth artifacts through Sprint 5R. The next narrow risk is no longer Gmail auth correctness inside the app database; it is secret-storage boundary quality. The roadmap and current-state docs both identify external secret-manager integration as the strongest next Gmail auth-adjacent seam before broader Gmail scope, Calendar, or UI work.

## Sprint Intent

Extend the existing protected Gmail credential seam so `gmail_account_credentials` can resolve secrets through one explicit external secret-manager boundary, while keeping Gmail account reads secret-free and preserving the existing single-message ingestion contract.

## Git Instructions

- Branch Name: `codex/sprint-5t-gmail-external-secret-manager`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5O opened the first narrow read-only Gmail account and single-message ingestion seam.
- Sprint 5P removed plaintext credential storage from the normal `gmail_accounts` surface.
- Sprint 5Q added refresh-token-backed renewal.
- Sprint 5R added rotated refresh-token persistence.
- Sprint 5S synchronized project truth and explicitly identified external secret-manager integration as the next narrow Gmail auth-adjacent seam.
- The next safe step is to externalize the protected credential storage boundary itself without widening into Gmail search, sync, attachments, Calendar, or UI.

## In Scope

- Add schema and migration support only as needed to support an external-secret-backed credential locator, for example:
  - secret reference fields on `gmail_account_credentials`
  - narrow metadata needed to distinguish local protected credentials from externally stored credentials during the transition
- Define typed contract changes only where needed for:
  - Gmail account connect writes if secret-manager-backed credential writes require a narrow new write shape
  - deterministic Gmail ingestion failure responses when external secret resolution fails
- Implement a narrow external secret-manager seam that:
  - writes Gmail credential material through one explicit secret-manager adapter boundary
  - persists only the non-secret locator or reference metadata in the application database
  - resolves credentials through that adapter for the existing single-message ingestion and token-renewal path
  - supports deterministic rotation-capable credential updates through the same externalized path
  - preserves secret-free Gmail account reads and per-user isolation
- Support one explicit runtime configuration path for the secret-manager adapter, with one deterministic local fallback only if needed for tests
- Add unit and integration tests for:
  - external secret reference persistence
  - absence of secret material in Gmail account responses and normal table reads
  - successful single-message Gmail ingestion through the externalized credential path
  - successful refresh-token renewal and rotated refresh-token persistence through the externalized path
  - deterministic failure when secret resolution or secret update fails
  - per-user isolation
  - stable response shape

## Out of Scope

- No Gmail search.
- No mailbox sync or backfill jobs.
- No attachment ingestion.
- No write-capable Gmail actions.
- No Calendar connector scope.
- No OAuth UI or callback handling.
- No broader connector-secret abstraction for other providers yet.
- No compile contract changes.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Migration updating the Gmail protected-credential seam to support external secret-manager references.
- Stable Gmail account contracts that remain secret-free on reads.
- One explicit external secret-manager adapter path used by Gmail credential reads and writes.
- Updated single-message Gmail ingestion plus refresh/rotation path running through the externalized credential seam.
- Unit and integration coverage for reference persistence, secret resolution, renewal/rotation continuity, failure handling, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- The repo no longer depends on application-table-stored Gmail secret material for the primary protected credential path.
- `gmail_account_credentials` persists only non-secret reference or locator data for the externalized path.
- Gmail account list and detail responses remain secret-free.
- The existing single-message Gmail ingestion path still works through the external secret-manager seam.
- Refresh-token renewal and rotated refresh-token persistence still work through the externalized credential seam.
- Secret-resolution or secret-update failures fail deterministically and do not corrupt Gmail account, task workspace, or artifact state.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No Gmail search, sync, attachments, write actions, Calendar, compile-contract, runner, or UI scope enters the sprint.

## Implementation Constraints

- Keep the auth-storage change narrow and boring.
- Reuse the existing `gmail_accounts` and `gmail_account_credentials` seam rather than introducing a second connector-account model.
- Preserve secret-free Gmail account reads.
- Keep the existing selected-message Gmail ingestion contract stable.
- Use one explicit secret-manager adapter boundary only; do not generalize it to every future provider in this sprint.
- If tests need a local adapter, keep it as a narrow testable implementation detail rather than a second product seam.

## Suggested Work Breakdown

1. Add the schema or migration changes required for external secret references.
2. Define any minimal Gmail write-contract updates needed for secret-manager-backed credential writes.
3. Implement one explicit secret-manager adapter for Gmail credential create, read, refresh, and rotation update paths.
4. Keep Gmail account reads secret-free and stable.
5. Add deterministic failure handling for secret resolution and secret update failures.
6. Add unit and integration tests.
7. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact Gmail credential schema and contract changes introduced
- the external secret-manager adapter rule used
- exact commands run
- unit and integration test results
- one example Gmail account response proving secret-free reads remain intact
- one example Gmail ingestion response through the externalized credential path
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to external secret-manager integration for the Gmail credential seam
- the primary Gmail protected credential path no longer depends on application-table-stored secret material
- Gmail account reads remain secret-free
- single-message Gmail ingestion plus refresh/rotation still work through the externalized seam
- failure handling, isolation, and response stability are test-backed
- no hidden Gmail search, sync, attachments, write actions, Calendar, compile-contract, runner, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the repo resolves Gmail secrets through one explicit external secret-manager boundary for the existing read-only single-message ingestion seam, preserves renewal and rotation behavior through that boundary, and verifies the full path with Postgres-backed tests while broader connector behavior remains deferred.
