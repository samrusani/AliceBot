# SPRINT_PACKET.md

## Sprint Title

Sprint 7I: Memory Quality Ship-Margin Hardening

## Sprint Type

qa

## Sprint Reason

Sprint 7H aligned canonical docs and gate usage. The remaining MVP release risk is memory-quality confidence margin: current readiness evidence sits at the floor (`precision=0.800000`, sample `10`), while the product brief requires memory extraction precision to exceed 80% at ship.

## Sprint Intent

Tighten memory-quality readiness gating from minimum-threshold posture to ship-margin posture, with deterministic evidence and no product-scope expansion.

## Git Instructions

- Branch Name: `codex/sprint-7i-memory-quality-ship-margin`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- MVP validation matrix now runs end-to-end and passes.
- Memory quality is currently just at the pass floor rather than above it.
- We need stronger deterministic evidence before calling MVP truly ship-ready.

## Design Truth

- This is a QA/readiness sprint, not a feature sprint.
- Keep scope on gate math, deterministic seed/evidence, and runbook/report alignment.
- Do not widen connectors, auth, orchestration, or UI feature scope.

## Exact Surfaces In Scope

- Memory-quality gate thresholds and posture logic in readiness tooling.
- Deterministic readiness seed profile used by gate probes.
- Readiness/validation runbooks and sprint reports.

## Exact Files In Scope

- [run_mvp_readiness_gates.py](scripts/run_mvp_readiness_gates.py)
- [run_mvp_validation_matrix.py](scripts/run_mvp_validation_matrix.py)
- [test_mvp_readiness_gates.py](tests/integration/test_mvp_readiness_gates.py)
- [test_mvp_validation_matrix.py](tests/integration/test_mvp_validation_matrix.py)
- [memory-quality-gate.md](docs/runbooks/memory-quality-gate.md)
- [mvp-readiness-gates.md](docs/runbooks/mvp-readiness-gates.md)
- [mvp-validation-matrix.md](docs/runbooks/mvp-validation-matrix.md)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Update memory gate criterion to ship-margin semantics:
  - `precision > 0.80` (strictly greater, not equal)
  - `adjudicated_sample >= 20`
- Update deterministic readiness seed profile so normal gate run can pass only with new margin.
- Update readiness gate tests to cover boundary behavior explicitly:
  - `precision == 0.80` must not pass
  - insufficient sample remains `BLOCKED`
- Ensure validation matrix behavior stays deterministic with the updated readiness gate.
- Align runbooks with the stricter memory-quality semantics and interpretation.

## Out of Scope

- No new endpoints, migrations, or schema changes.
- No connector breadth expansion or write-capable connector behavior.
- No auth, orchestration, or worker-runtime expansion.
- No UI feature scope changes.
- No new product behavior beyond readiness evidence hardening.

## Required Deliverables

- Updated readiness gate implementation and tests with strict memory-margin criteria.
- Updated runbooks reflecting strict threshold and larger minimum sample.
- Updated `BUILD_REPORT.md` and `REVIEW_REPORT.md` for Sprint 7I only.

## Acceptance Criteria

- `python3 scripts/run_mvp_readiness_gates.py` returns `PASS` only when `precision > 0.80` and `adjudicated_sample >= 20`.
- A boundary case with `precision == 0.80` is verified as non-pass (`FAIL` or `NO_GO` path).
- `python3 scripts/run_mvp_validation_matrix.py` remains deterministic with explicit `PASS/NO_GO`.
- Sprint remains within QA/readiness + docs/report scope only.

## Implementation Constraints

- Keep threshold/math changes explicit, deterministic, and test-backed.
- Do not weaken existing gate semantics for latency/cache/acceptance.
- Keep changes narrow to listed files.

## Suggested Work Breakdown

1. Update memory gate constants and posture logic in `scripts/run_mvp_readiness_gates.py`.
2. Update deterministic seed profile to satisfy strict ship-margin target on normal run.
3. Add/adjust integration tests for new boundary and sample semantics.
4. Validate readiness runner and matrix runner behavior with normal + induced-failure runs.
5. Update runbooks and sprint reports.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact updated threshold semantics (`>0.80`, sample `>=20`)
- exact commands run and pass/fail outcomes
- boundary-test evidence for `precision == 0.80`
- induced-failure evidence remains deterministic
- explicit deferred criteria not covered by this sprint

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed within readiness-hardening scope
- gate math matches Product Brief ship semantics
- deterministic behavior remains intact in readiness + matrix runners
- no hidden product/backend scope entered

## Exit Condition

This sprint is complete when memory-quality gating has ship-margin strictness (`precision > 0.80`, sample `>=20`) with deterministic evidence and unchanged product scope.
