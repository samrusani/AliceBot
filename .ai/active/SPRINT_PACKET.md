# SPRINT_PACKET.md

## Sprint Title

Phase 6 Sprint 24 (P6-S24): Trust Dashboard and Quality Release Evidence

## Sprint Type

feature

## Sprint Reason

P6-S23 shipped correction-impact and freshness-hygiene reliability signals. The remaining non-redundant Phase 6 seam is to make those quality semantics operator-visible and release-visible in one canonical dashboard/evidence flow.

## Sprint Intent

Ship a deterministic memory-quality dashboard and release-evidence seam that uses the same canonical semantics as the API/UI quality gates and review posture:

- `docs/phase6-product-spec.md`
- `docs/phase6-sprint-21-24-plan.md`
- `docs/phase6-memory-quality-model.md`

## Git Instructions

- Branch Name: `codex/phase6-sprint-24-trust-dashboard-quality-evidence`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the final planned Phase 6 seam and closes the trust-calibration loop.
- It avoids redundant rework of retrieval/correction logic by focusing only on visibility and release evidence.
- It gives operators one deterministic view of quality posture and what to review next.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 MVP qualification/sign-off is complete and remains canonical.
  - P5-S17 through P5-S20 continuity capture/recall/review/open-loop seams.
  - P6-S21 quality gate and deterministic review prioritization.
  - P6-S22 retrieval evaluation and ranking calibration.
  - P6-S23 correction impact and freshness hygiene, including recurrence/drift weekly signals.
- Required now (P6-S24):
  - operator-visible trust dashboard in `/memories`
  - deterministic quality evidence artifact for release/readiness reporting
  - explicit quality section integration in release-control reporting paths
- Explicitly out of P6-S24:
  - gate-threshold redesign
  - ranking/correction/freshness model redesign
  - connector/auth/orchestration expansion
  - new continuity object classes

## Design Truth

- Dashboard and release evidence must read from the same canonical quality semantics.
- Quality posture must remain deterministic for fixed input state.
- Operator guidance (what to review next) must be explicit and derived from canonical queue posture.
- Evidence output must be machine-checkable and archive-safe.

## Exact Surfaces In Scope

- memory quality dashboard payload seam
- `/memories` trust dashboard UI section
- deterministic quality evidence generation seam
- Phase 4 readiness/release reporting integration for quality evidence
- deterministic test coverage for dashboard/evidence behavior

## Exact Files In Scope

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/memories/page.tsx`
- `apps/web/app/memories/page.test.tsx`
- `scripts/run_phase4_readiness_gates.py`
- `scripts/run_phase4_release_candidate.py`
- `scripts/run_phase4_validation_matrix.py`
- `scripts/run_phase6_quality_evidence.py`
- `tests/unit/test_memory.py`
- `tests/unit/test_retrieval_evaluation.py`
- `tests/integration/test_memory_quality_gate_api.py`
- `tests/integration/test_retrieval_evaluation_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic quality-dashboard API surface (or deterministic extension of existing quality-gate surface) that aggregates:
  - gate status posture
  - queue posture/aging summary
  - retrieval quality summary
  - correction recurrence/freshness drift summary
  - recommended next review mode/action
- Add deterministic quality evidence command (`python3 scripts/run_phase6_quality_evidence.py`) that writes a canonical artifact for release/readiness usage.
- Integrate quality evidence summary into Phase 4 release/readiness reporting outputs without changing Phase 4 pass/fail semantics.
- Add `/memories` trust dashboard rendering using canonical API payload fields.
- Add test coverage for deterministic dashboard payload and quality evidence generation.

## Out of Scope

- changes to P6-S21 gate thresholds/status semantics
- changes to P6-S22 ranking contracts
- changes to P6-S23 correction/freshness behavior semantics
- connector/channel/auth/orchestration expansion
- broad UI redesign beyond `/memories` trust dashboard surfaces

## Required Deliverables

- deterministic quality dashboard contract and API implementation
- `/memories` trust dashboard UI with canonical posture fields
- deterministic quality evidence artifact generator and Phase 4 reporting integration
- API/web/script tests for dashboard and evidence seams
- synced docs and sprint reports

## Acceptance Criteria

- operator can view current quality posture and recommended review next-step in `/memories` without relying on inferred semantics.
- dashboard quality values match release-evidence quality values for the same state.
- `python3 scripts/run_phase6_quality_evidence.py` writes deterministic artifact output and exits successfully.
- Phase 4 reporting includes quality evidence summary while preserving existing GO/NO_GO semantics.
- `./.venv/bin/python -m pytest tests/unit/test_memory.py tests/unit/test_retrieval_evaluation.py tests/integration/test_memory_quality_gate_api.py tests/integration/test_retrieval_evaluation_api.py -q` passes.
- `pnpm --dir apps/web test -- app/memories/page.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P6-S24 scope and preserve “MVP complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P6-S21/P6-S22/P6-S23 contracts
- keep dashboard/evidence semantics server-side and deterministic
- keep release-control semantics stable (quality section additive only)
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Dashboard Contract + API

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `tests/unit/test_memory.py`
- `tests/unit/test_retrieval_evaluation.py`
- `tests/integration/test_memory_quality_gate_api.py`
- `tests/integration/test_retrieval_evaluation_api.py`

### Task 2: Quality Evidence Integration

Owner: tooling operative

Write scope:

- `scripts/run_phase6_quality_evidence.py`
- `scripts/run_phase4_readiness_gates.py`
- `scripts/run_phase4_release_candidate.py`
- `scripts/run_phase4_validation_matrix.py`

### Task 3: `/memories` Dashboard UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/memories/page.tsx`
- `apps/web/app/memories/page.test.tsx`

### Task 4: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6-S21/P6-S22/P6-S23 relitigation
- verify dashboard/evidence semantic parity
- verify no hidden connector/auth/orchestration expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact dashboard contract delta
- exact quality evidence artifact and reporting integration delta
- exact verification command outcomes
- explicit statement that P6-S21/P6-S22/P6-S23 contracts were preserved

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P6-S24 scoped
- dashboard/evidence semantics are canonical and deterministic
- UI/API/release quality values are consistent
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when memory quality posture is clearly visible in `/memories` and deterministically represented in release evidence, with no regression to shipped Phase 4/5/6 contracts.
