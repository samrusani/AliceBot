# BUILD_REPORT.md

## Sprint Objective
Implement Phase 4 Sprint 17 RC archive concurrency hardening so concurrent `run_phase4_release_candidate.py` runs cannot lose or corrupt `artifacts/release/archive/index.json` entries.

## Completed Work
- Hardened `scripts/run_phase4_release_candidate.py` archive/index path with deterministic lock + atomic persistence:
  - lock file path: `artifacts/release/archive/index.lock`
  - lock acquire: `os.O_CREAT | os.O_EXCL` loop with bounded wait
  - retry/timeout contract: `0.05s` retry interval, `5.0s` timeout
  - explicit lock-timeout behavior: `ArchiveIndexLockTimeoutError` and CLI exit code `2`
  - atomic writes: temp file in target directory + `os.replace()` for index and summary artifacts
  - contention consistency: archive artifact creation and index append now happen under one lock, with archive cleanup if index append fails before commit
- Extended `scripts/verify_phase4_rc_archive.py` hardening invariants:
  - index path must match `archive_dir/index.json`
  - stale `archive/index.lock` is treated as verification failure
- Added deterministic contention coverage:
  - `tests/integration/test_phase4_release_candidate.py`
    - parallel concurrent archive/index writes keep all entries (no drop)
    - explicit bounded lock-timeout contract test
  - `tests/integration/test_phase4_rc_archive.py`
    - stale lock detection test
  - `tests/unit/test_phase4_gate_wrappers.py`
    - CLI lock-timeout exit/message contract test
- Synced Sprint 17 docs in the sprint packet write scope:
  - `docs/runbooks/phase4-closeout-packet.md`
  - `docs/runbooks/phase4-validation-matrix.md`
  - `README.md`
  - `ROADMAP.md`
  - `.ai/handoff/CURRENT_STATE.md`

## Contention Scenario Results
- Concurrent-writer integration test (`test_archive_index_concurrent_writes_retain_all_entries`) passed:
  - 4 near-concurrent writers
  - 4 unique retained archive artifacts (`<timestamp>`, `_001`, `_002`, `_003`)
  - 4 index entries preserved (no lost updates)
- Lock-timeout integration test (`test_archive_index_lock_timeout_is_explicit_and_bounded`) passed:
  - pre-held `index.lock`
  - bounded timeout raises deterministic lock-timeout error
  - index write does not proceed
- CLI lock-timeout exit contract unit test passed:
  - emits explicit failure message
  - returns configured lock-timeout exit code `2`

## Incomplete Work
- None within Sprint 17 in-scope surfaces.

## Files Changed
- `scripts/run_phase4_release_candidate.py`
- `scripts/verify_phase4_rc_archive.py`
- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_rc_archive.py`
- `tests/unit/test_phase4_gate_wrappers.py`
- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
- `./.venv/bin/python -m pytest tests/integration/test_phase4_release_candidate.py tests/integration/test_phase4_rc_archive.py tests/unit/test_phase4_gate_wrappers.py -q`
  - PASS (`15 passed`)
- `python3 scripts/run_phase4_release_candidate.py`
  - PASS (`exit 0`, `GO`)
  - wrote latest summary + archive artifact + archive index entry
- `python3 scripts/run_phase4_release_candidate.py --induce-step phase4_validation_matrix`
  - EXPECTED NO_GO (`exit 1`)
  - archived NO_GO evidence and appended index entry
- `python3 scripts/verify_phase4_rc_archive.py`
  - PASS (`exit 0`)
- `python3 scripts/run_phase4_validation_matrix.py`
  - PASS (`exit 0`) via elevated run (sandbox localhost DB restriction workaround)
- `python3 scripts/run_phase3_validation_matrix.py`
  - PASS (`exit 0`) via elevated run (sandbox localhost DB restriction workaround)
- `python3 scripts/run_phase2_validation_matrix.py`
  - PASS (`exit 0`) via elevated run (sandbox localhost DB restriction workaround)
- `python3 scripts/run_mvp_validation_matrix.py`
  - PASS (`exit 0`) via elevated run (sandbox localhost DB restriction workaround)

## Blockers/Issues
- Direct non-elevated matrix command reruns in this environment hit sandbox localhost DB restrictions (`psycopg OperationalError: connection ... failed: Operation not permitted`).
- Resolved for verification by rerunning matrix commands with elevated permissions; results were PASS.

## Explicit Deferred Scope
- No changes in `apps/api/src/alicebot_api/*`
- No changes in `workers/alicebot_worker/*`
- No gate semantics changes
- No connector/auth/platform/runtime schema changes

## Recommended Next Step
- Control Tower review should confirm Sprint 17 hardening acceptance and merge once lock/atomic-write behavior and contention coverage are validated against this report.
