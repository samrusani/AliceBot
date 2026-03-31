# BUILD_REPORT.md

## sprint objective
Implement Phase 7 Sprint 28 (P7-S28): deterministic weekly review and recommendation outcome-learning seams for chief-of-staff, including auditable outcome capture (`accept`, `defer`, `ignore`, `rewrite`), deterministic learning rollups, visible priority-shift rationale, and `/chief-of-staff` weekly review + outcome controls.

## completed work
- Extended chief-of-staff contracts and response shape with P7-S28 fields:
  - `weekly_review_brief`
  - `recommendation_outcomes`
  - `priority_learning_summary`
  - `pattern_drift_summary`
- Added deterministic recommendation outcome capture seam:
  - new endpoint: `POST /v0/chief-of-staff/recommendation-outcomes`
  - new request/response contracts for outcome capture and returned learning summaries
  - auditable persistence via continuity capture + continuity note object records (no autonomous external side effects)
- Added deterministic weekly review synthesis in `compile_chief_of_staff_priority_brief`:
  - consumes continuity weekly review rollup
  - computes explicit close/defer/escalate guidance with deterministic ordering and rationale
- Added deterministic outcome-learning rollups:
  - outcome counts by type (`accept`, `defer`, `ignore`, `rewrite`)
  - acceptance and override rates
  - defer/ignore hotspots (stable count/key ordering)
  - explicit priority-shift explanation
  - explicit pattern drift posture (`improving`, `stable`, `drifting`, `insufficient_signal`) with supporting signals
- Added chief-of-staff weekly review UI panel and controls:
  - new `ChiefOfStaffWeeklyReviewPanel` component
  - visible weekly rollup, guidance, outcomes, learning summary, drift summary
  - outcome-capture controls wired to the new API seam
- Extended web API client/types for new chief-of-staff fields and outcome capture helper.
- Updated and expanded unit/integration/web tests for outcome capture, weekly review rendering, and learning rollups.
- Updated sprint-scoped docs (`README.md`, `ROADMAP.md`, `.ai/handoff/CURRENT_STATE.md`) to reflect active P7-S28 scope while preserving Phase 6 completion truth.

## exact weekly-review/outcome contract delta
- `apps/api/src/alicebot_api/contracts.py`
  - Added literals:
    - `ChiefOfStaffRecommendationOutcome = Literal["accept", "defer", "ignore", "rewrite"]`
    - `ChiefOfStaffWeeklyReviewGuidanceAction = Literal["close", "defer", "escalate"]`
    - `ChiefOfStaffPatternDriftPosture = Literal["improving", "stable", "drifting", "insufficient_signal"]`
  - Added constants/ordering sets:
    - `CHIEF_OF_STAFF_RECOMMENDATION_OUTCOMES`
    - `CHIEF_OF_STAFF_WEEKLY_REVIEW_GUIDANCE_ACTIONS`
    - `CHIEF_OF_STAFF_RECOMMENDATION_OUTCOME_ORDER`
    - `CHIEF_OF_STAFF_OUTCOME_HOTSPOT_ORDER`
  - Added request/response contracts:
    - `ChiefOfStaffRecommendationOutcomeCaptureInput`
    - `ChiefOfStaffRecommendationOutcomeCaptureResponse`
  - Added new chief-of-staff records:
    - `ChiefOfStaffWeeklyReviewBriefRecord`
    - `ChiefOfStaffRecommendationOutcomeSection`
    - `ChiefOfStaffPriorityLearningSummaryRecord`
    - `ChiefOfStaffPatternDriftSummaryRecord`
  - Extended `ChiefOfStaffPriorityBriefRecord` with:
    - `weekly_review_brief`
    - `recommendation_outcomes`
    - `priority_learning_summary`
    - `pattern_drift_summary`

## exact deterministic outcome-capture and learning-summary behavior
- Outcome capture (`POST /v0/chief-of-staff/recommendation-outcomes`):
  - validates deterministic outcome/action enums
  - enforces rewrite-title rule (`rewrite` requires `rewritten_title`; other outcomes reject it)
  - writes an auditable continuity capture event and continuity note object (`kind=chief_of_staff_recommendation_outcome`)
  - returns captured outcome plus updated recommendation outcomes + learning summaries for the scoped brief
- Recommendation outcome aggregation:
  - parsed only from continuity note records tagged with `kind=chief_of_staff_recommendation_outcome`
  - deterministic sort order: `created_at_desc`, `id_desc`
  - deterministic summary counts for all four outcomes
- Priority learning summary:
  - deterministic totals/counts
  - deterministic `acceptance_rate` and `override_rate` (rounded)
  - deterministic defer/ignore hotspots ordered by `count_desc`, then `key_asc`
  - explicit `priority_shift_explanation` derived from outcome mix
- Pattern drift summary:
  - deterministic posture assignment (`improving`/`stable`/`drifting`/`insufficient_signal`)
  - explicit reason + stable supporting signal lines
- Weekly review guidance:
  - deterministic close/defer/escalate guidance list with stable ranking and signal counts
  - explicit rationale text per guidance item

## incomplete work
- None within P7-S28 scope.

## files changed
- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-priority-panel.test.tsx`
- `apps/web/components/chief-of-staff-follow-through-panel.test.tsx`
- `apps/web/components/chief-of-staff-preparation-panel.test.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.tsx` (new)
- `apps/web/components/chief-of-staff-weekly-review-panel.test.tsx` (new)
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q`
  - PASS (`7 passed`)
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-priority-panel.test.tsx components/chief-of-staff-follow-through-panel.test.tsx components/chief-of-staff-preparation-panel.test.tsx components/chief-of-staff-weekly-review-panel.test.tsx lib/api.test.ts`
  - PASS (`6 files, 46 tests`)
- `python3 scripts/run_phase4_validation_matrix.py`
  - PASS (`Phase 4 validation matrix result: PASS`)

## blockers/issues
- No unresolved implementation blockers.
- Intermediate validation runs initially failed due control-doc marker mismatch and sandboxed DB access; resolved by doc synchronization and rerun with local DB access.

## recommended next step
Proceed to merge review for P7-S28 and begin Phase 8 planning from the shipped P7-S25/P7-S26/P7-S27/P7-S28 baseline without reopening prior semantics.

Phase 7 scope is complete after P7-S28.
