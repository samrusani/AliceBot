# BUILD_REPORT

## Sprint Objective

Implement `P12-S4` public eval harness so Alice can run reproducible local eval suites, persist suite/case/run/result records, emit stable baseline report artifacts, and document what the measured quality surface means.

## Completed Work

- Added public eval persistence tables for `eval_suites`, `eval_cases`, `eval_runs`, and `eval_results`.
- Added `alicebot_api.public_evals` with:
  - fixture-catalog loading
  - suite/case syncing into the database
  - fixture-backed recall, resumption, correction, contradiction, and open-loop evaluators
  - canonical report generation with stable digests
  - report writing helper for checked-in baseline artifacts
- Added current-branch public eval API surfaces:
  - `GET /v1/evals/suites`
  - `POST /v1/evals/runs`
  - `GET /v1/evals/runs`
  - `GET /v1/evals/runs/{eval_run_id}`
- Made the checked-in fixture catalog authoritative for suite listing and run selection.
- Added pruning for persisted suite/case rows so removed catalog entries do not survive as stale runtime state.
- Added explicit validation for unknown `suite_key` filters instead of silently returning partial or empty runs.
- Added CLI surfaces:
  - `alicebot evals suites`
  - `alicebot evals run`
  - `alicebot evals runs`
  - `alicebot evals show`
- Added public fixture definitions in `eval/fixtures/public_eval_suites.json`.
- Added checked-in current-branch baseline report artifact in `eval/baselines/public_eval_harness_v1.json`, with final committed artifact format still pending Control Tower confirmation.
- Added sprint-owned docs in `docs/evals/public_eval_harness.md`, explicitly framed as current branch behavior where API and artifact decisions are still pending.
- Added focused unit and integration coverage for the runner, migration, API, CLI, and baseline reproduction path.

## Incomplete Work

- None inside the sprint packet scope.

## Files Changed

- `BUILD_REPORT.md`
- `RULES.md`
- `ARCHITECTURE.md`
- `CURRENT_STATE.md`
- `.ai/handoff/CURRENT_STATE.md`
- `PRODUCT_BRIEF.md`
- `ROADMAP.md`
- `REVIEW_REPORT.md`
- `apps/api/alembic/versions/20260414_0060_phase12_public_eval_harness.py`
- `apps/api/src/alicebot_api/cli.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/public_evals.py`
- `apps/api/src/alicebot_api/store.py`
- `scripts/check_control_doc_truth.py`
- `docs/evals/public_eval_harness.md`
- `eval/baselines/public_eval_harness_v1.json`
- `eval/fixtures/public_eval_suites.json`
- `tests/integration/test_cli_integration.py`
- `tests/integration/test_public_evals_api.py`
- `tests/unit/test_20260414_0060_phase12_public_eval_harness.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_main.py`
- `tests/unit/test_public_evals.py`

## Tests Run

- `./.venv/bin/pytest tests/unit/test_public_evals.py tests/unit/test_20260414_0060_phase12_public_eval_harness.py tests/unit/test_cli.py tests/unit/test_main.py tests/integration/test_public_evals_api.py tests/integration/test_cli_integration.py tests/integration/test_retrieval_evaluation_api.py -q`
  - Result: PASS (`83 passed`)
- `./.venv/bin/python scripts/check_control_doc_truth.py`
  - Result: PASS
- `rg -n "/Users|samirusani|Desktop/Codex" RULES.md ARCHITECTURE.md CURRENT_STATE.md .ai/handoff/CURRENT_STATE.md PRODUCT_BRIEF.md ROADMAP.md docs/evals eval/fixtures eval/baselines`
  - Result: PASS (no matches)

## Blockers/Issues

- No sprint blocker remains.
- The recall suite keeps one non-gating coverage snapshot for entity-edge expansion. It records the current shipped output with `score=0.0` while the suite still passes because the catalog marks that case as observational rather than a strict gate.
- Final product policy is still pending for the Control Tower decisions called out in the sprint packet, including the committed artifact format and whether `/v1/evals/*` remains part of the accepted Phase 12 surface.

## Recommended Next Step

Request Control Tower merge review against the current `P12-S4` branch head.
