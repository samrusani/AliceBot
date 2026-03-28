# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 15: MVP Release-Candidate Rehearsal and Evidence Bundle

## Sprint Type

feature

## Sprint Reason

Sprint 14 made Phase 4 gate ownership canonical. The next non-redundant gap is final MVP release confidence: one deterministic rehearsal command that produces a complete, auditable evidence bundle for go/no-go.

## Sprint Intent

Automate MVP release-candidate rehearsal by running the canonical Phase 4 chain plus compatibility checks and emitting a structured evidence bundle that Control Tower and CTO can review directly.

## Git Instructions

- Branch Name: `codex/phase4-sprint-15-mvp-rc-rehearsal-evidence-bundle`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It closes the last planning-to-release gap between “gates exist” and “release evidence is deterministic and packaged.”
- It reduces review churn by standardizing one RC rehearsal command and one evidence shape.
- It avoids redundant runtime work and keeps scope on MVP closeout operations.

## Redundancy Guard

- Already shipped in Sprint 12/13:
  - runtime execution linkage, idempotency, observability, retry/failure discipline
- Already shipped in Sprint 14:
  - canonical Phase 4 acceptance/readiness/validation ownership and magnesium scenario integration
- Required now (Sprint 15):
  - deterministic RC rehearsal orchestration and evidence packaging
  - stable machine-readable result summary for go/no-go
  - closeout runbook alignment to generated evidence artifact
- Explicitly out of Sprint 15:
  - runtime schema or execution semantics changes
  - connector/auth/platform expansion
  - orchestration model redesign

## Design Truth

- Phase 4 remains canonical MVP release gate.
- Canonical scenario remains magnesium reorder (`request -> approval -> execution -> memory write-back`).
- Compatibility guarantees remain mandatory:
  - `python3 scripts/run_phase3_validation_matrix.py`
  - `python3 scripts/run_phase2_validation_matrix.py`
  - `python3 scripts/run_mvp_validation_matrix.py`
- Release decision must be backed by one deterministic evidence bundle artifact, not ad-hoc command transcripts.

## Exact Surfaces In Scope

- RC rehearsal script and evidence output contract
- Phase 4 closeout runbook updates for artifact-driven review
- deterministic tests for rehearsal command behavior (success + induced failure paths)
- control-doc sync to reflect Sprint 15 ownership

## Exact Files In Scope

- `scripts/run_phase4_release_candidate.py`
- `scripts/run_phase4_validation_matrix.py`
- `scripts/run_phase4_acceptance.py`
- `scripts/run_phase4_readiness_gates.py`
- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_validation_matrix.py`
- `tests/unit/test_phase4_gate_wrappers.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add `scripts/run_phase4_release_candidate.py` to run ordered MVP rehearsal steps:
  - control-doc truth
  - phase4 acceptance
  - phase4 readiness
  - phase4 validation matrix
  - phase3 compatibility validation
  - phase2 compatibility validation
  - mvp compatibility validation
- Emit deterministic artifact output (for example `artifacts/release/phase4_rc_summary.json`) with:
  - per-step status
  - command
  - exit code
  - duration
  - final GO/NO_GO
- Ensure failure in any step fails the rehearsal command and preserves partial evidence.
- Update runbooks so review and merge decisions reference the generated artifact contract.
- Keep existing phase4 scripts backward-compatible while wiring into the new rehearsal flow.

## Out of Scope

- `apps/api/src/alicebot_api/*` runtime behavior/schema changes
- `workers/alicebot_worker/*` runtime behavior changes
- UI feature expansion
- connector breadth expansion
- auth expansion

## Required Deliverables

- deterministic Phase 4 RC rehearsal script
- stable JSON evidence artifact contract for go/no-go
- integration tests covering PASS and induced-failure NO_GO paths
- updated closeout runbook instructions tied to artifact review
- sprint-scoped build/review reports

## Acceptance Criteria

- `python3 scripts/run_phase4_release_candidate.py` passes and emits RC summary artifact with deterministic schema.
- `python3 scripts/run_phase4_release_candidate.py --induce-step phase4_validation_matrix` fails with explicit NO_GO and writes failure evidence.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- `python3 scripts/run_mvp_validation_matrix.py` remains PASS.
- `./.venv/bin/python -m pytest tests/integration/test_phase4_release_candidate.py tests/integration/test_phase4_validation_matrix.py tests/unit/test_phase4_gate_wrappers.py -q` passes.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` are synchronized to Sprint 15 focus.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing Phase 4/3/2/MVP command contracts
- keep deterministic ordered execution and explicit pass/fail reporting
- keep machine-independent commands and paths in docs

## Control Tower Task Cards

### Task 1: RC Rehearsal Script

Owner: tooling operative

Write scope:

- `scripts/run_phase4_release_candidate.py`
- `scripts/run_phase4_validation_matrix.py`

### Task 2: RC Contract Tests

Owner: tooling operative

Write scope:

- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_validation_matrix.py`
- `tests/unit/test_phase4_gate_wrappers.py`

### Task 3: Runbook + Control Sync

Owner: tooling operative

Write scope:

- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 4: Integration Review

Owner: control tower

Write scope:

- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no reimplementation overlap with Sprint 12/13/14 runtime and gate-ownership work
- verify RC artifact contract is deterministic and actionable
- verify compatibility chains remain PASS
- verify docs and active packet stay synchronized

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact RC rehearsal orchestration delta
- exact evidence artifact schema and output path
- exact verification command outcomes
- explicit deferred scope

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed release-control scoped
- RC command deterministically reports GO/NO_GO with per-step evidence
- failure injection behavior is explicit and stable
- compatibility chains remain green
- no hidden runtime scope expansion

## Exit Condition

This sprint is complete when one deterministic Phase 4 RC rehearsal command produces a complete evidence bundle with explicit GO/NO_GO and all compatibility gates remain green.
