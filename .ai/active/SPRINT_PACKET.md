# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 16: RC Evidence Archive and Audit Ledger

## Sprint Type

feature

## Sprint Reason

Sprint 15 delivered deterministic release-candidate rehearsal with GO/NO_GO artifacts, but evidence is currently written to one deterministic path and overwritten on each run. The next non-redundant MVP gap is audit-grade evidence retention for repeated rehearsal/testing cycles.

## Sprint Intent

Make RC evidence durable across runs by adding deterministic archival/ledger support while preserving Sprint 15 gate semantics and compatibility guarantees.

## Git Instructions

- Branch Name: `codex/phase4-sprint-16-rc-evidence-archive-ledger`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It closes the evidence-loss risk called out in Sprint 15 review (`phase4_rc_summary.json` overwrite behavior).
- It enables thorough MVP testing with retained GO/NO_GO history instead of one latest snapshot.
- It improves release auditability without reopening runtime or gate-ownership scope.

## Redundancy Guard

- Already shipped through Sprint 15:
  - canonical Phase 4 gates and magnesium ship-gate integration
  - deterministic RC rehearsal and structured summary artifact
- Required now (Sprint 16):
  - persistent archival of RC artifacts across runs
  - deterministic audit ledger/index for historical rehearsal evidence
  - runbook and control-doc alignment to archive workflow
- Explicitly not in Sprint 16:
  - runtime behavior/schema changes under `apps/api` or `workers`
  - connector/auth/platform expansion
  - gate-chain semantic redesign

## Design Truth

- Phase 4 remains canonical MVP release gate.
- Canonical magnesium scenario remains required in RC chain.
- Compatibility checks remain required:
  - `python3 scripts/run_phase3_validation_matrix.py`
  - `python3 scripts/run_phase2_validation_matrix.py`
  - `python3 scripts/run_mvp_validation_matrix.py`
- RC evidence must support both:
  - latest summary (`artifacts/release/phase4_rc_summary.json`)
  - append-only historical archive + index for audit/replay

## Exact Surfaces In Scope

- RC rehearsal artifact write behavior (latest + archived copies)
- archive index/ledger generation and validation
- deterministic tests for archival contract and backward compatibility
- runbook/control-doc synchronization for audit workflow

## Exact Files In Scope

- `scripts/run_phase4_release_candidate.py`
- `scripts/verify_phase4_rc_archive.py`
- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_rc_archive.py`
- `tests/unit/test_phase4_gate_wrappers.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Extend `scripts/run_phase4_release_candidate.py` with deterministic archival support:
  - keep writing latest artifact to `artifacts/release/phase4_rc_summary.json`
  - optionally/by-default write timestamped archive copy (for example `artifacts/release/archive/YYYYMMDDTHHMMSSZ_phase4_rc_summary.json`)
  - update append-only index (for example `artifacts/release/archive/index.json`) with run metadata (`final_decision`, failing steps, command mode, created_at)
- Add archive verification command:
  - `python3 scripts/verify_phase4_rc_archive.py`
  - validates archive index schema, references, and consistency with stored artifacts
- Preserve backward compatibility for existing Sprint 15 command/JSON contract consumers.
- Update runbooks and control docs to treat archive index as canonical audit trail for repeated MVP rehearsal runs.

## Out of Scope

- any changes in `apps/api/src/alicebot_api/*`
- any changes in `workers/alicebot_worker/*`
- UI feature work
- connector breadth changes
- auth model changes

## Required Deliverables

- RC rehearsal archival + index contract
- archive verification script
- tests covering GO and NO_GO archival behavior
- updated closeout/runbook docs for archive-driven audit
- sprint build/review reports scoped to Sprint 16

## Acceptance Criteria

- `python3 scripts/run_phase4_release_candidate.py` passes and writes:
  - latest summary (`artifacts/release/phase4_rc_summary.json`)
  - archive entry + index update
- `python3 scripts/run_phase4_release_candidate.py --induce-step phase4_validation_matrix` fails as expected and archives NO_GO evidence without overwriting prior archive entries.
- `python3 scripts/verify_phase4_rc_archive.py` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- `python3 scripts/run_mvp_validation_matrix.py` remains PASS.
- `./.venv/bin/python -m pytest tests/integration/test_phase4_release_candidate.py tests/integration/test_phase4_rc_archive.py tests/unit/test_phase4_gate_wrappers.py -q` passes.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` are synchronized to Sprint 16 archive/audit focus.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing Sprint 15 RC summary schema fields
- keep archival format deterministic and machine-readable
- keep machine-independent paths and commands in docs

## Control Tower Task Cards

### Task 1: RC Archive Wiring

Owner: tooling operative

Write scope:

- `scripts/run_phase4_release_candidate.py`
- `scripts/verify_phase4_rc_archive.py`

### Task 2: Archive Contract Tests

Owner: tooling operative

Write scope:

- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_rc_archive.py`
- `tests/unit/test_phase4_gate_wrappers.py`

### Task 3: Docs + Control Sync

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

- verify no overlap with Sprint 12-15 runtime/gate-ownership scope
- verify archival index is deterministic and append-only
- verify GO and NO_GO runs are retained concurrently
- verify compatibility chains remain PASS

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact archive/index contract delta
- exact artifact path model (latest + archive + index)
- verification command outcomes
- explicit deferred scope

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed release-audit scoped
- archival behavior preserves historical GO/NO_GO evidence
- archive verification script catches malformed/missing records
- compatibility chains remain green
- no hidden runtime scope expansion

## Exit Condition

This sprint is complete when RC evidence is durable across repeated runs via a deterministic archive/index contract, with compatibility gates still green and no runtime scope expansion.
