# SPRINT_PACKET.md

## Sprint Title

Phase 6 Sprint 22 (P6-S22): Retrieval Quality Evaluation and Ranking Calibration

## Sprint Type

feature

## Sprint Reason

P6-S21 shipped canonical quality-gate semantics and deterministic review prioritization. The next non-redundant phase step is retrieval quality calibration so recall ranking consistently favors current trustworthy memory (`confirmation`, `freshness`, `provenance`, `supersession posture`) with measurable precision evidence.

## Sprint Intent

Ship deterministic retrieval-evaluation seams and ranking calibration for continuity recall, with explainable ordering evidence and precision reporting aligned to Phase 6 trust-calibration docs:

- `docs/phase6-product-spec.md`
- `docs/phase6-sprint-21-24-plan.md`
- `docs/phase6-memory-quality-model.md`

## Git Instructions

- Branch Name: `codex/phase6-sprint-22-retrieval-ranking-calibration`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It addresses the next planned P6 risk seam after gate/queue semantics.
- It keeps scope narrow to ranking and evaluation, not schema/channel expansion.
- It converts memory-trust posture into measurable retrieval precision outcomes.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 MVP qualification/sign-off remains canonical.
  - P5-S17 through P5-S20 continuity capture/recall/resumption/review/open-loop seams.
  - P6-S21 memory-quality gate and deterministic queue-priority modes.
- Required now (P6-S22):
  - retrieval evaluation fixtures/suite
  - ranking calibration for confirmation/freshness/provenance/supersession posture
  - explainable ranking posture in recall outputs/UI
- Explicitly out of P6-S22:
  - correction/freshness policy redesign (P6-S23)
  - trust dashboard/release-evidence dashboarding (P6-S24)
  - connector breadth expansion
  - auth/orchestration redesign

## Design Truth

- Recall ordering must remain deterministic for fixed input state.
- Ranking posture must explicitly prefer active confirmed fresher truth over stale/superseded truth when query scope matches.
- Provenance quality and confirmation/freshness posture must be visible in recall output evidence.
- Evaluation fixtures and precision summary outputs must be reproducible and machine-checkable.

## Exact Surfaces In Scope

- continuity recall ranking policy calibration
- retrieval evaluation fixture + precision summary seams
- recall output ordering-evidence metadata
- continuity recall UI posture evidence updates
- deterministic test coverage for ranking behavior

## Exact Files In Scope

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/semantic_retrieval.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-recall-panel.tsx`
- `apps/web/components/continuity-recall-panel.test.tsx`
- `tests/unit/test_continuity_recall.py`
- `tests/unit/test_semantic_retrieval.py`
- `tests/unit/test_retrieval_evaluation.py`
- `tests/integration/test_continuity_recall_api.py`
- `tests/integration/test_retrieval_evaluation_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Calibrate recall ranking policy to explicitly account for:
  - confirmation posture
  - freshness posture
  - provenance quality
  - superseded/stale suppression posture
- Add retrieval-evaluation endpoint(s) and fixture-backed precision summary output.
- Extend recall response ordering evidence to show key ranking posture contributions.
- Update continuity recall UI to surface ranking posture evidence.
- Add deterministic tests for:
  - confirmed vs stale/superseded ordering behavior
  - provenance-backed tie-break behavior
  - evaluation precision summary determinism.

## Out of Scope

- new continuity object classes
- broad daily/weekly review redesign
- correction model redesign or new correction actions
- connector-driven retrieval expansion
- broad UI redesign outside continuity recall posture surfaces

## Required Deliverables

- calibrated recall ranking policy contract
- deterministic retrieval-evaluation API + fixture set
- recall ranking-evidence metadata in API/UI
- unit/integration/web tests for ranking/evaluation behavior
- synced docs and sprint reports

## Acceptance Criteria

- recall ordering remains deterministic and reflects calibrated posture priorities.
- confirmed/fresher active truths outrank stale/superseded candidates where appropriate for scoped recall queries.
- retrieval evaluation route returns deterministic precision summary from fixture-backed suite.
- recall output exposes enough ordering posture evidence to explain ranking behavior.
- `./.venv/bin/python -m pytest tests/unit/test_continuity_recall.py tests/unit/test_semantic_retrieval.py tests/unit/test_retrieval_evaluation.py tests/integration/test_continuity_recall_api.py tests/integration/test_retrieval_evaluation_api.py -q` passes.
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-recall-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P6-S22 scope and preserve “MVP complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P6-S21 quality-gate and queue-priority contracts
- keep ranking behavior deterministic and explicitly test-backed
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Ranking Backend Calibration

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/memory.py`
- `tests/unit/test_continuity_recall.py`
- `tests/integration/test_continuity_recall_api.py`

### Task 2: Retrieval Evaluation Seams

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `apps/api/src/alicebot_api/semantic_retrieval.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `tests/unit/test_retrieval_evaluation.py`
- `tests/unit/test_semantic_retrieval.py`
- `tests/integration/test_retrieval_evaluation_api.py`

### Task 3: Recall UI Evidence

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-recall-panel.tsx`
- `apps/web/components/continuity-recall-panel.test.tsx`

### Task 4: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6-S21 contract relitigation
- verify deterministic ranking/evaluation behavior
- verify no hidden connector or orchestration expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact ranking calibration delta
- exact retrieval-evaluation fixture/precision behavior
- exact verification command outcomes
- explicit deferred Phase 6 scope (P6-S23/P6-S24)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P6-S22 scoped
- ranking behavior is deterministic and explainable
- retrieval evaluation outputs are deterministic and useful
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when retrieval quality evaluation and recall ranking calibration are shipped with deterministic ordering evidence and no Phase 4 regression.
