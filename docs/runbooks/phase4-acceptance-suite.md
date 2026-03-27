# Phase 4 Acceptance Suite

This runbook defines the Phase 4 acceptance entrypoint and required scenario evidence mapping for Sprint 13.

## Canonical Command

Run from repo root:

1. `python3 scripts/run_phase4_acceptance.py`

## Required Scenario Evidence Mapping

The acceptance chain must preserve deterministic evidence for:

- `run_progression_with_pause`: `tests/integration/test_task_runs_api.py::test_task_run_endpoints_cover_budget_wait_resume_pause_cancel_and_conflicts`
- `restart_safe_resume`: `tests/unit/test_approvals.py::test_approval_resolution_resumes_waiting_approval_run_only`
- `budget_exhaustion_fail_closed`: `tests/unit/test_task_runs.py::test_tick_sets_budget_exhaustion_as_failed_with_explicit_failure_class`
- `draft_first_tool_execution`: `tests/unit/test_proxy_execution.py::test_registered_proxy_handler_keys_are_sorted_and_explicit`
- `approval_resume_execution`: `tests/integration/test_proxy_execution_api.py::test_execute_approved_proxy_endpoint_marks_linked_run_failed_when_blocked`

## PASS Rule

- PASS only when the entrypoint exits `0` and all mapped scenario checks pass in the same run window.
- FAIL when any required scenario is missing, skipped, or non-deterministic.
