# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 19: MVP Qualification and Sign-off Record

## Sprint Type

hardening

## Sprint Reason

Phase 4 closeout tooling is complete through Sprint 18, but MVP still needs one deterministic qualification run and a formal sign-off record that captures GO/NO_GO plus any residual blockers.

## Sprint Intent

Run the full MVP qualification chain end-to-end, generate a deterministic sign-off record artifact, and resolve only blocking defects discovered in that bounded qualification scope.

## Git Instructions

- Branch Name: `codex/phase4-sprint-19-mvp-qualification-signoff`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It converts “tools exist” into “MVP qualification executed and recorded.”
- It prevents redundant tooling loops by moving to an execution/sign-off sprint.
- It establishes a clear handoff checkpoint before Phase 5 planning.

## Redundancy Guard

- Already shipped through Sprint 18:
  - canonical Phase 4 gates
  - RC rehearsal + archive/index + concurrency hardening
  - MVP exit manifest generation/verification
- Required now (Sprint 19):
  - deterministic qualification orchestrator command
  - deterministic sign-off record artifact with GO/NO_GO + blocker registry
  - only blocker fixes needed to make qualification pass
- Explicitly out of Sprint 19:
  - net-new product scope expansion
  - connector/auth/platform expansion
  - broad refactors unrelated to qualification blockers

## Design Truth

- Qualification must be derived from existing Phase 4 release controls, not alternate paths.
- Canonical compatibility checks remain:
  - `run_phase4_validation_matrix.py`
  - `run_phase3_validation_matrix.py`
  - `run_phase2_validation_matrix.py`
  - `run_mvp_validation_matrix.py`
- Sign-off record must capture:
  - executed commands
  - pass/fail status per gate
  - final GO/NO_GO
  - blocker list (empty for GO)

## Exact Surfaces In Scope

- MVP qualification orchestration script
- sign-off record generation and verification
- closeout docs/control docs alignment
- blocker-only fixes discovered during qualification execution

## Exact Files In Scope

- `scripts/run_phase4_mvp_qualification.py`
- `scripts/verify_phase4_mvp_signoff_record.py`
- `scripts/run_phase4_release_candidate.py`
- `scripts/generate_phase4_mvp_exit_manifest.py`
- `scripts/verify_phase4_mvp_exit_manifest.py`
- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/phase4-mvp-qualification.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `tests/integration/test_phase4_mvp_qualification.py`
- `tests/integration/test_phase4_mvp_exit_manifest.py`
- `tests/unit/test_phase4_gate_wrappers.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add qualification command:
  - `python3 scripts/run_phase4_mvp_qualification.py`
  - runs ordered sequence:
    - RC rehearsal (`run_phase4_release_candidate.py`)
    - RC archive verify (`verify_phase4_rc_archive.py`)
    - MVP exit manifest generation (`generate_phase4_mvp_exit_manifest.py`)
    - MVP exit manifest verify (`verify_phase4_mvp_exit_manifest.py`)
  - emits sign-off record artifact (for example `artifacts/release/phase4_mvp_signoff_record.json`)
- Add sign-off verifier command:
  - `python3 scripts/verify_phase4_mvp_signoff_record.py`
  - validates schema, required references, and GO/NO_GO consistency.
- Fix only blocking defects found by qualification chain.
- Update closeout docs with final qualification/sign-off workflow and criteria.

## Out of Scope

- non-blocking UX enhancement work
- broad runtime refactors
- new connector/platform capabilities
- architecture redesign

## Required Deliverables

- deterministic qualification orchestration command
- deterministic sign-off record + verifier
- blocker-only fixes (if required)
- updated closeout and qualification runbooks
- sprint build/review reports

## Acceptance Criteria

- `python3 scripts/run_phase4_mvp_qualification.py` runs and writes sign-off record artifact.
- `python3 scripts/verify_phase4_mvp_signoff_record.py` passes.
- `python3 scripts/run_phase4_release_candidate.py` passes.
- `python3 scripts/verify_phase4_rc_archive.py` passes.
- `python3 scripts/generate_phase4_mvp_exit_manifest.py` passes.
- `python3 scripts/verify_phase4_mvp_exit_manifest.py` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- `python3 scripts/run_mvp_validation_matrix.py` remains PASS.
- `./.venv/bin/python -m pytest tests/integration/test_phase4_mvp_qualification.py tests/integration/test_phase4_mvp_exit_manifest.py tests/unit/test_phase4_gate_wrappers.py -q` passes.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect Sprint 19 qualification/sign-off ownership.

## Implementation Constraints

- do not introduce new dependencies
- keep qualification deterministic and machine-readable
- preserve existing gate semantics and artifact schema compatibility
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Qualification Orchestrator

Owner: tooling operative

Write scope:

- `scripts/run_phase4_mvp_qualification.py`
- `scripts/verify_phase4_mvp_signoff_record.py`

### Task 2: Qualification Contract Tests

Owner: tooling operative

Write scope:

- `tests/integration/test_phase4_mvp_qualification.py`
- `tests/integration/test_phase4_mvp_exit_manifest.py`
- `tests/unit/test_phase4_gate_wrappers.py`

### Task 3: Blocker Fixes (If Any)

Owner: tooling operative

Write scope:

- only files required to resolve qualification blockers, with explicit justification in `BUILD_REPORT.md`

### Task 4: Docs + Control Sync

Owner: tooling operative

Write scope:

- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/phase4-mvp-qualification.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 5: Integration Review

Owner: control tower

Write scope:

- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify sprint remained qualification/sign-off scoped
- verify blocker fixes were truly blocker-only and minimal
- verify GO/NO_GO record is deterministic and coherent
- verify no hidden scope expansion

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact qualification chain and artifact outputs
- any blocker fixes and why they were required
- command outcomes for each gate
- explicit deferred scope

## Review Focus

`REVIEW_REPORT.md` should verify:

- qualification chain is deterministic and complete
- sign-off record schema and references are valid
- blocker list is empty for GO or explicit for NO_GO
- compatibility chains remain green
- no hidden runtime/product scope expansion

## Exit Condition

This sprint is complete when MVP qualification is executed end-to-end with a deterministic sign-off record artifact and either:
- GO with no unresolved blockers, or
- NO_GO with explicit blocker registry and remediation ownership.
