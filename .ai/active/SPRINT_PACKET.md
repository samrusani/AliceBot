# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 11: Canonicalize Phase 2 Gates (Remove Wrapper Drift)

## Sprint Type

hardening

## Sprint Reason

Sprint 10 closed acceptance evidence for capture-to-resumption continuity. The remaining control risk is runner drift: `run_phase2_*` scripts are still thin wrappers over `run_mvp_*`, so Phase 2 is named as canonical in docs while MVP scripts remain the implementation source. This causes planning churn and redundant sprint pressure.

## Sprint Intent

Make Phase 2 gate scripts the canonical implementation source and downgrade MVP runners to explicit compatibility aliases, while preserving the exact current gate behavior and thresholds.

## Git Instructions

- Branch Name: `codex/phase2-sprint11-gate-canonicalization`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- We are on track, but control artifacts still carry dual-source gate semantics (Phase 2 labels, MVP implementations).
- Canonicalizing one runner source removes duplicate maintenance and prevents repeated "wrapper parity" sprints.
- This is the narrowest high-value hardening seam before broader Phase 2 completion work.

## Design Truth

- Do not change product/API behavior or gate thresholds.
- Keep deterministic gate coverage and scenario list behavior stable.
- One canonical source for gate orchestration must exist after this sprint.

## Exact Surfaces In Scope

- gate runner canonicalization (Phase 2 scripts become source of truth)
- MVP compatibility aliasing (MVP scripts call Phase 2 scripts)
- runbook naming/ownership alignment
- sprint-scoped verification of deterministic parity

## Exact Files In Scope

- [run_phase2_acceptance.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_phase2_acceptance.py)
- [run_phase2_readiness_gates.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_phase2_readiness_gates.py)
- [run_phase2_validation_matrix.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_phase2_validation_matrix.py)
- [run_mvp_acceptance.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_acceptance.py)
- [run_mvp_readiness_gates.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_readiness_gates.py)
- [run_mvp_validation_matrix.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_validation_matrix.py)
- [test_phase2_gate_wrappers.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_phase2_gate_wrappers.py)
- [mvp-acceptance-suite.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-acceptance-suite.md)
- [mvp-readiness-gates.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-readiness-gates.md)
- [mvp-validation-matrix.md](/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-validation-matrix.md)
- [README.md](/Users/samirusani/Desktop/Codex/AliceBot/README.md)
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `./.venv/bin/python -m pytest tests/unit/test_phase2_gate_wrappers.py`
  - `python3 scripts/run_phase2_acceptance.py`
  - `python3 scripts/run_phase2_readiness_gates.py --induce-gate acceptance_fail`
  - `python3 scripts/run_phase2_validation_matrix.py --induce-step readiness_gates`

## In Scope

- Move canonical gate orchestration and messaging into:
  - `scripts/run_phase2_acceptance.py`
  - `scripts/run_phase2_readiness_gates.py`
  - `scripts/run_phase2_validation_matrix.py`
- Convert MVP scripts into compatibility aliases that delegate to Phase 2 scripts with explicit alias messaging.
- Preserve existing deterministic scenario coverage, gate thresholds, and no-go behavior (no semantic widening).
- Update unit tests to verify canonical direction (MVP -> Phase 2 aliasing) and deterministic command wiring.
- Update runbooks and entry docs so "Phase 2 canonical / MVP alias" is explicit and internally consistent.

## Out of Scope

- API endpoint changes or schema/migration work
- feature-scope changes in chat/memory/connectors/tasks
- threshold tuning or acceptance scenario rewrites beyond naming/wiring parity
- workers/automation/orchestration implementation
- Phase 3 runtime/profile routing implementation

## Required Deliverables

- Phase 2 scripts become canonical runner implementations (no longer wrappers to MVP scripts).
- MVP scripts remain available as compatibility aliases to Phase 2 scripts.
- Unit tests prove alias behavior and deterministic wiring.
- Runbooks/docs clearly declare canonical ownership and compatibility aliases.
- Updated sprint reports for this sprint only.

## Acceptance Criteria

- `run_phase2_acceptance.py`, `run_phase2_readiness_gates.py`, and `run_phase2_validation_matrix.py` do not invoke `run_mvp_*` scripts.
- `run_mvp_*` scripts invoke `run_phase2_*` scripts and preserve backward-compatible invocation UX.
- Existing deterministic gate semantics remain intact (same scenario coverage and pass/fail/no-go logic).
- `tests/unit/test_phase2_gate_wrappers.py` passes with updated canonical direction.
- Runbooks and top-level docs are consistent with "Phase 2 canonical, MVP alias."
- No product/runtime endpoint behavior changes are introduced.

## Implementation Constraints

- keep script behavior deterministic and non-interactive
- preserve existing thresholds and scenario-node coverage
- use machine-independent assertions in tests
- do not introduce external dependencies
- co-deliver verification commands with outcomes in reports

## Control Tower Task Cards

### Task 1: Canonical Gate Scripts
Owner: tooling operative  
Write scope:
- `scripts/run_phase2_acceptance.py`
- `scripts/run_phase2_readiness_gates.py`
- `scripts/run_phase2_validation_matrix.py`
- `scripts/run_mvp_acceptance.py`
- `scripts/run_mvp_readiness_gates.py`
- `scripts/run_mvp_validation_matrix.py`
- `tests/unit/test_phase2_gate_wrappers.py`

### Task 2: Runbook And Entry-Doc Alignment
Owner: tooling operative  
Write scope:
- `docs/runbooks/mvp-acceptance-suite.md`
- `docs/runbooks/mvp-readiness-gates.md`
- `docs/runbooks/mvp-validation-matrix.md`
- `README.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify canonical direction (Phase 2 source, MVP alias)
- verify deterministic parity and gate semantics continuity
- verify strict no-product-scope expansion
- verify docs and runner consistency

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact script ownership migration (Phase 2 canonical, MVP alias)
- exact parity-preservation notes (what remained unchanged semantically)
- test updates and outcomes for alias/wiring verification
- exact verification commands run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained gate-canonicalization scoped
- no hidden gate-semantics drift
- docs and script ownership consistency
- verification evidence is sufficient for hardening sprint
- no hidden scope expansion

## Exit Condition

This sprint is complete when Phase 2 gates are the single canonical implementation source, MVP commands are explicit compatibility aliases, deterministic gate behavior remains unchanged, and control docs no longer imply dual ownership.
