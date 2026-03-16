# SPRINT_PACKET.md

## Sprint Title

Sprint 5U: Project Truth Synchronization After Gmail Secret Externalization

## Sprint Type

refactor

## Sprint Reason

Sprint 5T is implemented and the repo remains on track, but the live truth artifacts have drifted again. `ARCHITECTURE.md` now reflects Sprint 5T, while `ROADMAP.md` and `.ai/handoff/CURRENT_STATE.md` are still anchored around Sprint 5R. Before opening the next Gmail follow-up seam such as `legacy_db_v0` removal, Control Tower needs the planning and handoff artifacts reset to the accepted repo state.

## Sprint Intent

Synchronize the live truth artifacts with the implemented and review-passed repo state through Sprint 5T, so future planning, handoff, and review work all start from accurate architecture, roadmap, and current-state documents.

## Git Instructions

- Branch Name: `codex/sprint-5u-project-truth-sync-after-gmail-secret-externalization`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5S last synchronized truth through Sprint 5R.
- Sprint 5T changed the accepted connector boundary materially:
  - the primary Gmail credential path is now external-secret-backed
  - `gmail_account_credentials` now persists locator metadata on the primary path
  - a narrow `legacy_db_v0` transition path now exists for older rows
- `ARCHITECTURE.md` already reflects that accepted state, but `ROADMAP.md` and `.ai/handoff/CURRENT_STATE.md` still describe the repo through Sprint 5R and still describe external secret-manager integration as future work.
- Planning from that stale truth would create avoidable scope and review drift for the next Gmail sprint.

## In Scope

- Audit the accepted implemented slice from the repo and passed sprint reports through Sprint 5T.
- Update `ARCHITECTURE.md` only if needed so it accurately describes the implemented seams through:
  - externalized Gmail secret-manager-backed credential storage
  - secret-free Gmail account reads
  - refresh-token renewal and rotated refresh-token persistence through the externalized seam
  - the narrow `legacy_db_v0` transition boundary
- Update `ROADMAP.md` so:
  - completed and current milestone state reflects the accepted repo state through Sprint 5T
  - the next delivery focus is framed from the actual shipped Gmail externalized-secret baseline
  - stale “next delivery focus” language that still treats external secret-manager integration as future work is corrected
- Update `.ai/handoff/CURRENT_STATE.md` so:
  - implemented areas and current boundaries reflect the repo through Sprint 5T
  - the current milestone position is correct
  - the immediate next move matches the next narrow sprint boundary after truth sync
- Update `BUILD_REPORT.md` with the truth-sync evidence and exact files corrected.

## Out of Scope

- No schema changes.
- No API changes.
- No runtime code changes.
- No Gmail search, mailbox sync, attachments, or write actions.
- No Calendar connector scope.
- No `legacy_db_v0` removal yet.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Updated `ARCHITECTURE.md` aligned to the implemented repo state through Sprint 5T.
- Updated `ROADMAP.md` with correct completed/current/next milestone sequencing.
- Updated `.ai/handoff/CURRENT_STATE.md` reflecting the actual shipped state and immediate next move.
- Updated `BUILD_REPORT.md` describing exactly which truth artifacts were synchronized and what evidence was used.

## Acceptance Criteria

- `ARCHITECTURE.md` accurately describes the shipped Gmail seam as external-secret-backed on the primary path, secret-free on reads, renewal-capable, rotation-capable, and still narrow/read-only.
- `ROADMAP.md` no longer claims the next Gmail auth-adjacent seam is external secret-manager integration.
- `.ai/handoff/CURRENT_STATE.md` no longer describes external secret-manager integration as unimplemented.
- Truth artifacts clearly distinguish implemented Gmail externalization behavior from later planned Gmail breadth and from the still-deferred `legacy_db_v0` cleanup sprint.
- No runtime, schema, API, connector-breadth, runner, or UI changes appear in the sprint diff.

## Implementation Constraints

- Keep this sprint documentation-only and boring.
- Use accepted repo state and passed sprint reports as evidence, not aspiration.
- Prefer explicit “implemented now” versus “planned later” boundaries.
- If a truth artifact cannot be updated confidently from accepted evidence, narrow the statement rather than guessing.
- Do not widen into product changes just because the roadmap or handoff text is stale.

## Suggested Work Breakdown

1. Audit the implemented repo state and accepted sprint reports through Sprint 5T.
2. Update `ARCHITECTURE.md` only where it still lags the accepted Gmail externalization seam.
3. Update `ROADMAP.md` to reflect actual completed and current milestone state.
4. Update `.ai/handoff/CURRENT_STATE.md` to reflect actual current state and the immediate next move.
5. Update `BUILD_REPORT.md` with exact truth-sync evidence and scope confirmation.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exactly which truth artifacts were updated
- which accepted reports or repo evidence were used
- the specific stale statements that were corrected
- confirmation that no runtime or schema changes were made
- what remains intentionally deferred after truth synchronization

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed documentation-only
- `ARCHITECTURE.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` now match the implemented repo state through Sprint 5T
- the shipped Gmail external secret-manager seam and its current narrow boundary are documented accurately
- milestone sequencing is truthful and current
- no hidden runtime, schema, API, connector-breadth, runner, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the project truth artifacts accurately describe the implemented repo state through Sprint 5T and future planning can proceed from synchronized architecture, roadmap, and current-state documents.
