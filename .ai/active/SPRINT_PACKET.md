# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 14: MVP Ship-Gate Canonicalization and Gate Ownership

## Sprint Type

feature

## Sprint Reason

Sprint 13 closed run observability and failure discipline. The next non-redundant gap is release-control ownership: Phase 4 gate entrypoints still delegate through older phase wrappers, which creates planning drift and repeated sprint confusion.

## Sprint Intent

Make Phase 4 the canonical MVP release gate by owning acceptance/readiness/validation semantics directly, embedding canonical magnesium reorder evidence in the Phase 4 chain, and keeping compatibility gates green.

## Git Instructions

- Branch Name: `codex/phase4-sprint-14-mvp-ship-gate-canonicalization`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It removes wrapper-on-wrapper gate ambiguity (`phase4 -> phase3 -> phase2`) that causes redundant planning cycles.
- It aligns release-control with product truth: canonical MVP scenario is magnesium reorder with explicit approval and memory write-back evidence.
- It enables clear go/no-go ownership at Phase 4 without reopening runtime implementation seams already delivered.

## Redundancy Guard

- Already shipped in Sprint 12:
  - run-aware execution linkage and idempotent replay controls
  - approval pause/resume continuity for linked runs
- Already shipped in Sprint 13:
  - run transition/stop-reason observability
  - retry posture and failure classification discipline
  - Phase 4 runner entrypoints and baseline runbooks
- Required now (Sprint 14):
  - Phase 4 gate semantics become canonical, not only compatibility wrappers
  - canonical MVP magnesium ship-gate evidence is first-class in Phase 4 acceptance/matrix contracts
  - explicit anti-drift control-doc truth for Phase 4 ownership
- Explicitly out of Sprint 14:
  - new runtime/task-run schema changes
  - connector/auth/platform scope expansion
  - workflow engine/orchestration redesign

## Design Truth

- Phase 4 release-control is the canonical MVP go/no-go chain.
- Canonical scenario remains:
  - request -> approval -> execution -> memory write-back (magnesium reorder)
- Compatibility must remain:
  - `python3 scripts/run_phase3_validation_matrix.py` PASS
  - `python3 scripts/run_phase2_validation_matrix.py` PASS
  - `python3 scripts/run_mvp_validation_matrix.py` PASS
- Control-doc truth must describe current ownership without stale phase narratives.

## Exact Surfaces In Scope

- Phase 4 acceptance/readiness/validation script ownership
- canonical MVP ship-gate scenario mapping in Phase 4 acceptance/matrix docs and scripts
- deterministic gate-contract tests for Phase 4 scripts
- control-doc truth checker updates for Phase 4 canonical ownership
- canonical docs synchronization to avoid review packet drift

## Exact Files In Scope

- `scripts/run_phase4_acceptance.py`
- `scripts/run_phase4_readiness_gates.py`
- `scripts/run_phase4_validation_matrix.py`
- `scripts/check_control_doc_truth.py`
- `docs/runbooks/phase4-acceptance-suite.md`
- `docs/runbooks/phase4-readiness-gates.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/mvp-ship-gate-magnesium-reorder.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `tests/unit/test_phase4_gate_wrappers.py`
- `tests/integration/test_phase4_acceptance_suite.py`
- `tests/integration/test_phase4_readiness_gates.py`
- `tests/integration/test_phase4_validation_matrix.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Replace simple Phase 4 wrapper delegation with explicit Phase 4 gate command contracts and deterministic step ownership.
- Ensure Phase 4 acceptance includes canonical magnesium reorder scenario evidence mapping.
- Ensure Phase 4 validation matrix executes ordered, deterministic steps and reports failing step IDs clearly.
- Add/expand Phase 4 gate contract tests (unit/integration) similar rigor to existing Phase 2 matrix contracts.
- Update control-doc truth checks so required markers and disallowed markers reflect current Phase 4 canonical ownership.
- Keep Phase 3/Phase 2/MVP compatibility commands functional and explicitly verified.

## Out of Scope

- `apps/api/src/alicebot_api/*` runtime behavior/schema changes
- `workers/alicebot_worker/*` runtime behavior changes
- connector breadth expansion (Gmail/Calendar)
- auth model changes
- platform/channel expansion
- proactive automation/voice/browser automation

## Required Deliverables

- canonical Phase 4 gate scripts with deterministic, test-backed contracts
- explicit magnesium ship-gate scenario coverage in Phase 4 acceptance/matrix chain
- Phase 4 gate contract test suite additions
- updated Phase 4 runbooks and closeout packet text aligned to actual script behavior
- updated control docs and control-doc truth rules reflecting current ownership
- sprint-scoped build/review reports

## Acceptance Criteria

- `python3 scripts/run_phase4_acceptance.py` passes and includes canonical magnesium scenario evidence mapping.
- `python3 scripts/run_phase4_readiness_gates.py` passes with deterministic gate output.
- `python3 scripts/run_phase4_validation_matrix.py` passes with deterministic ordered step output and explicit failing-step reporting contract.
- `./.venv/bin/python -m pytest tests/integration/test_phase4_acceptance_suite.py tests/integration/test_phase4_readiness_gates.py tests/integration/test_phase4_validation_matrix.py tests/unit/test_phase4_gate_wrappers.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_mvp_acceptance_suite.py::test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence -q` passes.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- `python3 scripts/run_mvp_validation_matrix.py` remains PASS.
- `python3 scripts/check_control_doc_truth.py` passes with updated Phase 4 ownership markers.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` are synchronized to Sprint 14 ownership truth.

## Implementation Constraints

- do not introduce new dependencies
- do not change delivered Sprint 12/13 runtime semantics
- preserve deterministic command contracts and explicit pass/fail signals
- preserve backward compatibility for Phase 3/2/MVP entrypoints
- keep machine-independent commands and links in canonical docs

## Control Tower Task Cards

### Task 1: Phase 4 Gate Script Ownership

Owner: tooling operative

Write scope:

- `scripts/run_phase4_acceptance.py`
- `scripts/run_phase4_readiness_gates.py`
- `scripts/run_phase4_validation_matrix.py`

### Task 2: Gate Contract Tests

Owner: tooling operative

Write scope:

- `tests/unit/test_phase4_gate_wrappers.py`
- `tests/integration/test_phase4_acceptance_suite.py`
- `tests/integration/test_phase4_readiness_gates.py`
- `tests/integration/test_phase4_validation_matrix.py`

### Task 3: Runbooks + Control Truth

Owner: tooling operative

Write scope:

- `docs/runbooks/phase4-acceptance-suite.md`
- `docs/runbooks/phase4-readiness-gates.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/mvp-ship-gate-magnesium-reorder.md`
- `scripts/check_control_doc_truth.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 4: Integration Review

Owner: control tower

Write scope:

- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify sprint is non-redundant vs Sprint 12/13 runtime work
- verify Phase 4 canonical gate ownership is real (not wrapper-only)
- verify magnesium ship-gate scenario is first-class in Phase 4 acceptance chain
- verify compatibility chains (phase3/phase2/mvp) remain green
- verify docs and active packet stay in sync

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact gate-ownership delta (what moved from wrappers to canonical behavior)
- exact magnesium scenario integration delta
- exact test/command outcomes
- explicit deferred scope (runtime schema, connector/auth/platform expansion)

## Review Focus

`REVIEW_REPORT.md` should verify:

- no runtime reimplementation overlap with Sprint 12/13
- Phase 4 scripts are deterministic and measurable with clear failure step signaling
- magnesium ship-gate evidence is canonical in acceptance/matrix contracts
- compatibility commands remain PASS
- control docs and control-doc truth checker are aligned

## Exit Condition

This sprint is complete when Phase 4 is the unambiguous canonical MVP release gate, magnesium ship-gate evidence is first-class and deterministic, compatibility chains remain green, and planning/control docs no longer encode stale wrapper ownership.
