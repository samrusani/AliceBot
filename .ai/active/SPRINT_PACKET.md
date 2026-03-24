# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 14: Memory-Quality Gate Realism Hardening

## Sprint Type

hardening

## Sprint Reason

Current readiness `memory_quality` evidence is still generated from synthetic seeded memory labels in `scripts/run_phase2_readiness_gates.py`. That can pass while explicit-signal capture quality regresses. This is now the highest remaining MVP-testing risk and is distinct from prior gate/doc canonicalization sprints.

## Sprint Intent

Make readiness `memory_quality` evidence derive from deterministic explicit-signal capture outcomes and deterministic adjudication logic, while preserving existing gate thresholds and deterministic no-go behavior.

## Git Instructions

- Branch Name: `codex/phase2-sprint14-memory-quality-realism`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- `python3 scripts/run_phase2_validation_matrix.py` is green, but memory-quality gating still uses synthetic seeded labels.
- A green memory gate should mean capture/extraction behavior is healthy, not only seeded bookkeeping is healthy.
- This closes a true testing-evidence gap without expanding product feature scope.

## Design Truth

- Keep thresholds unchanged:
  - precision `> 0.80`
  - adjudicated sample `>= 20`
- Keep deterministic gate behavior and induced-gate controls.
- Do not change API contracts or user-facing product behavior.

## Exact Surfaces In Scope

- readiness gate memory-quality evidence generation path
- readiness gate test coverage for memory-quality evidence source and posture transitions
- sprint-scoped reports

## Exact Files In Scope

- [run_phase2_readiness_gates.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_phase2_readiness_gates.py)
- [test_mvp_readiness_gates.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_mvp_readiness_gates.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `./.venv/bin/python -m pytest tests/integration/test_mvp_readiness_gates.py -q`
  - `python3 scripts/run_phase2_readiness_gates.py --induce-gate memory_needs_review`
  - `python3 scripts/run_phase2_readiness_gates.py --induce-gate memory_insufficient`
  - `python3 scripts/run_phase2_validation_matrix.py`

## In Scope

- Replace synthetic memory-label seeding as the default `memory_quality` evidence source with deterministic capture-derived evaluation inputs.
- Implement deterministic adjudication mapping from capture-derived outputs to memory review labels used by evaluation-summary.
- Preserve current gate posture semantics:
  - `PASS` when thresholds are exceeded
  - `FAIL` when sample is sufficient but precision is at/below threshold
  - `BLOCKED` when sample is insufficient or evidence unavailable
- Keep `--induce-gate memory_needs_review` and `--induce-gate memory_insufficient` deterministic and explicit.

## Out of Scope

- endpoint/schema changes
- acceptance scenario expansion beyond readiness-memory evidence source
- connector/orchestration/worker scope
- UI feature changes
- Phase 3 runtime/profile routing

## Required Deliverables

- readiness `memory_quality` path no longer depends on synthetic bulk memory seeding as primary evidence
- deterministic tests proving capture-derived memory-quality evidence behavior
- unchanged thresholds and deterministic induced-gate behavior
- updated sprint reports for this sprint only

## Acceptance Criteria

- `tests/integration/test_mvp_readiness_gates.py` passes with updated canonical memory-quality evidence logic.
- Default readiness run computes `memory_quality` from capture-derived deterministic evidence path.
- `--induce-gate memory_needs_review` and `--induce-gate memory_insufficient` still force expected deterministic outcomes.
- Full `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No API contract or runtime endpoint behavior changes are introduced.

## Implementation Constraints

- keep scripts deterministic and non-interactive
- preserve existing threshold constants and gate naming
- avoid external dependencies
- keep assertions machine-independent

## Control Tower Task Cards

### Task 1: Memory-Quality Evidence Source
Owner: tooling operative  
Write scope:
- `scripts/run_phase2_readiness_gates.py`

### Task 2: Gate Test Alignment
Owner: tooling operative  
Write scope:
- `tests/integration/test_mvp_readiness_gates.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify evidence source changed from synthetic seed to capture-derived logic
- verify threshold and posture semantics unchanged
- verify no hidden scope expansion
- verify reports and packet consistency

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact previous synthetic evidence path and exact replacement path
- deterministic adjudication rules used
- verification command outputs and outcomes
- explicit deferred scope

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed memory-quality-readiness scoped
- capture-derived evidence is deterministic and credible
- threshold/posture behavior is preserved
- no hidden runtime/product scope changes

## Exit Condition

This sprint is complete when readiness `memory_quality` gate evidence is capture-derived and deterministic, thresholds/postures remain unchanged, and full Phase 2 validation remains green.
