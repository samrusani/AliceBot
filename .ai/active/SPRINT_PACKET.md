# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 10: Capture-To-Resumption Acceptance Evidence

## Sprint Type

hardening

## Sprint Reason

Phase 2 core seams are shipped (explicit-signal capture, manual chat capture controls, deterministic resumption briefs), but the acceptance suite does not yet prove this full chain as one governed scenario. Remaining risk is claiming Phase 2 readiness without end-to-end acceptance evidence for this path.

## Sprint Intent

Add deterministic acceptance evidence that explicit-signal capture writes flow through to resumption-brief context and remains stable under Phase 2 gate execution.

## Git Instructions

- Branch Name: `codex/phase2-sprint10-capture-resumption-acceptance`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Phase 2 validation is green, but acceptance coverage is still centered on legacy MVP scenarios.
- The highest-value missing proof is capture -> memory/open-loop persistence -> resumption brief inclusion.
- This is the narrowest high-signal seam before Phase 2 completion call.

## Design Truth

- Reuse shipped endpoints/contracts; do not invent parallel test-only behavior.
- Keep acceptance scenario deterministic and database-backed.
- Treat acceptance evidence as release artifact, not ad hoc test output.

## Exact Surfaces In Scope

- integration acceptance scenario for capture-to-resumption chain
- phase2/mvp acceptance runner inclusion
- sprint-scoped gate verification

## Exact Files In Scope

- [test_mvp_acceptance_suite.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_mvp_acceptance_suite.py)
- [run_mvp_acceptance.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_acceptance.py)
- [run_phase2_acceptance.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_phase2_acceptance.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_mvp_acceptance_suite.py::test_acceptance_explicit_signal_capture_flows_into_resumption_brief`
  - `python3 scripts/run_phase2_acceptance.py`

## In Scope

- Add one new deterministic acceptance scenario that proves:
  - a user `message.user` event containing explicit preference + commitment signals
  - `POST /v0/memories/capture-explicit-signals` yields expected candidate/admission/open-loop outcomes
  - `GET /v0/threads/{thread_id}/resumption-brief` includes resulting open loop + memory highlight evidence
- Include this scenario in acceptance runner command list (`scripts/run_mvp_acceptance.py`) so it is part of gate evidence.
- Ensure Phase 2 acceptance alias (`scripts/run_phase2_acceptance.py`) executes updated acceptance chain unchanged.
- Keep scenario deterministic (stable ordering assertions, explicit expected fields, no timing-sensitive heuristics).

## Out of Scope

- any product/runtime API change
- UI feature changes
- docs truth-sync edits outside sprint reports
- workers/automation/orchestration implementation
- Phase 3 runtime/profile routing implementation

## Required Deliverables

- acceptance scenario committed and passing
- acceptance runner updated to include scenario
- phase2 acceptance alias verified with updated chain
- updated sprint reports for this sprint only

## Acceptance Criteria

- new acceptance test passes and is deterministic
- `run_mvp_acceptance.py` includes and executes the new scenario
- `run_phase2_acceptance.py` runs the updated acceptance chain successfully
- evidence demonstrates capture-to-resumption path without regressions to existing acceptance scenarios
- no endpoint contract changes are required to satisfy this sprint
- no out-of-scope implementation work enters sprint

## Implementation Constraints

- keep script behavior deterministic and non-interactive
- use machine-independent assertions in tests
- do not introduce external dependencies for tests
- co-deliver verification commands with outcomes in reports

## Control Tower Task Cards

### Task 1: Acceptance Scenario
Owner: tooling operative  
Write scope:
- `tests/integration/test_mvp_acceptance_suite.py`
- `scripts/run_mvp_acceptance.py`
- `scripts/run_phase2_acceptance.py`

### Task 2: Integration Review
Owner: control tower  
Responsibilities:
- verify capture-to-resumption evidence completeness
- verify acceptance chain integrity
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact acceptance scenario added
- exact runner command list delta
- explicit assertions proving capture-to-resumption continuity
- exact verification commands run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained capture-resumption-acceptance scoped
- acceptance/test-runner consistency and completeness
- verification evidence is sufficient for acceptance-hardening sprint
- no hidden scope expansion

## Exit Condition

This sprint is complete when deterministic acceptance evidence exists for explicit-signal capture flowing into resumption brief context, is included in phase2 acceptance runner execution, and no product/runtime behavior changed outside test/gate orchestration.
