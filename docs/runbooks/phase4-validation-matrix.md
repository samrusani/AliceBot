# Phase 4 Validation Matrix

This runbook defines the deterministic Phase 4 validation chain used by Sprint 15 release-candidate rehearsal.

## Canonical Command

Run from repo root:

1. `python3 scripts/run_phase4_validation_matrix.py`
2. RC rehearsal entrypoint: `python3 scripts/run_phase4_release_candidate.py` (includes this matrix step)

## Validation Steps

The validation matrix executes these ordered steps:

1. `control_doc_truth`
2. `phase4_acceptance`
3. `phase4_readiness_gates`
4. `phase4_magnesium_ship_gate`
5. `phase4_scenarios`
6. `phase4_web_diagnostics`
7. `phase3_compat_validation`
8. `phase2_compat_validation`
9. `mvp_compat_validation`

## Canonical Magnesium Step

The `phase4_magnesium_ship_gate` step runs:

- `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence`

## Scenario Step Coverage

The `phase4_scenarios` step runs:

- `run_progression_with_pause`
- `restart_safe_resume`
- `budget_exhaustion_fail_closed`
- `draft_first_tool_execution`
- `approval_resume_execution`

## PASS Rule

- PASS only when every step reports `PASS`.
- NO_GO when any step fails.
- Failing step IDs are reported explicitly as `Failing steps: ...`.
- In RC rehearsal context, matrix failure marks overall `final_decision` as `NO_GO` in `artifacts/release/phase4_rc_summary.json`.
