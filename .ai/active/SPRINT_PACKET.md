# SPRINT_PACKET.md

## Sprint Title

Phase 4 Sprint 17: RC Archive Concurrency Hardening

## Sprint Type

hardening

## Sprint Reason

Phase 4 is functionally complete for MVP scope, with one non-blocking operational risk left: concurrent `run_phase4_release_candidate.py` runs can race when updating `artifacts/release/archive/index.json`.

## Sprint Intent

Harden RC archive/index writes with deterministic locking + atomic update behavior so concurrent rehearsals cannot drop or corrupt ledger entries.

## Git Instructions

- Branch Name: `codex/phase4-sprint-17-rc-archive-concurrency-hardening`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It resolves the only remaining non-blocking risk from Sprint 16 review.
- It improves reliability of extensive MVP rehearsal/testing workflows.
- It does not reopen runtime/API scope.

## Redundancy Guard

- Already shipped through Sprint 16:
  - canonical Phase 4 gate ownership
  - RC rehearsal GO/NO_GO evidence
  - append-only archive/index retention
- Required now (Sprint 17):
  - concurrency-safe archive index append behavior
  - atomic file-write guarantees for index updates
  - deterministic tests for parallel/contended update paths
- Explicitly out of Sprint 17:
  - gate semantics changes
  - runtime behavior/schema changes under `apps/api` or `workers`
  - connector/auth/platform changes

## Design Truth

- RC output must remain backward compatible:
  - latest summary: `artifacts/release/phase4_rc_summary.json`
  - archive summary copies under `artifacts/release/archive/`
  - append-only ledger: `artifacts/release/archive/index.json`
- New hardening must prevent lost updates when multiple RC commands run close together.
- Existing phase compatibility checks remain unchanged:
  - `run_phase4_validation_matrix.py`
  - `run_phase3_validation_matrix.py`
  - `run_phase2_validation_matrix.py`
  - `run_mvp_validation_matrix.py`

## Exact Surfaces In Scope

- lock acquisition/release behavior around archive index update
- atomic write/replace semantics for index persistence
- deterministic retry/timeout behavior for lock contention
- archive verification updates for hardening guarantees

## Exact Files In Scope

- `scripts/run_phase4_release_candidate.py`
- `scripts/verify_phase4_rc_archive.py`
- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_rc_archive.py`
- `tests/unit/test_phase4_gate_wrappers.py`
- `docs/runbooks/phase4-closeout-packet.md`
- `docs/runbooks/phase4-validation-matrix.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Implement concurrency-safe index append strategy in `run_phase4_release_candidate.py`:
  - deterministic lock file/path (for example `artifacts/release/archive/index.lock`)
  - bounded wait with explicit failure message/exit behavior on lock timeout
  - atomic index write (temp file + atomic replace)
- Ensure archive artifact creation and index append are consistent under contention.
- Extend `verify_phase4_rc_archive.py` to validate hardening invariants where applicable.
- Add/expand tests that simulate contended index updates and verify no ledger entry loss.
- Update runbooks/control docs with lock/timeout and failure-handling expectations.

## Out of Scope

- any changes in `apps/api/src/alicebot_api/*`
- any changes in `workers/alicebot_worker/*`
- UI changes
- connector/auth expansion
- new gate steps or changed pass/fail criteria for Phase 4/3/2/MVP chains

## Required Deliverables

- concurrency-safe RC archive index write path
- deterministic lock contention behavior contract
- contended-write test coverage
- updated closeout docs for hardening behavior
- sprint-scoped build/review reports

## Acceptance Criteria

- Two sequential or near-concurrent RC runs do not lose archive index entries.
- `python3 scripts/run_phase4_release_candidate.py` still passes and writes latest + archive + index.
- `python3 scripts/run_phase4_release_candidate.py --induce-step phase4_validation_matrix` still archives NO_GO evidence correctly.
- Lock contention behavior is deterministic:
  - explicit timeout/failure contract is test-covered.
- `python3 scripts/verify_phase4_rc_archive.py` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase3_validation_matrix.py` remains PASS.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- `python3 scripts/run_mvp_validation_matrix.py` remains PASS.
- `./.venv/bin/python -m pytest tests/integration/test_phase4_release_candidate.py tests/integration/test_phase4_rc_archive.py tests/unit/test_phase4_gate_wrappers.py -q` passes.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` are synchronized to Sprint 17 hardening focus.

## Implementation Constraints

- do not introduce new dependencies
- preserve Sprint 16 archive/index schema and existing field names
- keep deterministic machine-readable output
- keep machine-independent commands/paths in docs

## Control Tower Task Cards

### Task 1: Locking + Atomic Write Path

Owner: tooling operative

Write scope:

- `scripts/run_phase4_release_candidate.py`
- `scripts/verify_phase4_rc_archive.py`

### Task 2: Contention Tests

Owner: tooling operative

Write scope:

- `tests/integration/test_phase4_release_candidate.py`
- `tests/integration/test_phase4_rc_archive.py`
- `tests/unit/test_phase4_gate_wrappers.py`

### Task 3: Docs Sync

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

- verify no scope expansion beyond RC archive hardening
- verify no lost index entries under contention scenarios
- verify compatibility chain remains green
- verify docs and active packet stay aligned

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact locking/atomic-write implementation approach
- contention scenario results
- verification command outcomes
- explicit deferred scope

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed hardening-scoped
- lock + atomic write behavior prevents lost updates
- failure modes are explicit and test-backed
- compatibility chains remain green
- no hidden runtime scope expansion

## Exit Condition

This sprint is complete when RC archive/index updates are concurrency-safe and deterministic, with no lost evidence entries under contention and all compatibility gates still passing.
