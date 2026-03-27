# Phase 4 Readiness Gates

This runbook defines deterministic readiness prerequisites for Phase 4 Sprint 13.

## Canonical Command

Run from repo root:

1. `python3 scripts/run_phase4_readiness_gates.py`

## Gate Intent

Phase 4 readiness must preserve:

- explicit run transition evidence for non-happy-path states
- bounded retry posture and retry-cap enforcement
- explicit failure-class categorization (`transient`, `policy`, `approval`, `budget`, `fatal`)
- compatibility with the existing Phase 3 gate chain

## PASS Rule

- PASS only when the command exits `0`.
- FAIL when any readiness prerequisite is not measurable or deterministic.
