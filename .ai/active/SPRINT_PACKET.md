# SPRINT_PACKET.md

## Sprint Title

Sprint 7F: MVP Quantitative Gate Evidence

## Sprint Type

qa

## Sprint Reason

Sprint 7E proved qualitative MVP journeys with deterministic acceptance tests. The remaining ship risk is quantitative gate evidence: p95 response latency, prompt/cache reuse evidence, and memory quality gate posture in one auditable pass/fail package.

## Sprint Intent

Create one bounded MVP readiness gate runner (plus tests and runbook) that produces a deterministic go/no-go signal for quantitative MVP criteria without widening product or connector scope.

## Git Instructions

- Branch Name: `codex/sprint-7f-mvp-quantitative-gate-evidence`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- The Product Brief ship criteria include quantitative thresholds not yet covered by one deterministic command.
- Sprint 7E’s acceptance suite can now be treated as prerequisite evidence and reused directly.
- Review and merge decisions need one scorecard artifact instead of separate ad hoc checks.

## Design Truth

- This is a readiness-evidence sprint, not a new-feature sprint.
- Reuse shipped seams only; do not introduce new business capabilities.
- Prefer deterministic, reviewer-friendly output over broad benchmarking frameworks.

## Exact Surfaces In Scope

- Response usage telemetry normalization for cache-reuse evidence.
- Deterministic MVP readiness runner for quantitative gates.
- Runbook/report alignment for reproducible reviewer execution.

## Exact Files In Scope

- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [response_generation.py](apps/api/src/alicebot_api/response_generation.py)
- [test_response_generation.py](tests/unit/test_response_generation.py)
- [test_responses_api.py](tests/integration/test_responses_api.py)
- [test_mvp_acceptance_suite.py](tests/integration/test_mvp_acceptance_suite.py)
- [test_mvp_readiness_gates.py](tests/integration/test_mvp_readiness_gates.py)
- [run_mvp_acceptance.py](scripts/run_mvp_acceptance.py)
- [run_mvp_readiness_gates.py](scripts/run_mvp_readiness_gates.py)
- [memory-quality-gate.md](docs/runbooks/memory-quality-gate.md)
- [mvp-readiness-gates.md](docs/runbooks/mvp-readiness-gates.md)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Extend response-usage parsing to capture optional cache-reuse telemetry when provider payload includes cached input-token details, while remaining backward compatible.
- Add deterministic tests for usage parsing and response-trace payload shape when cache telemetry is absent/present.
- Add `scripts/run_mvp_readiness_gates.py` that runs a bounded gate sequence and prints explicit status per gate:
  - acceptance suite gate (reusing `scripts/run_mvp_acceptance.py`)
  - latency gate (`p95 < 5.0s`) on repeated retrieval-plus-response probe calls
  - cache-reuse gate (`>= 0.70`) when cached-token telemetry is available; otherwise explicit blocked status
  - memory-quality gate posture from shipped memory evaluation summary semantics
- Add `tests/integration/test_mvp_readiness_gates.py` to validate runner determinism, threshold math, and exit-code behavior.
- Add/align runbook documentation with prerequisites, command(s), interpretation, and blocked-state handling.

## Out of Scope

- No new endpoints, migrations, or schema changes.
- No connector breadth expansion (Gmail/Calendar/search/write flows).
- No auth, orchestration, or worker-runtime expansion.
- No web UI redesign or new route work.
- No changes to product scope or non-gate behavior.

## Required Deliverables

- `scripts/run_mvp_readiness_gates.py` committed and runnable.
- Integration coverage for readiness-runner logic and gate math.
- Usage parsing updates plus test coverage for optional cached-token telemetry.
- `docs/runbooks/mvp-readiness-gates.md` committed and aligned to executable commands.
- Updated `BUILD_REPORT.md` and `REVIEW_REPORT.md` reflecting Sprint 7F only.

## Acceptance Criteria

- `python3 scripts/run_mvp_readiness_gates.py` runs the bounded gates and exits non-zero on any failed/blocked gate.
- Latency gate computes p95 deterministically from measured probe durations and enforces `< 5.0s`.
- Cache-reuse gate computes ratio from captured token telemetry when available and enforces `>= 0.70`; missing telemetry is explicit and does not report false pass.
- Memory-quality gate math aligns with shipped runbook semantics (`precision >= 0.80`, adjudicated sample >= 10).
- `python3 scripts/run_mvp_acceptance.py` remains passing as a prerequisite gate.
- Sprint stays within listed QA/telemetry/runbook surfaces.

## Implementation Constraints

- Keep usage contract changes additive/backward-compatible.
- Keep runner deterministic with explicit scenario names and threshold constants.
- Do not rely on flaky timing assertions inside unit tests; isolate gate math from environment jitter.
- Reuse existing API seams and fixtures; avoid parallel bespoke evaluation pipelines.

## Suggested Work Breakdown

1. Add optional cached-token telemetry plumbing in response usage contracts/parsing with unit tests.
2. Implement gate-math helpers for latency and cache-reuse decisions.
3. Implement `scripts/run_mvp_readiness_gates.py` with explicit output and exit behavior.
4. Add integration tests for runner pass/fail/blocked outcomes.
5. Add `docs/runbooks/mvp-readiness-gates.md` and align memory-gate references.
6. Execute commands, capture evidence, and update sprint reports.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact readiness gates executed
- exact command(s) and environment assumptions
- per-gate outcome table with measured values and thresholds
- blocked/insufficient-evidence handling summary (if any)
- explicit deferred criteria not covered by this sprint

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed within readiness-evidence scope
- cache and latency gate math is correct and deterministic
- runner output is actionable for merge/go-no-go decisions
- no hidden product/backend scope entered

## Exit Condition

This sprint is complete when one documented command produces deterministic, reviewer-ready quantitative MVP gate evidence (acceptance prerequisite, latency, cache reuse, memory quality posture) with explicit pass/fail/blocked states and no product scope expansion.
