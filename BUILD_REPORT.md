# BUILD_REPORT.md

## Sprint Objective
Add deterministic acceptance evidence that explicit-signal capture writes flow into resumption-brief context and remain included in the Phase 2 acceptance gate chain.

## Completed Work
- Added new deterministic acceptance scenario:
  - `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_explicit_signal_capture_flows_into_resumption_brief`
- Scenario setup seeds one thread with two `message.user` explicit-signal events (preference + commitment) and one assistant event.
- Scenario validates `POST /v0/memories/capture-explicit-signals` outcomes for both signals:
  - preference capture: candidate payload shape, `ADD` admission, and aggregate summary counts.
  - commitment capture: candidate payload shape, `ADD` admission, `open_loop.decision == "CREATED"`, and aggregate summary counts.
- Scenario validates continuity into `GET /v0/threads/{thread_id}/resumption-brief`:
  - open-loop section summary (`limit/returned_count/total_count/order`) and exact item continuity with created open-loop id/memory id/title.
  - memory-highlights section summary (`limit/returned_count/total_count/order`) and deterministic keys/values/source_event_ids for both captured memories.
- Updated `scripts/run_mvp_acceptance.py` to include the new scenario in gate execution.
- Confirmed `scripts/run_phase2_acceptance.py` executes the updated acceptance chain unchanged (no code changes required in alias script).

## Exact Runner Command List Delta
- Added scenario key in `ACCEPTANCE_SCENARIOS`:
  - `capture_resumption`
- Added acceptance node id in `ACCEPTANCE_TEST_NODE_IDS`:
  - `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_explicit_signal_capture_flows_into_resumption_brief`

## Explicit Assertions Proving Capture-To-Resumption Continuity
- Capture endpoint assertions prove persistence/admission outcomes:
  - preference candidate key/value/source metadata + summary counts.
  - commitment candidate key/value/open-loop title + `ADD` admission + `open_loop CREATED` summary counts.
- Resumption-brief assertions prove downstream continuity:
  - open-loop item equals created loop identity and title from capture output.
  - memory-highlights include both captured memory keys in deterministic order with expected values and source event ids.

## Incomplete Work
- None within sprint scope.

## Files Changed
- `tests/integration/test_mvp_acceptance_suite.py`
- `scripts/run_mvp_acceptance.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_mvp_acceptance_suite.py::test_acceptance_explicit_signal_capture_flows_into_resumption_brief`
- Outcome: PASS (`1 passed`, exit code `0`).

2. `python3 scripts/run_phase2_acceptance.py`
- Outcome: PASS (`4 passed`, exit code `0`).
- Includes updated acceptance chain containing the new scenario node id.

## Blockers/Issues
- Integration tests require local Postgres connectivity; sandboxed execution initially failed with connection permission errors.
- Verification completed successfully after running the required commands with escalated permissions.
- No API/contract changes were required.

## Deferred Scope (Explicit)
- Automation implementation: deferred (out of scope).
- Workers/orchestration implementation: deferred (out of scope).
- Phase 3 runtime/profile routing or orchestration: deferred (out of scope).

## Recommended Next Step
Proceed to Control Tower integration review to confirm sprint-scope adherence and acceptance-hardening evidence, then advance the sprint PR.
