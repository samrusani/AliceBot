# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 10: Closeout Truth Sync + Phase Gate Canonicalization

## Sprint Type

control-plane

## Sprint Reason

Sprint 9 closed the last known runtime invariance gap for profile-isolated execution budgets. The next non-redundant blocker to MVP/Phase 3 completion is control-plane drift: canonical docs and control-doc checks still anchor to a Phase 2 Sprint 14 baseline.

## Sprint Intent

Re-anchor canonical truth, validation entrypoints, and closeout runbooks to the accepted Phase 3 Sprint 9 baseline without changing product runtime behavior.

## Git Instructions

- Branch Name: `codex/phase3-sprint10-closeout-truth-sync`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It closes the remaining planning/validation drift risk before phase completion.
- It enables deterministic “are we done?” checks using phase-correct runbooks and truth guards.
- It avoids redundant runtime work by focusing only on docs/gates canonicalization.

## Redundancy Guard

- Already shipped in Sprint 1: thread-level profile identity + metadata propagation.
- Already shipped in Sprint 2: web profile selection/visibility.
- Already shipped in Sprint 3: profile-aware response prompting.
- Already shipped in Sprint 4: durable profile registry + thread FK.
- Already shipped in Sprint 5: profile-scoped memory/context isolation.
- Already shipped in Sprint 6: profile-scoped policy evaluation/routing.
- Already shipped in Sprint 7: profile-scoped model/provider routing for `/v0/responses`.
- Already shipped in Sprint 8: profile-scoped execution-budget matching + counted execution isolation.
- Already shipped in Sprint 9: fail-closed context invariance hardening for budget decisioning.
- Missing and required now: Phase 3 canonical truth + gate/runbook alignment for deterministic closeout.

## Design Truth

- Canonical docs must state the accepted repo baseline through Phase 3 Sprint 9, not Phase 2 Sprint 14.
- Control-doc truth checks must enforce Phase 3 markers and reject stale Phase 2 baseline claims where now obsolete.
- Phase gate entrypoints should include Phase 3 names, preserving compatibility aliases to existing gate semantics.
- This sprint is documentation and control-plane only; runtime API/web behavior must remain unchanged.

## Exact Surfaces In Scope

- canonical truth docs baseline alignment (architecture/roadmap/readme/handoff)
- control-doc truth guardrail update + unit tests
- Phase 3 gate entrypoint scripts (compatibility wrappers allowed)
- Phase 3 closeout runbook packet and evidence requirements

## Exact Files In Scope

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [README.md](README.md)
- [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md)
- [scripts/check_control_doc_truth.py](scripts/check_control_doc_truth.py)
- [tests/unit/test_control_doc_truth.py](tests/unit/test_control_doc_truth.py)
- [scripts/run_phase3_acceptance.py](scripts/run_phase3_acceptance.py)
- [scripts/run_phase3_readiness_gates.py](scripts/run_phase3_readiness_gates.py)
- [scripts/run_phase3_validation_matrix.py](scripts/run_phase3_validation_matrix.py)
- [docs/runbooks/phase3-closeout-packet.md](docs/runbooks/phase3-closeout-packet.md)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Update canonical docs to reflect accepted baseline through Phase 3 Sprint 9.
- Update control-doc truth markers/rules and keep stale-marker rejection accurate.
- Add Phase 3 gate entrypoint scripts as compatibility wrappers to current deterministic gate runners.
- Add Phase 3 closeout runbook with required commands, PASS evidence bundle, and deferred-scope statement.
- Keep root `BUILD_REPORT.md`/`REVIEW_REPORT.md` conventions explicit.
- Validate docs and gate tooling through targeted unit and gate commands.

## Out of Scope

- runtime API logic changes
- web UI behavior changes
- schema/migration changes
- provider/connector/auth capability expansion
- orchestration/worker runtime changes
- profile CRUD expansion

## Required Deliverables

- canonical docs aligned to Phase 3 Sprint 9 baseline
- control-doc truth guard and unit tests updated and passing
- Phase 3 gate entrypoint scripts present and executable
- Phase 3 closeout runbook present with deterministic go/no-go checklist
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- `python3 scripts/check_control_doc_truth.py` passes with Phase 3 markers.
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q` passes.
- `python3 scripts/run_phase3_validation_matrix.py` passes.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS (compatibility guarantee).
- Canonical docs do not claim a baseline earlier than accepted Phase 3 Sprint 9.
- No runtime API/web/schema capability expansion enters this sprint.
- No provider/connector/orchestration scope expansion enters this sprint.

## Implementation Constraints

- do not introduce new dependencies
- keep script behavior deterministic and machine-independent
- use repo-relative paths and machine-independent command examples in docs
- preserve existing runtime product behavior (docs/control-plane only)

## Control Tower Task Cards

### Task 1: Canonical Truth Sync
Owner: tooling operative  
Write scope:
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `README.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 2: Control Guard + Gate Entry Points
Owner: tooling operative  
Write scope:
- `scripts/check_control_doc_truth.py`
- `tests/unit/test_control_doc_truth.py`
- `scripts/run_phase3_acceptance.py`
- `scripts/run_phase3_readiness_gates.py`
- `scripts/run_phase3_validation_matrix.py`
- `docs/runbooks/phase3-closeout-packet.md`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays docs/control-plane scoped
- verify phase baseline markers and closeout runbook are internally consistent
- verify no runtime/schema expansion
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact canonical-doc and control-guard deltas
- exact verification command outcomes
- explicit deferred scope (runtime/schema/providers/connectors/orchestration/profile CRUD)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to closeout truth-sync scope
- canonical docs and truth checks align on Phase 3 baseline markers
- phase3 gate wrappers and closeout runbook are deterministic and coherent
- runtime behavior remained unchanged
- no hidden scope expansion

## Exit Condition

This sprint is complete when canonical docs, control-doc truth checks, and gate entrypoints consistently represent the accepted Phase 3 Sprint 9 baseline, with all required verification commands passing and no runtime-scope expansion.
