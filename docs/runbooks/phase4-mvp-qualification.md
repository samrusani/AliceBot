# Phase 4 MVP Qualification

Phase 4 Sprint 19 formalizes MVP qualification as one deterministic command plus a sign-off verifier.

## Canonical Commands

Run from repo root:

1. `python3 scripts/run_phase4_mvp_qualification.py`
2. `python3 scripts/verify_phase4_mvp_signoff_record.py`

The qualification command executes this ordered chain:

1. `python3 scripts/run_phase4_release_candidate.py`
2. `python3 scripts/verify_phase4_rc_archive.py`
3. `python3 scripts/generate_phase4_mvp_exit_manifest.py`
4. `python3 scripts/verify_phase4_mvp_exit_manifest.py`

## Qualification Artifacts

- Sign-off record: `artifacts/release/phase4_mvp_signoff_record.json`
- RC summary: `artifacts/release/phase4_rc_summary.json`
- RC archive index: `artifacts/release/archive/index.json`
- MVP exit manifest: `artifacts/release/phase4_mvp_exit_manifest.json`

## Sign-Off Contract

- `final_decision = GO` requires:
  - all qualification chain steps `PASS`
  - `summary_exit_code = 0`
  - `blockers = []`
- `final_decision = NO_GO` requires:
  - one or more non-PASS steps (`FAIL` and/or `NOT_RUN`)
  - `summary_exit_code = 1`
  - explicit `blockers[]` entries for each non-PASS step

## Blocker Policy

- Fixes in this sprint are blocker-only.
- Non-blocking improvements are deferred.
- If qualification returns `NO_GO`, capture blocker details in:
  - `artifacts/release/phase4_mvp_signoff_record.json`
  - `BUILD_REPORT.md`
