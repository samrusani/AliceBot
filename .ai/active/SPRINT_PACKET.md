# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 15: Phase-Closeout Packet And Exit Guardrail

## Sprint Type

hardening

## Sprint Reason

Phase 2 gate execution is currently green through Sprint 14, but canonical docs still describe the repo as current through Sprint 11 and there is no explicit, enforced Phase 2 exit packet/checklist. We need one closeout sprint that finalizes phase truth and makes exit-state drift mechanically detectable.

## Sprint Intent

Create an explicit Phase 2 closeout packet, sync canonical truth docs to Sprint 14, and update truth guardrails so the closeout state is enforced deterministically.

## Git Instructions

- Branch Name: `codex/phase2-sprint15-closeout-packet`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- We are on track technically (`python3 scripts/run_phase2_validation_matrix.py` is PASS), but closeout governance artifacts lag.
- Repeated “what phase are we in” friction comes from missing enforced exit packet, not missing core functionality.
- This is a non-redundant closeout sprint: it converts current state into an explicit, enforceable phase-complete baseline.

## Design Truth

- No endpoint/schema/runtime feature changes.
- Keep existing gate thresholds and matrix behavior unchanged.
- Closeout should be encoded as deterministic file+marker truth, not ad hoc interpretation.

## Exact Surfaces In Scope

- canonical truth doc sync to Sprint 14 baseline
- explicit Phase 2 exit packet documentation
- deterministic control-doc truth guardrail update for closeout state

## Exact Files In Scope

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [README.md](README.md)
- [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md)
- [check_control_doc_truth.py](scripts/check_control_doc_truth.py)
- [test_control_doc_truth.py](tests/unit/test_control_doc_truth.py)
- [phase2-closeout-packet.md](docs/runbooks/phase2-closeout-packet.md)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
  - `python3 scripts/check_control_doc_truth.py`
  - `python3 scripts/run_phase2_validation_matrix.py`

## In Scope

- Update canonical docs to reflect accepted state through Phase 2 Sprint 14.
- Add a dedicated closeout runbook packet documenting:
  - required Phase 2 go/no-go commands
  - required PASS evidence bundle
  - explicit deferred scope entering next phase
- Update control-doc truth rules to require closeout packet presence and Sprint 14 baseline markers.
- Update unit tests for truth guardrails to cover new required markers and stale-marker rejection behavior.

## Out of Scope

- API/runtime feature work
- connector capability expansion
- orchestration/worker implementation
- UI redesign
- Phase 3 routing implementation

## Required Deliverables

- canonical docs synced to Sprint 14 baseline
- `docs/runbooks/phase2-closeout-packet.md` committed as closeout source-of-truth
- truth guardrail rules and tests updated and passing
- sprint reports updated for this sprint only

## Acceptance Criteria

- Canonical docs no longer claim Sprint 11 as current baseline.
- `python3 scripts/check_control_doc_truth.py` passes with updated closeout markers.
- `tests/unit/test_control_doc_truth.py` passes with updated rule assertions.
- `docs/runbooks/phase2-closeout-packet.md` clearly defines the Phase 2 exit evidence bundle and deferred scope boundary.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No product/runtime endpoint behavior changes are introduced.

## Implementation Constraints

- keep checks deterministic and machine-independent
- avoid adding dependencies
- preserve existing gate command semantics
- do not broaden scope beyond closeout docs/guardrails

## Control Tower Task Cards

### Task 1: Canonical Truth Sync
Owner: tooling operative  
Write scope:
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `README.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 2: Closeout Guardrail
Owner: tooling operative  
Write scope:
- `docs/runbooks/phase2-closeout-packet.md`
- `scripts/check_control_doc_truth.py`
- `tests/unit/test_control_doc_truth.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify closeout packet completeness
- verify canonical truth sync to Sprint 14
- verify guardrail coverage for closeout markers
- verify strict no hidden scope expansion

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact canonical-doc baseline marker changes
- exact closeout packet contents added
- exact truth-guardrail rule/test changes
- exact verification command outcomes
- explicit deferred scope into next phase

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained closeout-doc-and-guardrail scoped
- closeout packet is operationally sufficient for phase handoff
- truth guardrails enforce updated baseline and packet presence
- no hidden runtime/product scope changes

## Exit Condition

This sprint is complete when Phase 2 closeout documentation is explicit and enforceable, canonical docs align to Sprint 14, and truth guardrails pass with the updated closeout baseline.
