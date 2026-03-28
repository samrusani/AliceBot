# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 18: MVP Exit Manifest and Phase Closeout

## Sprint Type

hardening

## Sprint Reason

Phase 4 engineering work is functionally complete through Sprint 17. The remaining non-redundant gap is formal MVP phase closeout evidence: an immutable release manifest tied to a verified GO rehearsal run.

## Sprint Intent

Produce deterministic, reviewable MVP exit artifacts (manifest + verification command) so Phase 4 can be formally closed without relying on ad-hoc report interpretation.

## Git Instructions

- Branch Name: `codex/phase4-sprint-18-mvp-exit-manifest`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It turns “we passed gates” into an auditable release package.
- It gives CTO/control-tower one canonical artifact for sign-off.
- It avoids redoing Sprint 14-17 runtime/gate/archive work.

## Redundancy Guard

- Already shipped through Sprint 17:
  - canonical Phase 4 gate ownership
  - RC rehearsal GO/NO_GO artifacts
  - archive ledger + concurrency-safe index updates
- Required now (Sprint 18):
  - immutable MVP exit manifest from a GO rehearsal
  - verification command for manifest integrity and required fields
  - phase closeout runbook updates
- Explicitly out of Sprint 18:
  - runtime changes under `apps/api` or `workers`
  - connector/auth/platform scope changes
  - new gate semantics

## Design Truth

- Phase 4 remains canonical MVP release gate.
- Manifest must be derived from existing RC artifact chain, not from manual edits.
- Compatibility checks remain required and unchanged:
  - `python3 scripts/run_phase4_validation_matrix.py`
  - `python3 scripts/run_phase3_validation_matrix.py`
  - `python3 scripts/run_phase2_validation_matrix.py`
  - `python3 scripts/run_mvp_validation_matrix.py`

## Exact Surfaces In Scope

- MVP exit manifest generation
- manifest verification command
- closeout runbook + control-doc synchronization
- test coverage for manifest contract

## Exact Files In Scope

- `scripts/run_phase4_release_candidate.py`
- `scripts/generate_phase4_mvp_exit_manifest.py`
- `scripts/verify_phase4_mvp_exit_manifest.py`
- `docs/runbooks/phase4-closeout-packet.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_mvp_exit_manifest.py`
- `tests/unit/test_phase4_gate_wrappers.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add manifest generator command:
  - `python3 scripts/generate_phase4_mvp_exit_manifest.py`
  - consumes latest GO RC summary and archive/index references
  - writes deterministic manifest (for example `artifacts/release/phase4_mvp_exit_manifest.json`)
- Add manifest verifier command:
  - `python3 scripts/verify_phase4_mvp_exit_manifest.py`
  - validates schema, required fields, and referenced artifacts
- Add tests for:
  - GO manifest generation path
  - invalid/missing-reference failure path
- Update closeout docs to require manifest creation + verification before phase sign-off.

## Out of Scope

- `apps/api/src/alicebot_api/*`
- `workers/alicebot_worker/*`
- UI/connector/auth feature work
- changing Phase 4/3/2/MVP gate behavior

## Required Deliverables

- deterministic MVP exit manifest artifact
- deterministic manifest verification command
- tests for manifest contract
- updated closeout runbook and control docs
- sprint-scoped build/review reports

## Acceptance Criteria

- `python3 scripts/run_phase4_release_candidate.py` passes and records GO evidence.
- `python3 scripts/generate_phase4_mvp_exit_manifest.py` passes and writes manifest artifact.
- `python3 scripts/verify_phase4_mvp_exit_manifest.py` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- `python3 scripts/run_mvp_validation_matrix.py` remains PASS.
- `./.venv/bin/python -m pytest tests/integration/test_phase4_release_candidate.py tests/integration/test_phase4_mvp_exit_manifest.py tests/unit/test_phase4_gate_wrappers.py -q` passes.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` are synchronized to Sprint 18 closeout focus.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing RC archive/index schema and compatibility behavior
- keep machine-independent paths/commands in docs
- keep manifest deterministic and machine-readable

## Control Tower Task Cards

### Task 1: Exit Manifest Tooling

Owner: tooling operative

Write scope:

- `scripts/generate_phase4_mvp_exit_manifest.py`
- `scripts/verify_phase4_mvp_exit_manifest.py`
- `scripts/run_phase4_release_candidate.py`

### Task 2: Manifest Contract Tests

Owner: tooling operative

Write scope:

- `tests/integration/test_phase4_mvp_exit_manifest.py`
- `tests/integration/test_phase4_release_candidate.py`
- `tests/unit/test_phase4_gate_wrappers.py`

### Task 3: Closeout Docs Sync

Owner: tooling operative

Write scope:

- `docs/runbooks/phase4-closeout-packet.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`

### Task 4: Integration Review

Owner: control tower

Write scope:

- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no runtime scope expansion
- verify manifest is deterministic and derived from RC evidence
- verify compatibility chains remain PASS
- verify phase closeout docs and packet are aligned

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact manifest schema/output location
- exact generation/verification command outcomes
- explicit deferred scope

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed closeout-scoped
- manifest generation/verification is deterministic and test-backed
- referenced RC artifacts and archive ledger are coherent
- compatibility chains remain green
- no hidden runtime scope expansion

## Exit Condition

This sprint is complete when a deterministic MVP exit manifest can be generated and verified from RC evidence, with compatibility gates still passing and Phase 4 closeout artifacts ready for formal sign-off.
