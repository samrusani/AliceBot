# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 9: Phase-2 Gate Wrapper Parity

## Sprint Type

hardening

## Sprint Reason

Phase 2 gate entrypoint scripts now exist and are used, but wrapper behavior (arg passthrough and exit-code passthrough) is only manually verified. The remaining risk is silent drift between wrapper behavior and underlying MVP runners.

## Sprint Intent

Add deterministic automated tests for Phase 2 wrapper parity and tighten wrapper robustness without changing gate semantics.

## Git Instructions

- Branch Name: `codex/phase2-sprint9-gate-wrapper-parity`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Phase 2 validation now runs through wrapper scripts in control flow.
- Current checks prove executability, but not full passthrough guarantees.
- This is the narrowest remaining seam before declaring Phase 2 gate tooling stable.

## Design Truth

- Preserve existing gate semantics and target-script mappings.
- Keep wrappers deterministic, non-interactive, and shell-compatible.
- Validate behavior via automated tests, not manual inspection only.

## Exact Surfaces In Scope

- phase2 gate wrapper scripts
- wrapper parity unit tests
- sprint-scoped script/test verification

## Exact Files In Scope

- [run_phase2_acceptance.py](scripts/run_phase2_acceptance.py)
- [run_phase2_readiness_gates.py](scripts/run_phase2_readiness_gates.py)
- [run_phase2_validation_matrix.py](scripts/run_phase2_validation_matrix.py)
- [test_phase2_gate_wrappers.py](tests/unit/test_phase2_gate_wrappers.py)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `PYTHONPATH=$PWD .venv/bin/pytest tests/unit/test_phase2_gate_wrappers.py`

## In Scope

- Add automated tests that assert for each phase2 wrapper:
  - forwards all CLI args unchanged to target MVP script
  - executes with repo-root cwd
  - returns subprocess exit code unchanged
  - keeps expected target script mapping
- Add deterministic fallback-path coverage:
  - venv python selected when present
  - `sys.executable` selected when venv missing
- Optional small wrapper hardening if needed for testability:
  - extract shared wrapper-run helper, preserving existing behavior
  - avoid changing user-facing CLI surface

## Out of Scope

- any product/runtime API change
- docs truth-sync edits outside direct wrapper references
- UI changes
- workers/automation/orchestration implementation
- Phase 3 runtime/profile routing implementation

## Required Deliverables

- wrapper parity test suite committed and passing
- phase2 wrappers verified to preserve arg/exit-code passthrough semantics
- updated sprint reports for this sprint only

## Acceptance Criteria

- tests cover all three wrappers and pass
- tests assert deterministic arg passthrough behavior
- tests assert deterministic exit-code passthrough behavior
- tests assert wrapper target-script mapping and Python executable resolution behavior
- no gate semantics changed versus current alias behavior
- no out-of-scope implementation work enters sprint

## Implementation Constraints

- keep script behavior deterministic and non-interactive
- use machine-independent assertions in tests
- do not introduce external dependencies for tests
- co-deliver verification commands with outcomes in reports

## Control Tower Task Cards

### Task 1: Wrapper Test Coverage
Owner: tooling operative  
Write scope:
- `scripts/run_phase2_acceptance.py`
- `scripts/run_phase2_readiness_gates.py`
- `scripts/run_phase2_validation_matrix.py`
- `tests/unit/test_phase2_gate_wrappers.py`

### Task 2: Integration Review
Owner: control tower  
Responsibilities:
- verify wrapper parity evidence completeness
- verify no behavior drift in gate aliases
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact wrapper/test files changed
- exact parity guarantees asserted by tests
- exact verification commands run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained wrapper-parity scoped
- wrapper/test consistency and completeness
- verification evidence is sufficient for script-hardening sprint
- no hidden scope expansion

## Exit Condition

This sprint is complete when automated tests prove Phase 2 gate wrappers preserve arg/exit-code passthrough semantics for all three wrappers, with no product/runtime behavior change.
