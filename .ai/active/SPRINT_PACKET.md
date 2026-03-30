# SPRINT_PACKET.md

## Sprint Title

Phase 6 Sprint 23 (P6-S23): Correction Impact and Freshness Hygiene

## Sprint Type

feature

## Sprint Reason

P6-S22 shipped deterministic retrieval evaluation and ranking calibration. The next non-redundant Phase 6 seam is ensuring correction actions and freshness posture drive immediate, durable recall behavior so stale or superseded truth does not quietly re-enter primary recall.

## Sprint Intent

Ship deterministic correction-impact and freshness-hygiene behavior across continuity recall/review/resumption surfaces, aligned to:

- `docs/phase6-product-spec.md`
- `docs/phase6-sprint-21-24-plan.md`
- `docs/phase6-memory-quality-model.md`

## Git Instructions

- Branch Name: `codex/phase6-sprint-23-correction-freshness-hygiene`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the next planned P6 seam after ranking calibration.
- It prevents redundant rework of P6-S21/P6-S22 by focusing only on correction effect durability and freshness posture hygiene.
- It closes the trust gap where corrected or aging truth may still be retrieved as current.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 MVP qualification/sign-off is complete and remains canonical.
  - P5-S17 through P5-S20 continuity capture/recall/review/open-loop seams.
  - P6-S21 quality gate and deterministic review prioritization.
  - P6-S22 retrieval evaluation and ranking calibration.
- Required now (P6-S23):
  - correction-impact durability in recall/resumption behavior
  - canonical freshness posture hygiene (`fresh`, `aging`, `stale`, `superseded`)
  - superseded/stale suppression for primary current-truth recall
  - correction recurrence and freshness drift evidence
- Explicitly out of P6-S23:
  - trust dashboard/release evidence dashboarding (P6-S24)
  - broad ranking-model redesign beyond correction/freshness effects
  - connector/auth/orchestration expansion
  - new continuity object classes

## Design Truth

- Correction actions must change primary recall behavior immediately and deterministically.
- Superseded memories remain historically visible but are not treated as current truth by default recall views.
- Freshness posture must be canonical, explicit, and shared across API and UI surfaces.
- Recurrence and freshness-drift evidence must be machine-checkable and reproducible.

## Exact Surfaces In Scope

- correction impact propagation through recall/resumption/open-loop brief outputs
- canonical freshness posture transitions and visibility
- superseded/stale hygiene for default recall behavior
- correction recurrence/freshness-drift summary seams
- deterministic tests for correction impact and freshness suppression behavior

## Exact Files In Scope

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-recall-panel.tsx`
- `apps/web/components/continuity-recall-panel.test.tsx`
- `apps/web/components/continuity-review-queue.tsx`
- `apps/web/components/continuity-review-queue.test.tsx`
- `apps/web/components/continuity-correction-form.tsx`
- `apps/web/components/continuity-correction-form.test.tsx`
- `tests/unit/test_continuity_review.py`
- `tests/unit/test_continuity_recall.py`
- `tests/unit/test_continuity_open_loops.py`
- `tests/unit/test_retrieval_evaluation.py`
- `tests/integration/test_continuity_review_api.py`
- `tests/integration/test_continuity_recall_api.py`
- `tests/integration/test_continuity_daily_weekly_review_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Ensure correction actions (`confirm`, `edit`, `supersede`, `mark_stale`, `delete`) produce deterministic immediate impact on default recall ordering/eligibility.
- Enforce canonical freshness posture transitions for active continuity objects and expose that posture consistently in recall/review/resumption outputs.
- Add deterministic correction-recurrence/freshness-drift evidence seam for quality tracking.
- Ensure superseded/stale objects remain audit-visible while being suppressed from default current-truth recall posture.
- Add test coverage for hot correction impact, freshness posture transitions, and superseded-chain suppression behavior.

## Out of Scope

- trust dashboard and release-evidence dashboarding work (P6-S24)
- connector/channel expansion
- auth model or orchestration changes
- broad UI redesign outside continuity correction/recall/review posture surfaces
- reopening P6-S21 gate semantics or P6-S22 ranking contracts

## Required Deliverables

- deterministic correction-impact behavior contract across recall/resumption/open-loop outputs
- canonical freshness posture contract and API/UI exposure
- correction-recurrence/freshness-drift summary seam
- API/web unit and integration tests for correction/freshness hygiene behavior
- synced docs and sprint reports

## Acceptance Criteria

- corrected and superseded memories are suppressed from default current-truth recall posture when replacement truth exists.
- correction actions update recall/resumption outputs immediately and deterministically for fixed state.
- freshness posture transitions are explicit and consistent across review and recall surfaces.
- correction recurrence and freshness-drift evidence is deterministic and reproducible.
- `./.venv/bin/python -m pytest tests/unit/test_continuity_review.py tests/unit/test_continuity_recall.py tests/unit/test_continuity_open_loops.py tests/unit/test_retrieval_evaluation.py tests/integration/test_continuity_review_api.py tests/integration/test_continuity_recall_api.py tests/integration/test_continuity_daily_weekly_review_api.py -q` passes.
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-recall-panel.test.tsx components/continuity-review-queue.test.tsx components/continuity-correction-form.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P6-S23 scope and preserve “MVP complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P6-S21 quality-gate/priority semantics
- preserve shipped P6-S22 ranking contracts except correction/freshness posture influence
- keep freshness/correction behavior deterministic and explicitly test-backed
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Correction Impact Backend

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/memory.py`
- `tests/unit/test_continuity_review.py`
- `tests/unit/test_continuity_recall.py`
- `tests/integration/test_continuity_review_api.py`
- `tests/integration/test_continuity_recall_api.py`

### Task 2: Freshness Hygiene + Metrics

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `apps/api/src/alicebot_api/main.py`
- `tests/unit/test_continuity_open_loops.py`
- `tests/unit/test_retrieval_evaluation.py`
- `tests/integration/test_continuity_daily_weekly_review_api.py`

### Task 3: Continuity UI Posture Alignment

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-recall-panel.tsx`
- `apps/web/components/continuity-recall-panel.test.tsx`
- `apps/web/components/continuity-review-queue.tsx`
- `apps/web/components/continuity-review-queue.test.tsx`
- `apps/web/components/continuity-correction-form.tsx`
- `apps/web/components/continuity-correction-form.test.tsx`

### Task 4: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6-S21/P6-S22 relitigation
- verify deterministic correction impact and freshness posture behavior
- verify no hidden connector/auth/orchestration expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact correction-impact behavior delta
- exact freshness posture/supersession hygiene delta
- exact correction-recurrence/freshness-drift evidence behavior
- exact verification command outcomes
- explicit deferred Phase 6 scope (P6-S24)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P6-S23 scoped
- correction impact is immediate and deterministic
- freshness posture and supersession hygiene are coherent and visible
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when correction actions and freshness posture deterministically control current-truth recall behavior, with reproducible evidence and no Phase 4 regression.
