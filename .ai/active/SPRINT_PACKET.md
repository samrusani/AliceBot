# SPRINT_PACKET.md

## Sprint Title

Sprint 5K: Project Truth Synchronization After Hybrid Artifact Compile

## Sprint Type

refactor

## Sprint Reason

Sprint 5J is implemented and the feature path is still correct, but the live truth artifacts are materially stale. `ARCHITECTURE.md` still describes the repo as current through Sprint 5H, and `ROADMAP.md` still says current through Sprint 5A. Before opening richer document parsing, read-only connectors, or any UI work, Control Tower needs the architecture and roadmap truth reset to the accepted repo state.

## Sprint Intent

Synchronize the live truth artifacts with the implemented and review-passed repo state through Sprint 5J, so future planning, handoff, and review work all start from accurate architecture, roadmap, and current-state documents.

## Git Instructions

- Branch Name: `codex/sprint-5k-project-truth-sync`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5I shipped compile-path semantic artifact retrieval.
- Sprint 5J shipped deterministic hybrid lexical-plus-semantic artifact merge in compile.
- `ARCHITECTURE.md` is still describing the accepted repo slice through Sprint 5H and still treats compile-path semantic artifact use and hybrid artifact retrieval as deferred.
- `ROADMAP.md` still says the accepted repo state is current through Sprint 5A.
- Planning from stale truth at this point would increase scope drift risk just before richer document parsing and connector work.

## In Scope

- Audit the accepted implemented slice from the repo and passed sprint reports through Sprint 5J.
- Update `ARCHITECTURE.md` so it accurately describes the implemented seams through:
  - compile-path semantic artifact retrieval
  - deterministic hybrid lexical-plus-semantic artifact merge in compile
  - current artifact chunk contracts and retrieval boundaries
- Update `ROADMAP.md` so:
  - completed/current milestone state reflects the accepted repo state through Sprint 5J
  - the next delivery focus is framed from the actual shipped artifact retrieval baseline
  - stale “current position” language is corrected
- Update `.ai/handoff/CURRENT_STATE.md` so:
  - implemented areas and risks reflect the repo through Sprint 5J
  - the current milestone position is correct
  - the immediate next move matches the next narrow sprint boundary after truth sync
- Update `BUILD_REPORT.md` with the truth-sync evidence and exact files corrected.

## Out of Scope

- No schema changes.
- No API changes.
- No runtime code changes.
- No richer document parsing.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Updated `ARCHITECTURE.md` aligned to the implemented repo state through Sprint 5J.
- Updated `ROADMAP.md` with correct completed/current/next milestone sequencing.
- Updated `.ai/handoff/CURRENT_STATE.md` reflecting the actual shipped state and immediate next move.
- Updated `BUILD_REPORT.md` describing exactly which truth artifacts were synchronized and what evidence was used.

## Acceptance Criteria

- `ARCHITECTURE.md` describes compile-path semantic artifact retrieval and hybrid artifact compile merge as implemented behavior, not deferred work.
- `ROADMAP.md` no longer claims the repo is current only through Sprint 5A.
- `.ai/handoff/CURRENT_STATE.md` no longer describes the repo as current only through Sprint 5D.
- Truth artifacts clearly distinguish between implemented behavior and later planned work.
- No runtime, schema, API, connector, runner, or UI changes appear in the sprint diff.

## Implementation Constraints

- Keep this sprint documentation-only and boring.
- Use accepted repo state and passed sprint reports as evidence, not aspiration.
- Prefer explicit “implemented now” versus “planned later” boundaries.
- If a truth artifact cannot be updated confidently from accepted evidence, narrow the statement rather than guessing.
- Do not widen into product changes just because the architecture text is stale.

## Suggested Work Breakdown

1. Audit the implemented repo state and accepted sprint reports through Sprint 5J.
2. Update `ARCHITECTURE.md` to reflect the current shipped seams and boundaries.
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
- `ARCHITECTURE.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` now match the implemented repo state through Sprint 5J
- compile-path semantic artifact retrieval and hybrid artifact merge are documented accurately
- milestone sequencing is truthful and current
- no hidden runtime, schema, API, connector, runner, or UI scope entered the sprint

## Exit Condition

This sprint is complete when the project truth artifacts accurately describe the implemented repo state through Sprint 5J and future planning can proceed from synchronized architecture, roadmap, and current-state documents.
