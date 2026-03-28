# Phase 4 Closeout Packet

This closeout packet defines Sprint 18 MVP phase-exit evidence required for formal closeout sign-off.

## Required Go/No-Go Commands

Run from repo root:

1. `python3 scripts/run_phase4_release_candidate.py`
2. `python3 scripts/generate_phase4_mvp_exit_manifest.py`
3. `python3 scripts/verify_phase4_mvp_exit_manifest.py`
4. `python3 scripts/verify_phase4_rc_archive.py`

## Required Evidence Bundle

- latest summary artifact (compatibility path): `artifacts/release/phase4_rc_summary.json`
- retained archive artifacts: `artifacts/release/archive/*_phase4_rc_summary.json`
- append-only archive ledger: `artifacts/release/archive/index.json`
- deterministic archive index lock path: `artifacts/release/archive/index.lock`
- MVP exit manifest artifact: `artifacts/release/phase4_mvp_exit_manifest.json`
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
- MVP exit manifest fields:
  - `artifact_version` (`phase4_mvp_exit_manifest.v1`)
  - `artifact_path`
  - `phase` (`phase4`) and `release_gate` (`mvp`)
  - `decision` (`final_decision`, `summary_exit_code`, `failing_steps`)
  - `source_references` (`archive_index_path`, `archive_entry_index`, `archive_entry_created_at`, `archive_artifact_path`, `archive_entry_command_mode`)
  - `ordered_steps`
  - `step_status_by_id`
  - `compatibility_validation_commands`
  - `integrity.archive_artifact_sha256`
- GO requires `final_decision` = `GO` and every step `status` = `PASS`
- NO_GO requires at least one failed step and preserves partial evidence (`NOT_RUN` for downstream steps)
- GO and NO_GO runs must be retained concurrently in the archive/index (no overwrite of prior archive entries)
- archive index updates are lock-guarded and atomic:
  - writer acquires `artifacts/release/archive/index.lock`
  - index persistence uses temp-file write + atomic replace for `artifacts/release/archive/index.json`
  - lock contention timeout is explicit and deterministic (`exit 2` with lock-timeout message)
- MVP exit manifest generation must select the latest GO rehearsal entry from archive index evidence.
- MVP exit manifest verification must validate required schema fields plus referenced archive/index evidence integrity.
- links to current `BUILD_REPORT.md` and `REVIEW_REPORT.md`

## Explicit Deferred Scope

Remain out of closeout scope unless explicitly opened:

- runtime/task-run schema redesign
- connector breadth expansion
- auth-model redesign
- platform/channel expansion
- workflow engine/orchestration redesign
