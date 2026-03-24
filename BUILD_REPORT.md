# BUILD_REPORT.md

## Sprint Objective
Implement Phase 2 Sprint 14 by replacing synthetic memory-label seeding in readiness `memory_quality` with deterministic explicit-signal-capture-derived evidence and deterministic adjudication, while preserving thresholds/posture semantics and induced-gate determinism.

## Completed Work
- Replaced previous synthetic memory evidence path:
  - Previous path: `run_readiness_gates()` called `_seed_memory_quality_sample(...)`, which directly created synthetic memories (`user.readiness.sample.{index}`) and directly wrote `memory_review_labels` (`correct`/`incorrect`) before evaluating `/v0/memories/evaluation-summary`.
  - Replacement path: `run_readiness_gates()` now calls `_capture_and_adjudicate_memory_quality_sample(...)`, which:
    - appends deterministic `message.user` events,
    - calls `/v0/memories/capture-explicit-signals` per event,
    - extracts capture admissions from `preferences` + `commitments`,
    - deterministically maps admissions to review labels,
    - persists those labels, then evaluates `/v0/memories/evaluation-summary`.
- Implemented deterministic capture input plans by profile:
  - `on_track`: 20 unique explicit preference messages (`I like readiness-topic-XX`).
  - `needs_review`: 16 unique + 4 deterministic duplicates (duplicate captures yield deterministic `NOOP` admissions).
  - `insufficient_evidence`: 9 unique + 1 deterministic duplicate.
- Implemented deterministic adjudication rules used for evaluation-label generation:
  - admission decision `ADD` or `UPDATE` => `correct`
  - any other admission decision (for example `NOOP`) => `incorrect`
  - evidence unavailable/invalid capture payload structure => runtime error, resulting in deterministic `BLOCKED` fallback behavior already present in gate runner.
- Preserved gate thresholds and posture semantics unchanged:
  - threshold remains `precision > 0.80 and adjudicated_sample >= 20`
  - posture outcomes remain `PASS`/`FAIL`/`BLOCKED` with `on_track`/`needs_review`/`insufficient_evidence`.
- Updated readiness-gate integration tests in-scope:
  - added deterministic tests for capture message profile generation,
  - added deterministic test for adjudication mapping,
  - added routing test ensuring induced memory scenarios flow through capture-derived profile selection and produce expected posture/status.

## Incomplete Work
- None in sprint scope.

## Files Changed
- `scripts/run_phase2_readiness_gates.py`
- `tests/integration/test_mvp_readiness_gates.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `./.venv/bin/python -m pytest tests/integration/test_mvp_readiness_gates.py -q`
- Outcome: PASS (`12 passed in 0.23s`, exit code `0`).

2. `python3 scripts/run_phase2_readiness_gates.py --induce-gate memory_needs_review`
- Outcome: deterministic NO_GO (`exit code 1`) as expected for induced scenario.
- Key gate evidence:
  - `memory_quality: FAIL`
  - `precision=0.800000; adjudicated_sample=20; posture=needs_review`
  - `correct=16; incorrect=4`

3. `python3 scripts/run_phase2_readiness_gates.py --induce-gate memory_insufficient`
- Outcome: deterministic NO_GO (`exit code 1`) as expected for induced scenario.
- Key gate evidence:
  - `memory_quality: BLOCKED`
  - `precision=0.900000; adjudicated_sample=10; posture=insufficient_evidence`
  - `correct=9; incorrect=1`

4. `python3 scripts/run_phase2_validation_matrix.py`
- Outcome: PASS (`exit code 0`).
- Matrix summary:
  - `control_doc_truth: PASS`
  - `gate_contract_tests: PASS`
  - `readiness_gates: PASS`
  - `backend_integration_matrix: PASS`
  - `web_validation_matrix: PASS`
- Readiness default memory evidence confirms capture-derived behavior:
  - `memory_quality: PASS`
  - `precision=1.000000; adjudicated_sample=20; posture=on_track`

## Blockers/Issues
- Local DB access is required for readiness/matrix verification; initial non-escalated run was sandbox-blocked from connecting to local Postgres (`localhost:5432`).
- Verification completed successfully after rerunning with elevated local access.

## Explicit Deferred Scope
- No endpoint/schema contract changes.
- No connector/orchestration/worker/UI changes.
- No Phase 3 runtime/profile routing work.

## Recommended Next Step
1. Send sprint for reviewer PASS with this evidence bundle (targeted readiness test PASS, both induced memory scenarios deterministic NO_GO with expected posture, full Phase 2 validation matrix PASS).
