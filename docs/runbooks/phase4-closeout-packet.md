# Phase 4 Closeout Packet

This closeout packet defines Sprint 16 evidence required to mark MVP release-candidate rehearsal as deterministic, artifact-driven, and durable across repeated runs.

## Required Go/No-Go Commands

Run from repo root:

1. `python3 scripts/run_phase4_release_candidate.py`
2. `python3 scripts/run_phase4_release_candidate.py --induce-step phase4_validation_matrix` (contract rehearsal NO_GO path)
3. `python3 scripts/verify_phase4_rc_archive.py`

## Required Evidence Bundle

- latest summary artifact (compatibility path): `artifacts/release/phase4_rc_summary.json`
- retained archive artifacts: `artifacts/release/archive/*_phase4_rc_summary.json`
- append-only archive ledger: `artifacts/release/archive/index.json`
- artifact schema fields:
  - `artifact_version`
  - `ordered_steps`
  - `steps[]` entries with `status`, `command`, `exit_code`, `duration_seconds`, and `induced_failure`
  - `final_decision` and `summary_exit_code`
- archive index entry fields:
  - `created_at`
  - `archive_artifact_path`
  - `final_decision`
  - `summary_exit_code`
  - `failing_steps`
  - `command_mode`
- GO requires `final_decision` = `GO` and every step `status` = `PASS`
- NO_GO requires at least one failed step and preserves partial evidence (`NOT_RUN` for downstream steps)
- GO and NO_GO runs must be retained concurrently in the archive/index (no overwrite of prior archive entries)
- links to current `BUILD_REPORT.md` and `REVIEW_REPORT.md`

## Explicit Deferred Scope

Remain out of closeout scope unless explicitly opened:

- runtime/task-run schema redesign
- connector breadth expansion
- auth-model redesign
- platform/channel expansion
- workflow engine/orchestration redesign
