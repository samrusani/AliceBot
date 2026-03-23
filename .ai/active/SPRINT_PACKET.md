# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 8: Closeout Gate And Truth Sync

## Sprint Type

hardening

## Sprint Reason

Phase 2 Sprint 7 is merged and validation is green, but canonical docs and runbook entrypoints still describe older Sprint 7G-era state. Planning drift is now the primary delivery risk.

## Sprint Intent

Synchronize canonical project truth to the merged Phase 2 Sprint 7 state and add explicit Phase 2 gate entrypoints, without changing product runtime behavior.

## Git Instructions

- Branch Name: `codex/phase2-sprint8-closeout-gate-truth-sync`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Repo behavior and tests indicate Phase 2 maturity, but reader-facing truth artifacts are stale.
- Control decisions now depend more on docs/runbooks than on new feature seams.
- This is the narrowest, highest-leverage closeout seam before Phase 2 completion call.

## Design Truth

- Do not change shipped feature contracts in this sprint.
- Keep Phase 2 gate entrypoints deterministic and shell-compatible.
- Canonical docs must reflect merged repo truth through Sprint 7.

## Exact Surfaces In Scope

- canonical docs truth sync
- Phase 2 gate script entrypoints
- sprint-scoped script/docs verification

## Exact Files In Scope

- [README.md](README.md)
- [ROADMAP.md](ROADMAP.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md)
- [run_mvp_acceptance.py](scripts/run_mvp_acceptance.py)
- [run_mvp_readiness_gates.py](scripts/run_mvp_readiness_gates.py)
- [run_mvp_validation_matrix.py](scripts/run_mvp_validation_matrix.py)
- [run_phase2_acceptance.py](scripts/run_phase2_acceptance.py)
- [run_phase2_readiness_gates.py](scripts/run_phase2_readiness_gates.py)
- [run_phase2_validation_matrix.py](scripts/run_phase2_validation_matrix.py)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `python3 -m py_compile scripts/run_phase2_acceptance.py scripts/run_phase2_readiness_gates.py scripts/run_phase2_validation_matrix.py`

## In Scope

- Update canonical docs to reflect merged state through Phase 2 Sprint 7:
  - typed memory + open-loop seams
  - resumption brief seam
  - unified explicit-signal capture + `/chat` manual capture controls
  - current validation/gate commands
- Add Phase 2 gate entrypoint scripts:
  - `scripts/run_phase2_acceptance.py`
  - `scripts/run_phase2_readiness_gates.py`
  - `scripts/run_phase2_validation_matrix.py`
- Keep Phase 2 scripts deterministic and compatible:
  - either thin wrappers to MVP runners or aliased implementations with identical semantics
- Ensure README and handoff docs point to canonical gate commands and current control artifacts.
- Update roadmap “Current Position” baseline from Sprint 7G-era wording to current merged phase state.
- Record explicit deferred scope boundaries for what is still not shipped.

## Out of Scope

- any backend/API behavior change
- UI/UX feature changes
- new migrations/schema changes
- workers/automation/orchestration implementation
- Phase 3 runtime/profile routing implementation

## Required Deliverables

- canonical docs synchronized to merged Phase 2 state
- Phase 2 gate script entrypoints present and parseable
- clear command guidance for operators/builders in README + handoff docs
- updated sprint reports for this sprint only

## Acceptance Criteria

- canonical docs no longer claim Sprint 7G as current state
- README/ROADMAP/ARCHITECTURE/CURRENT_STATE are mutually consistent about shipped seams
- `scripts/run_phase2_acceptance.py`, `scripts/run_phase2_readiness_gates.py`, `scripts/run_phase2_validation_matrix.py` exist and compile
- phase2 validation entrypoint command is documented and executable
- no product/runtime behavior changes are introduced
- no out-of-scope implementation work enters sprint

## Implementation Constraints

- keep script behavior deterministic and non-interactive
- use machine-independent paths/commands in docs
- avoid deleting historical artifacts needed for traceability
- co-deliver verification commands with outcomes in reports

## Control Tower Task Cards

### Task 1: Canonical Docs Sync
Owner: documentation operative  
Write scope:
- `README.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 2: Phase 2 Gate Entrypoints
Owner: tooling operative  
Write scope:
- `scripts/run_phase2_acceptance.py`
- `scripts/run_phase2_readiness_gates.py`
- `scripts/run_phase2_validation_matrix.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify docs/runbook truth coherence
- verify phase2 entrypoint script integrity
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact docs/files updated and previous stale claims removed
- exact phase2 entrypoint scripts added/updated
- exact verification commands run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained closeout-truth-sync scoped
- docs/script consistency across canonical surfaces
- verification evidence is sufficient for script/docs-only sprint
- no hidden scope expansion

## Exit Condition

This sprint is complete when canonical docs and gate entrypoints accurately represent merged Phase 2 state, verification evidence is recorded, and no product/runtime behavior changed.
