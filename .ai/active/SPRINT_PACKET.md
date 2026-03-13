# SPRINT_PACKET.md

## Sprint Title

Sprint 5B: Project Truth Compaction 01

## Sprint Type

refactor

## Sprint Reason

The live project-truth files are now materially stale and redundant relative to the accepted repo state through Sprint 5A. `ROADMAP.md` and `.ai/handoff/CURRENT_STATE.md` still describe the project as pre-Milestone-5 and pre-step-linked approval/execution/workspace work, which will degrade planning and review quality if not compacted now.

## Sprint Intent

Compact and synchronize the live project-truth files so Control Tower, builders, and reviewers operate from a smaller, current, non-redundant source-of-truth set without changing product scope or runtime behavior.

## Git Instructions

- Branch Name: `codex/refactor-project-truth-compaction-01`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint Matters

- `ROADMAP.md` and `.ai/handoff/CURRENT_STATE.md` are behind the accepted repo state.
- `ARCHITECTURE.md` now reflects Sprint 5A, so the other live truth artifacts need to catch up and shed stale milestone text.
- A narrow compaction sprint is safer than letting outdated truth leak into future planning or review work.
- This restores clean project truth without changing product scope.

## In Scope

- compact and synchronize `.ai/handoff/CURRENT_STATE.md`
- compact and synchronize `ROADMAP.md`
- prune `RULES.md` only if it contains stale or duplicate guidance after truth sync
- slim `README.md` only if it duplicates active planning truth instead of onboarding
- archive stale planning/history docs into `docs/archive/` when they are no longer appropriate as live context
- update internal references so canonical files point to the right archive locations
- update `ARCHITECTURE.md` only if a stale duplicate or outdated boundary statement remains after the Sprint 5A truth sync

## Out of Scope

- new product features
- source code changes unrelated to doc-link or archive-link integrity
- UI improvements
- backend refactors
- new architecture decisions unless a current truth file is factually inaccurate
- changing roadmap priorities beyond removing stale historical clutter
- artifact, document, connector, or runner implementation work

## Files / Modules In Scope

- `.ai/handoff/CURRENT_STATE.md`
- `ROADMAP.md`
- `RULES.md` only if needed for stale/duplicate guidance cleanup
- `README.md` only if needed for onboarding/truth separation
- `docs/archive/**`
- `ARCHITECTURE.md` only if duplicate or stale sections must be cleaned after truth sync

## Constraints

- do not delete information unless it is safely archived
- preserve historical traceability
- do not change product scope
- do not change runtime behavior
- keep canonical files concise, current, and durable
- prefer archive over deletion
- use `PRODUCT_BRIEF.md`, `ARCHITECTURE.md`, accepted build/review reports, and the implemented repo state as the truth basis

## Relevant Rules

- active sprint packet is the top scope boundary for implementation work
- never represent planned architecture as implemented behavior
- roadmap should be future-facing once historical milestone state has been distilled elsewhere
- rules should contain only durable reusable guidance
- when live context becomes noisy, reduce and archive instead of letting stale state accumulate

## Design Source of Truth

- `DESIGN_SYSTEM.md` if it is later introduced
- otherwise N/A for this sprint

## Architecture Source of Truth

- `ARCHITECTURE.md`

## Acceptance Criteria

- `.ai/handoff/CURRENT_STATE.md` is concise, current, and non-redundant through Sprint 5A.
- `ROADMAP.md` no longer presents stale pre-Sprint-5 state and is future-facing from the current repo position.
- `RULES.md` contains only durable rules and no stale scope-era leftovers.
- Any stale planning/history material moved out of live context is archived under `docs/archive/`.
- All archive links and references resolve correctly.
- No product behavior, scope, or runtime code was changed.
- Control Tower can plan from a smaller, cleaner active context set after this sprint.

## Required Tests

- manual review of canonical files for duplication, staleness, and truth alignment
- link/path sanity check for moved archive files
- confirm no runtime or schema behavior changed
- run docs/path validation only if any existing tooling references moved files

## Docs To Update

- `.ai/handoff/CURRENT_STATE.md`
- `ROADMAP.md`
- `RULES.md` if needed
- `README.md` if needed
- `ARCHITECTURE.md` only if stale duplication remains

## Definition of Done

The live project-truth files are smaller, cleaner, and aligned to the accepted repo state through Sprint 5A; stale planning/history material is preserved in archive; and the next sprint can be planned from a trustworthy active context set.
