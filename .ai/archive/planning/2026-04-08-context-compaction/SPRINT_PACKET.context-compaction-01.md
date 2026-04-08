# Sprint Packet — Context Compaction 01

## Sprint Type

refactor

## Sprint Reason

Live project memory has started to bloat. `.ai/handoff/CURRENT_STATE.md`, `ROADMAP.md`, `RULES.md`, and adjacent control/docs surfaces now contain overlap, stale phrasing, and historical detail that should be archived instead of kept in active context.

Phase 9 is complete. The goal here is to tighten live project truth before Phase 10 planning starts, not to reopen shipped product scope.

## Objective

Compact the project’s live operating files so Control Tower and future agents work from a smaller, cleaner, and more trustworthy active context set while preserving Phase 9 launch truth and historical traceability.

## Why This Sprint Matters

If live project memory keeps growing unchecked, planning quality, review quality, and execution quality degrade. This sprint reduces active-context noise and preserves trustworthy control docs without changing the product.

## In Scope

- compress `.ai/handoff/CURRENT_STATE.md`
- rewrite `ROADMAP.md` so it remains future-facing and non-redundant
- prune `RULES.md` to durable reusable rules only
- slim `README.md` to onboarding + shipped-product truth only if needed
- slim `CHANGELOG.md` to release-facing history only if needed
- archive superseded planning/history docs into `docs/archive/`
- archive superseded control snapshots into `.ai/archive/` if needed
- update references so canonical files point to the correct archive locations
- preserve and clarify the current control state:
  - Phase 9 complete
  - no active build sprint
  - waiting for Phase 10 planning docs

## Out of Scope

- new product features
- source code changes unrelated to doc paths or references
- UI improvements
- backend refactors
- new architecture decisions unless current docs are clearly inaccurate
- changing roadmap priorities beyond removing historical clutter
- creating a fake Phase 9 follow-on sprint
- archiving or pruning current Phase 9 launch docs/evidence simply because they are recent or prominent

## Files / Modules In Scope

- `.ai/handoff/CURRENT_STATE.md`
- `ROADMAP.md`
- `RULES.md`
- `README.md`
- `CHANGELOG.md`
- `.ai/archive/**`
- `docs/archive/**`
- `ARCHITECTURE.md` only if duplicate or stale control-language must be cleaned
- `DESIGN_SYSTEM.md` only if present and clearly stale

## Files Explicitly Protected From Archival/Pruning In This Sprint

- `docs/quickstart/**`
- `docs/integrations/**`
- `docs/examples/phase9-command-walkthrough.md`
- `docs/runbooks/phase9-public-release-runbook.md`
- `docs/release/**`
- `eval/baselines/phase9_s37_baseline.json`
- `eval/reports/phase9_eval_latest.json`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `LICENSE`

These are current shipped Phase 9 launch/release artifacts, not stale history.

## Constraints

- do not delete information unless it is safely archived
- preserve historical traceability
- do not change product scope
- do not change source code unless required for doc-link/path integrity
- keep canonical files concise and durable
- prefer archive over deletion
- preserve current repo truth that Phase 9 is complete and there is no active build sprint
- do not regenerate the active sprint packet into a fake new sprint; keep it as control truth only

## Relevant Rules

- archive history instead of feeding it back into live memory
- roadmap must be future-facing
- rules must contain only durable reusable guidance
- no execution agent owns project truth
- when in doubt, compress
- current shipped launch docs are canonical, not archive candidates

## Design Source of Truth

- `DESIGN_SYSTEM.md` if present
- otherwise N/A unless touched for pruning

## Architecture Source of Truth

- `ARCHITECTURE.md`

## Acceptance Criteria

- `CURRENT_STATE.md` is concise, current, and non-redundant
- `ROADMAP.md` no longer carries unnecessary sprint-ledger clutter beyond what is needed for current truth
- `RULES.md` contains only durable rules
- `README.md` is onboarding-first and accurate to the shipped Phase 9 wedge
- `CHANGELOG.md` is release-facing only
- superseded planning/history material has been moved to `docs/archive/` and/or `.ai/archive/`
- all archive links and references resolve correctly
- current Phase 9 quickstart/integration/release/eval artifacts remain canonical and unarchived
- no product behavior or scope was changed
- the repo remains in the correct control state:
  - Phase 9 complete
  - no active build sprint
  - Phase 10 planning not yet defined

## Required Tests

- manual review of canonical files for duplication/staleness
- link/path sanity check for moved archive files
- confirm no source-code behavior changed
- if docs paths are referenced in tooling, run relevant docs/path validation

## Docs To Update

- `.ai/handoff/CURRENT_STATE.md`
- `ROADMAP.md`
- `RULES.md`
- `README.md`
- `CHANGELOG.md`
- optional `ARCHITECTURE.md`
- optional `DESIGN_SYSTEM.md`

## Git Instructions

### Branch Name

`codex/refactor-context-compaction-01`

### Base Branch

`main`

### PR Strategy

create-or-update

### Merge Policy

squash-merge after PASS and explicit Control Tower approval

## Definition of Done

The live operating files are smaller, cleaner, and more trustworthy; historical material is preserved in archive; current Phase 9 launch truth remains canonical; and the project is left in a clean waiting state for Phase 10 planning.
