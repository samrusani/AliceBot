# SPRINT_PACKET.md

## Sprint Title

Sprint 7H: MVP RC Truth Sync And Gate Canonicalization

## Sprint Type

docs

## Sprint Reason

Sprint 7G delivered a deterministic extensive validation matrix and passed review, but canonical project docs still anchor to Sprint 6X-era state and one runbook command remains machine-specific. This creates avoidable planning and review drift risk right before MVP release-candidate decisions.

## Sprint Intent

Synchronize canonical docs and runbooks to the accepted Sprint 7G baseline and formalize the MVP validation matrix command as the default go/no-go gate, without changing product or backend behavior.

## Git Instructions

- Branch Name: `codex/sprint-7h-mvp-rc-truth-sync`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 7G now gives one reliable extensive-testing entrypoint.
- Canonical docs still claim Sprint 6X as current state, which no longer matches shipped verification reality.
- Pre-MVP control reliability now depends more on accurate docs and deterministic operator instructions than on new feature seams.

## Design Truth

- This is a documentation/control-artifact sprint, not a feature sprint.
- Make reality explicit: accepted state includes Sprint 7G readiness + validation tooling.
- Keep instructions portable and machine-independent.

## Exact Surfaces In Scope

- Canonical truth docs and planning docs.
- MVP validation runbook portability and gate canonicalization.
- Optional small durable rule updates to prevent recurrence.

## Exact Files In Scope

- [README.md](README.md)
- [ROADMAP.md](ROADMAP.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md)
- [RULES.md](RULES.md)
- [mvp-validation-matrix.md](docs/runbooks/mvp-validation-matrix.md)
- [mvp-readiness-gates.md](docs/runbooks/mvp-readiness-gates.md)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Update canonical docs to reflect accepted state through Sprint 7G (no 6X-era “current state” language).
- Document the MVP default validation command as:
  - `python3 scripts/run_mvp_validation_matrix.py`
- Fix runbook portability by removing machine-specific absolute command paths.
- Align README quick checks and handoff docs with readiness + validation matrix workflow.
- Optionally add concise RULES guidance to prevent recurrence:
  - no machine-specific local absolute paths in shared runbooks
  - canonical docs must be updated when sprint-level operating baseline changes

## Out of Scope

- No new endpoints, migrations, or schema changes.
- No connector breadth expansion or write-capable connector behavior.
- No auth, orchestration, or worker-runtime expansion.
- No new web routes, UI redesign, or test-behavior changes.
- No new validation runner features beyond documentation alignment.

## Required Deliverables

- Canonical docs updated to Sprint 7G truth baseline.
- Portable, machine-independent commands in `docs/runbooks/mvp-validation-matrix.md`.
- Updated sprint reports reflecting Sprint 7H docs/control scope only.

## Acceptance Criteria

- `README.md`, `ROADMAP.md`, `ARCHITECTURE.md`, and `.ai/handoff/CURRENT_STATE.md` no longer claim Sprint 6X as current state.
- `docs/runbooks/mvp-validation-matrix.md` uses repo-relative or environment-agnostic commands (no `/Users/...` paths).
- A grep-based portability check passes for shared docs/runbooks:
  - no `file://`, `vscode://`, or local absolute user-home paths.
- Sprint remains documentation/rules/report scope only.

## Implementation Constraints

- Keep edits concise and truth-preserving.
- Do not introduce new feature claims beyond what repo evidence already supports.
- Preserve product scope boundaries already documented in `PRODUCT_BRIEF.md`.

## Suggested Work Breakdown

1. Update canonical baseline statements from 6X-era to accepted 7G-era truth.
2. Normalize MVP validation runbook commands to portable forms.
3. Align README/handoff/roadmap language with current validation workflow.
4. Run portability/consistency checks over touched docs.
5. Update build/review reports.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact canonical docs updated
- portability checks executed and results
- explicit statement of what remains deferred
- explicit deferred criteria not covered by this sprint

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed within docs/control-artifact scope
- canonical files now match accepted 7G baseline
- runbook command portability is fixed
- no hidden product/backend scope entered

## Exit Condition

This sprint is complete when canonical docs and runbooks are synchronized to the accepted Sprint 7G operating baseline, matrix gate usage is explicit and portable, and review can no longer fail due to baseline-document drift.
