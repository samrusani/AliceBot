# BUILD_REPORT.md

## sprint objective
Implement Phase 6 Sprint 22 (P6-S22): ship deterministic retrieval-quality evaluation seams and calibrate continuity recall ranking so confirmed/fresher/current truth is preferred over stale/superseded candidates with explainable ordering evidence in API/UI.

## completed work
- Implemented continuity recall ranking calibration in backend:
  - added explicit ranking posture dimensions for `freshness`, `provenance`, and `supersession` in recall ordering metadata.
  - calibrated deterministic ranking weights/order so confirmed + fresh + current truth outranks stale/superseded alternatives when scope/query match.
  - preserved deterministic tie-break behavior (`created_at`/`id`) and existing scope/query semantics.
- Added deterministic retrieval-evaluation seam:
  - new module: `apps/api/src/alicebot_api/retrieval_evaluation.py`.
  - new endpoint: `GET /v0/continuity/retrieval-evaluation`.
  - fixture suite includes 3 deterministic scenarios:
    - `confirmed_fresh_truth_preferred`
    - `provenance_breaks_tie`
    - `supersession_chain_prefers_current_truth`
  - precision behavior:
    - `top_k=1` per fixture
    - expected relevant item is top-ranked in all fixtures
    - `precision_at_k_mean=1.0`
    - `precision_at_1_mean=1.0`
    - `precision_target=0.8`
    - summary `status=pass`.
- Updated retrieval utilities:
  - added deterministic precision helpers in `semantic_retrieval.py` (`calculate_precision_at_k`, `calculate_mean_precision`).
- Updated continuity UI/API contract surfaces:
  - web API types now include expanded recall ordering posture fields and retrieval-evaluation response types.
  - continuity recall panel now renders ranking posture evidence pills (`freshness`, `provenance`, `supersession`).
  - continuity fixture data/tests updated to include expanded ordering evidence.
- Added/updated deterministic tests for ranking and evaluation:
  - unit: recall calibration behavior, provenance tie-break behavior, retrieval evaluation determinism.
  - integration: recall API ranking posture assertions and retrieval-evaluation endpoint behavior.

## incomplete work
- None inside P6-S22 sprint scope.

## files changed
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/semantic_retrieval.py`
- `apps/api/src/alicebot_api/retrieval_evaluation.py`
- `tests/unit/test_continuity_recall.py`
- `tests/unit/test_semantic_retrieval.py`
- `tests/unit/test_retrieval_evaluation.py`
- `tests/integration/test_continuity_recall_api.py`
- `tests/integration/test_retrieval_evaluation_api.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-recall-panel.tsx`
- `apps/web/components/continuity-recall-panel.test.tsx`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `./.venv/bin/python -m pytest tests/unit/test_continuity_recall.py tests/unit/test_semantic_retrieval.py tests/unit/test_retrieval_evaluation.py tests/integration/test_continuity_recall_api.py tests/integration/test_retrieval_evaluation_api.py -q`
  - PASS (`21 passed`)
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-recall-panel.test.tsx lib/api.test.ts`
  - PASS (`3 files`, `36 tests`)
- `python3 scripts/run_phase4_validation_matrix.py`
  - PASS (`Phase 4 validation matrix result: PASS`)

## blockers/issues
- No functional blockers in P6-S22 scope.
- Test execution requiring local Postgres access needed elevated runtime permissions in this environment; reruns with elevation passed.

## recommended next step
Proceed to P6-S23 correction impact and freshness hygiene while treating P6-S21 (quality-gate/queue-priority) and P6-S22 (retrieval-evaluation/ranking calibration) contracts as fixed baseline.

### deferred phase 6 scope (explicit)
- P6-S23: correction impact and freshness hygiene (not implemented in this sprint).
- P6-S24: trust dashboard and release-evidence dashboarding (not implemented in this sprint).
