# Phase 4 Closeout Packet

This closeout packet defines Sprint 15 evidence required to mark MVP release-candidate rehearsal as deterministic and artifact-driven.

## Required Go/No-Go Commands

Run from repo root:

1. `python3 scripts/run_phase4_release_candidate.py`
2. `python3 scripts/run_phase4_release_candidate.py --induce-step phase4_validation_matrix` (contract rehearsal NO_GO path)

## Required Evidence Bundle

- generated artifact: `artifacts/release/phase4_rc_summary.json`
- artifact schema fields:
  - `artifact_version`
  - `ordered_steps`
  - `steps[]` entries with `status`, `command`, `exit_code`, `duration_seconds`, and `induced_failure`
  - `final_decision` and `summary_exit_code`
- GO requires `final_decision` = `GO` and every step `status` = `PASS`
- NO_GO requires at least one failed step and preserves partial evidence (`NOT_RUN` for downstream steps)
- links to current `BUILD_REPORT.md` and `REVIEW_REPORT.md`

## Explicit Deferred Scope

Remain out of closeout scope unless explicitly opened:

- runtime/task-run schema redesign
- connector breadth expansion
- auth-model redesign
- platform/channel expansion
- workflow engine/orchestration redesign
