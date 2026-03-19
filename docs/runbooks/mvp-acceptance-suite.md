# MVP Acceptance Suite Runbook

## Objective
Run one deterministic acceptance suite that validates shipped MVP-critical journeys and returns a single reviewer-ready pass/fail signal.

## Prerequisites
- Local dependencies installed (`python3 -m venv .venv` and `./.venv/bin/python -m pip install -e '.[dev]'`).
- Postgres stack available (for example `docker compose up -d`).
- Migrations applied (`./scripts/migrate.sh`).

## Included Acceptance Scenarios
- `response_memory`:
  - context-aware response uses admitted memory evidence
  - preference correction is reflected in subsequent compile + response flow
- `approval_execution`:
  - approval-required request lifecycle (pending -> approved -> executed) stays linked
  - consequential trace evidence remains queryable
- `magnesium_reorder`:
  - canonical magnesium reorder flow preserves explicit memory write-back evidence

## Exact Command (Normal)
```bash
python3 scripts/run_mvp_acceptance.py
```

Expected behavior:
- Runs this bounded subset only:
  - `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_response_path_uses_admitted_memory_and_preference_correction`
  - `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_approval_lifecycle_resolution_execution_and_trace_availability`
  - `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence`
- Exit code `0` means PASS.
- Any non-zero exit code means FAIL.

## Exact Command (Induced-Failure Check)
```bash
python3 scripts/run_mvp_acceptance.py --induce-failure approval_execution
```

Expected behavior:
- Intentionally fails exactly the selected scenario via `MVP_ACCEPTANCE_INDUCED_FAILURE_SCENARIO`.
- Returns non-zero exit code and prints `MVP acceptance suite result: FAIL (...)`.
- This validates deterministic negative signaling for reviewers.

Other valid induced-failure scenario names:
- `response_memory`
- `approval_execution`
- `magnesium_reorder`

## Optional Direct Pytest Command
```bash
./.venv/bin/python -m pytest tests/integration/test_mvp_acceptance_suite.py
```

## Non-Goals / Deferred Criteria
- No backend contract expansion, migrations, or schema changes.
- No UI validation, UI latency metrics, or end-user workflow UX checks.
- No connector breadth expansion or auth/orchestration changes.
- No load/performance characterization beyond deterministic functional acceptance evidence.
