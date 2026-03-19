# SPRINT_PACKET.md

## Sprint Title

Sprint 7G: MVP Extensive Validation Matrix

## Sprint Type

qa

## Sprint Reason

Sprint 7F proved quantitative readiness gates and passed review. The remaining MVP risk is practical testing confidence: evidence is still split across multiple backend and web commands, which makes “thoroughly test the agent/os” slower and easier to execute inconsistently.

## Sprint Intent

Create one deterministic MVP validation matrix runner (plus tests and runbook) that executes the shipped end-to-end backend and web verification surfaces from a single command and outputs a clear go/no-go result.

## Git Instructions

- Branch Name: `codex/sprint-7g-mvp-extensive-validation-matrix`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- MVP-critical seams are shipped and quantitative gates now pass, but practical confidence still depends on running scattered commands manually.
- We need one reproducible “extensive testing” entrypoint for backend and web behavior together.
- A deterministic validation matrix reduces release risk without adding product scope.

## Design Truth

- This is a verification sprint, not a feature sprint.
- Reuse existing shipped seams and tests; do not widen product, connector, or architecture scope.
- Keep output explicit and reviewer-friendly with deterministic pass/fail reporting.

## Exact Surfaces In Scope

- Validation orchestration over shipped backend + web test surfaces.
- Single-command extensive testing entrypoint and deterministic summary output.
- Runbook/report alignment for reproducible reviewer execution.

## Exact Files In Scope

- [run_mvp_validation_matrix.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_validation_matrix.py)
- [run_mvp_acceptance.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_acceptance.py)
- [run_mvp_readiness_gates.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_readiness_gates.py)
- [test_mvp_validation_matrix.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_mvp_validation_matrix.py)
- [package.json](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/package.json)
- [vitest.config.ts](/Users/samirusani/Desktop/Codex/AliceBot/apps/web/vitest.config.ts)
- [mvp-validation-matrix.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-validation-matrix.md)
- [mvp-readiness-gates.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-readiness-gates.md)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)

## In Scope

- Add `scripts/run_mvp_validation_matrix.py` that runs a deterministic sequence and reports per-step status plus final `PASS`/`NO_GO`.
- Sequence must include:
  - readiness gates (`python3 scripts/run_mvp_readiness_gates.py`)
  - bounded backend integration matrix covering shipped seams (continuity, responses, approvals/execution, tasks/steps, traces, memory/entities/artifacts, Gmail/Calendar account seams)
  - bounded web test matrix covering shipped operator shell surfaces (`/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, `/traces`) through existing Vitest suites
- Add deterministic integration tests for matrix runner behavior (pass/fail propagation, output shape, exit code contract).
- Add runbook documentation with prerequisites, exact command, expected runtime class, and failure triage flow.

## Out of Scope

- No new endpoints, migrations, or schema changes.
- No connector breadth expansion or write-capable connector behavior.
- No auth, orchestration, or worker-runtime expansion.
- No new web routes or UI redesign.
- No feature behavior changes beyond testability/verification wiring.

## Required Deliverables

- `scripts/run_mvp_validation_matrix.py` committed and runnable.
- `tests/integration/test_mvp_validation_matrix.py` committed with deterministic runner-contract coverage.
- `docs/runbooks/mvp-validation-matrix.md` committed and aligned to executable commands.
- Updated `BUILD_REPORT.md` and `REVIEW_REPORT.md` reflecting Sprint 7G only.

## Acceptance Criteria

- `python3 scripts/run_mvp_validation_matrix.py` executes the defined matrix and exits `0` only when all steps pass.
- A single induced step failure causes deterministic non-zero exit and explicit failing-step output.
- Matrix includes both backend and web verification commands defined in this sprint packet.
- `python3 scripts/run_mvp_readiness_gates.py` remains part of the matrix prerequisite chain and passes in reviewer environment.
- Sprint remains within QA/test orchestration and documentation surfaces only.

## Implementation Constraints

- Keep matrix commands explicit and stable; avoid hidden autodiscovery.
- Do not add flaky timing assertions to web/backend suites in this sprint.
- Prefer reusing existing tests over inventing broad new coverage surfaces.
- Keep runtime bounded and practical for local reviewer use.

## Suggested Work Breakdown

1. Define the exact backend + web validation command list and output contract.
2. Implement `scripts/run_mvp_validation_matrix.py` with deterministic sequencing and exit-code behavior.
3. Add `tests/integration/test_mvp_validation_matrix.py` for pass/fail propagation and output assertions.
4. Add `docs/runbooks/mvp-validation-matrix.md` with execution and triage flow.
5. Run matrix command(s), capture evidence, and update sprint reports.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact matrix steps executed (backend + web + readiness prerequisite)
- exact command(s) and environment assumptions
- per-step outcome table with duration and exit status
- induced-failure verification summary
- explicit deferred criteria not covered by this sprint

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed within extensive-validation scope
- matrix runner output is deterministic and actionable
- backend and web verification coverage in the matrix matches this packet
- no hidden product/backend scope entered

## Exit Condition

This sprint is complete when one documented command provides deterministic, reviewer-ready extensive test evidence across shipped backend and web surfaces with explicit pass/fail output and no product scope expansion.
