# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 12: Control-Doc Truth Guardrails And Baseline Sync

## Sprint Type

hardening

## Sprint Reason

Sprint 11 removed gate-runner ownership drift, but canonical docs still carry stale baseline claims (for example "through Phase 2 Sprint 7") and legacy ship-gate language that causes repeated planning confusion and redundant truth-sync churn. We need one narrow sprint that both updates canonical docs and adds a deterministic guardrail so this drift cannot silently recur.

## Sprint Intent

Sync canonical control docs to the actual merged baseline (through Phase 2 Sprint 11) and add an automated control-doc truth check wired into the Phase 2 validation chain to prevent stale/planning-drift regressions.

## Git Instructions

- Branch Name: `codex/phase2-sprint12-control-doc-truth-guardrails`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Current implementation is advancing, but planning artifacts are behind merged reality.
- Repeated doc drift creates redundant "truth-sync-only" sprint loops and merge-review friction.
- A lightweight automated check is the smallest durable fix that prevents recurrence.

## Design Truth

- No product/runtime/API feature changes.
- No gate threshold or scenario behavior changes.
- Guardrails should validate documented truth signals, not attempt semantic NLP inference.

## Exact Surfaces In Scope

- canonical control-doc baseline sync
- deterministic control-doc truth guardrail script + tests
- validation-matrix integration of truth guardrail step
- sprint-scoped report updates

## Exact Files In Scope

- [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md)
- [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md)
- [README.md](/Users/samirusani/Desktop/Codex/AliceBot/README.md)
- [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md)
- [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md)
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md)
- [run_phase2_validation_matrix.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_phase2_validation_matrix.py)
- [check_control_doc_truth.py](/Users/samirusani/Desktop/Codex/AliceBot/scripts/check_control_doc_truth.py)
- [test_control_doc_truth.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_control_doc_truth.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)
- relevant verification under:
  - `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py`
  - `python3 scripts/check_control_doc_truth.py`
  - `python3 scripts/run_phase2_validation_matrix.py --induce-step control_doc_truth`

## In Scope

- Update canonical docs to reflect merged baseline through Sprint 11 and canonical Phase 2 gate ownership.
- Remove/replace stale statements that anchor planning to Sprint 7-era baseline.
- Add a deterministic script that validates required truth markers and rejects disallowed stale markers in canonical docs.
- Add unit tests covering pass/fail cases for the truth-check script.
- Add `control_doc_truth` as a deterministic first step in `run_phase2_validation_matrix.py`.
- Keep induced-failure behavior in validation matrix deterministic and reviewer-visible.

## Out of Scope

- any endpoint, schema, or runtime behavior change
- connector capability expansion or orchestrator implementation
- memory extraction/retrieval algorithm changes
- UI feature changes
- workers/automation/orchestration implementation
- Phase 3 runtime/profile routing implementation

## Required Deliverables

- Canonical docs aligned to Sprint 11 merged reality.
- `scripts/check_control_doc_truth.py` implemented and deterministic.
- `tests/unit/test_control_doc_truth.py` passing.
- `scripts/run_phase2_validation_matrix.py` includes `control_doc_truth` step.
- Updated sprint reports for this sprint only.

## Acceptance Criteria

- Canonical docs no longer claim Sprint 7 as current baseline.
- Canonical docs reflect Phase 2 gate ownership as implemented after Sprint 11.
- `python3 scripts/check_control_doc_truth.py` returns exit code `0` on synced docs and non-zero on intentional stale-marker injection.
- `run_phase2_validation_matrix.py` executes `control_doc_truth` as a named step and reports deterministic pass/fail/no-go.
- `tests/unit/test_control_doc_truth.py` passes.
- No product/runtime endpoint behavior changes are introduced.

## Implementation Constraints

- keep script behavior deterministic and non-interactive
- keep checks machine-independent and path-stable
- use machine-independent assertions in tests
- do not introduce external dependencies
- co-deliver verification commands with outcomes in reports

## Control Tower Task Cards

### Task 1: Canonical Doc Sync
Owner: tooling operative  
Write scope:
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `README.md`
- `PRODUCT_BRIEF.md`
- `RULES.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 2: Truth Guardrail
Owner: tooling operative  
Write scope:
- `scripts/check_control_doc_truth.py`
- `tests/unit/test_control_doc_truth.py`
- `scripts/run_phase2_validation_matrix.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify doc truth aligns with merged baseline
- verify guardrail determinism and validation-matrix integration
- verify strict no-product-scope expansion
- verify reports and packet consistency

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact canonical-doc deltas
- truth-guardrail rules enforced (required and rejected markers)
- validation-matrix step integration details
- exact verification commands run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained doc-truth-and-guardrail scoped
- no hidden runtime/product-scope drift
- guardrail catches stale baseline markers deterministically
- verification evidence is sufficient for hardening sprint
- no hidden scope expansion

## Exit Condition

This sprint is complete when canonical control docs reflect the merged Sprint 11 baseline, deterministic truth guardrails are enforced in CI/local validation flow, and future stale-baseline drift is mechanically blocked.
