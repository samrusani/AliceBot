# Phase 4 Readiness Gates

This runbook defines deterministic Phase 4 readiness prerequisites for Sprint 14 canonical gate ownership.

## Canonical Command

Run from repo root:

1. `python3 scripts/run_phase4_readiness_gates.py`

## Ordered Gate Contract

The readiness command executes these ordered gates:

1. `phase4_acceptance`
2. `canonical_magnesium_ship_gate`
3. `phase3_readiness_compat`

## PASS Rule

- PASS only when every readiness gate reports `PASS`.
- NO_GO when any readiness gate fails.
- Failing gate IDs are reported explicitly as `Failing gates: ...`.
