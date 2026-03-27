# Phase 4 Validation Matrix

This runbook defines the deterministic Phase 4 validation chain for Sprint 13.

## Canonical Command

Run from repo root:

1. `python3 scripts/run_phase4_validation_matrix.py`

## Validation Steps

The validation matrix executes these ordered steps:

1. `control_doc_truth`
2. `phase4_acceptance`
3. `phase4_readiness_gates`
4. `phase4_scenarios`
5. `phase4_web_diagnostics`
6. `phase3_compat_validation`

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
