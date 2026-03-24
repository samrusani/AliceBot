# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 13: Gate Contract Test Canonicalization

## Sprint Type

hardening

## Sprint Reason

Sprint 11 made `run_phase2_*` canonical and reduced `run_mvp_*` to compatibility aliases. Two gate-script test files still target the old MVP-owned module internals and now fail (`tests/integration/test_mvp_readiness_gates.py`, `tests/integration/test_mvp_validation_matrix.py`). Because these tests are not in the default Phase 2 validation matrix, this drift can recur silently.

## Sprint Intent

Restore deterministic gate-contract coverage by updating stale gate-script tests to the Phase 2 canonical ownership model and include that coverage in the default Phase 2 validation matrix.

## Git Instructions

- Branch Name: `codex/phase2-sprint13-gate-contract-tests`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Current `main` is functionally on track (`python3 scripts/run_phase2_validation_matrix.py` passes), but hidden stale tests reduce confidence in gate-runner refactors.
- The failure mode is concrete and reproducible: stale imports from MVP alias scripts now missing canonical internals.
- This is a narrow hardening seam that improves MVP extensive-testing confidence without expanding product scope.

## Design Truth

- `run_phase2_*` scripts are canonical implementation sources.
- `run_mvp_*` scripts remain compatibility entrypoints only.
- Gate-contract tests must validate canonical behavior directly and alias compatibility behavior explicitly.

## Exact Surfaces In Scope

- gate-runner contract tests for readiness and validation matrix scripts
- phase2 validation-matrix wiring to include gate-contract tests
- sprint-scoped build/review reporting

## Exact Files In Scope

- [run_phase2_validation_matrix.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_phase2_validation_matrix.py)
- [test_mvp_readiness_gates.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_mvp_readiness_gates.py)
- [test_mvp_validation_matrix.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_mvp_validation_matrix.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `./.venv/bin/python -m pytest tests/integration/test_mvp_readiness_gates.py tests/integration/test_mvp_validation_matrix.py -q`
  - `python3 scripts/run_phase2_validation_matrix.py --induce-step gate_contract_tests`
  - `python3 scripts/run_phase2_validation_matrix.py`

## In Scope

- Update stale test expectations so gate-contract tests validate Phase 2 canonical modules (`scripts.run_phase2_readiness_gates`, `scripts.run_phase2_validation_matrix`) instead of relying on removed MVP-owned internals.
- Keep explicit coverage for MVP compatibility aliases where appropriate (entrypoint forwarding and output contract), without treating aliases as canonical implementation modules.
- Add one deterministic `gate_contract_tests` step to `scripts/run_phase2_validation_matrix.py` that executes the gate-contract test subset.
- Preserve deterministic induced-failure behavior and failing-step reporting for the new step.

## Out of Scope

- product/runtime endpoint changes
- schema/migration work
- memory/retrieval algorithm changes
- connector scope expansion
- UI feature changes
- workers/orchestration implementation
- Phase 3 runtime/profile routing implementation

## Required Deliverables

- stale gate-script tests updated and passing under the canonical ownership model
- validation matrix includes `gate_contract_tests` in deterministic step order
- induced-step behavior supports `--induce-step gate_contract_tests`
- updated sprint reports for this sprint only

## Acceptance Criteria

- `./.venv/bin/python -m pytest tests/integration/test_mvp_readiness_gates.py tests/integration/test_mvp_validation_matrix.py -q` passes.
- `scripts/run_phase2_validation_matrix.py` includes `gate_contract_tests` as a named step and reports it in results output.
- `python3 scripts/run_phase2_validation_matrix.py --induce-step gate_contract_tests` fails deterministically with explicit failing-step output.
- Full `python3 scripts/run_phase2_validation_matrix.py` remains PASS with the new step included.
- No product/runtime endpoint behavior changes are introduced.

## Implementation Constraints

- keep script behavior deterministic and non-interactive
- preserve existing readiness thresholds and matrix semantics
- keep test assertions machine-independent
- do not introduce external dependencies
- co-deliver verification commands with outcomes in reports

## Control Tower Task Cards

### Task 1: Gate Contract Tests
Owner: tooling operative  
Write scope:
- `tests/integration/test_mvp_readiness_gates.py`
- `tests/integration/test_mvp_validation_matrix.py`

### Task 2: Matrix Integration
Owner: tooling operative  
Write scope:
- `scripts/run_phase2_validation_matrix.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify canonical-vs-alias test boundaries are correct
- verify `gate_contract_tests` step determinism and reporting
- verify strict no-product-scope expansion
- verify reports and packet consistency

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact failing stale-test root cause before changes
- exact test-contract changes made for canonical ownership
- exact validation-matrix step delta
- exact verification commands run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained gate-contract-hardening scoped
- stale gate tests are restored and meaningful
- validation-matrix integration is deterministic and reviewer-clear
- no hidden scope expansion

## Exit Condition

This sprint is complete when gate-contract tests are aligned to the Phase 2 canonical runner model, included in default matrix execution, and deterministic failure signaling for that step is verified.
