# Phase 4 Acceptance Suite

This runbook defines the canonical Phase 4 acceptance command contract for Sprint 14 MVP ship-gate ownership.

## Canonical Command

Run from repo root:

1. `python3 scripts/run_phase4_acceptance.py`

## Required Scenario Evidence Mapping

The acceptance chain is deterministic and must include these scenario-to-evidence mappings:

- `response_memory`: `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_response_path_uses_admitted_memory_and_preference_correction`
- `capture_resumption`: `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_explicit_signal_capture_flows_into_resumption_brief`
- `approval_execution`: `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_approval_lifecycle_resolution_execution_and_trace_availability`
- `magnesium_reorder`: `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence`

The `magnesium_reorder` scenario is the canonical MVP ship-gate flow:
`request -> approval -> execution -> memory write-back`.

## PASS Rule

- PASS only when the command exits `0` and all mapped scenario checks pass.
- FAIL when any mapped scenario is missing, skipped, or non-deterministic.
