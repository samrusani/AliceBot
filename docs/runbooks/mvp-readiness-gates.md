# MVP Readiness Gates Runbook

## Objective
Run one deterministic command that produces quantitative MVP go/no-go evidence across acceptance, latency, cache reuse, and memory quality gates.

This readiness runner is also the first prerequisite step in `python3 scripts/run_mvp_validation_matrix.py`.

## Prerequisites
- Local dependencies installed (`python3 -m venv .venv` and `./.venv/bin/python -m pip install -e '.[dev]'`).
- Local Postgres available at the configured admin/app URLs.
- No extra API keys required for this readiness runner: model calls are stubbed for deterministic probe evidence.

## Exact Command
```bash
python3 scripts/run_mvp_readiness_gates.py
```

Expected behavior:
- Executes bounded gates in this order:
  - `acceptance_suite` (runs `python3 scripts/run_mvp_acceptance.py`)
  - `latency_p95` (`p95_seconds < 5.0`)
  - `cache_reuse` (`cache_reuse_ratio >= 0.70` when cached-token telemetry is present)
  - `memory_quality` (`precision > 0.80` and `adjudicated_sample >= 20`)
- Prints explicit `PASS`, `FAIL`, or `BLOCKED` per gate with measured values and thresholds.
- Returns exit code `0` only when every gate is `PASS`.
- Returns non-zero on any `FAIL` or `BLOCKED` gate.

## Gate Interpretation
- `acceptance_suite`
  - `PASS`: acceptance runner exit code is `0`.
  - `FAIL`: acceptance runner returned non-zero.

- `latency_p95`
  - measured from repeated retrieval-plus-response probe calls.
  - p95 uses deterministic nearest-rank math on probe durations.
  - `PASS` requires strictly `< 5.0` seconds.

- `cache_reuse`
  - ratio = `sum(cached_input_tokens) / sum(input_tokens)`.
  - `PASS` requires `>= 0.70`.
  - `BLOCKED` when cached-token telemetry is missing/invalid for any probe sample.

- `memory_quality`
  - derived from `/v0/memories/evaluation-summary` semantics.
  - `precision = correct / (correct + incorrect)` when denominator > 0.
  - `adjudicated_sample = correct + incorrect`.
  - `PASS` when precision and sample thresholds are met.
  - `FAIL` when adjudicated sample is sufficient but precision is at-or-below target (`<= 0.80`).
  - `BLOCKED` when adjudicated sample is below minimum or summary data is unavailable/invalid.

## Optional Deterministic Negative Checks
```bash
python3 scripts/run_mvp_readiness_gates.py --induce-gate acceptance_fail
python3 scripts/run_mvp_readiness_gates.py --induce-gate latency_fail
python3 scripts/run_mvp_readiness_gates.py --induce-gate cache_fail
python3 scripts/run_mvp_readiness_gates.py --induce-gate cache_blocked
python3 scripts/run_mvp_readiness_gates.py --induce-gate memory_needs_review
python3 scripts/run_mvp_readiness_gates.py --induce-gate memory_insufficient
```

These options intentionally force deterministic gate outcomes to validate reviewer signaling.

## Blocked-State Handling
- Treat any `BLOCKED` gate as no-go until evidence gaps are resolved.
- Do not treat blocked cache/memory gates as implicit pass.
- Re-run the full command after resolving the blocked condition.
