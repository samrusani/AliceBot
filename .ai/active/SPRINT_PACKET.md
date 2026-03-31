# SPRINT_PACKET.md

## Sprint Title

Phase 7 Sprint 28 (P7-S28): Weekly Review and Outcome Learning

## Sprint Type

feature

## Sprint Reason

P7-S27 shipped deterministic preparation and resumption supervision. The next non-redundant step is closing the chief-of-staff loop with weekly review and explicit recommendation-outcome learning signals.

## Sprint Intent

Ship deterministic weekly review and outcome-learning seams on top of shipped P7-S25/P7-S26/P7-S27:

- weekly review artifact
- recommendation outcome capture (`accept`, `defer`, `ignore`, `rewrite`)
- learning signal rollups for future prioritization
- visible “why prioritization is changing” summary

## Git Instructions

- Branch Name: `codex/phase7-sprint-28-weekly-review-outcome-learning`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the final planned sprint in the Phase 7 sequence.
- It turns chief-of-staff guidance into a measurable feedback loop.
- It improves recommendation quality without widening platform scope.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP sign-off seams.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 trust calibration (`P6-S21` through `P6-S24`), complete as of March 31, 2026.
  - P7-S25 chief-of-staff priority dashboard.
  - P7-S26 follow-through supervision.
  - P7-S27 preparation and resumption supervision.
- Required now (P7-S28):
  - weekly review artifact and workflow surface
  - deterministic outcome capture for recommendation handling
  - learning summary signals for recommendation-quality drift
  - explicit operator/user visibility into why future recommendations shift
- Explicitly out of P7-S28:
  - connector/channel/auth/orchestration expansion
  - generic multi-agent platformization
  - autonomous external writes/sends

## Design Truth

- Outcome capture and learning summaries must be deterministic for fixed state.
- Outcome handling is feedback and guidance logic, not autonomous execution.
- Trust posture must remain explicit and continue to cap confidence.
- Weekly review must help close/defer/escalate loops with auditable rationale.

## Exact Surfaces In Scope

- chief-of-staff weekly review artifact/API seam
- recommendation outcome capture endpoint/seam
- learning summary rollup for priority behavior changes
- `/chief-of-staff` weekly review + outcome capture UI
- deterministic tests for outcome capture and learning summaries

## Exact Files In Scope

- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-priority-panel.tsx`
- `apps/web/components/chief-of-staff-priority-panel.test.tsx`
- `apps/web/components/chief-of-staff-follow-through-panel.tsx`
- `apps/web/components/chief-of-staff-follow-through-panel.test.tsx`
- `apps/web/components/chief-of-staff-preparation-panel.tsx`
- `apps/web/components/chief-of-staff-preparation-panel.test.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.test.tsx`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic weekly review artifact/API fields:
  - `weekly_review_brief`
  - `recommendation_outcomes`
  - `priority_learning_summary`
  - `pattern_drift_summary`
- Add deterministic outcome-capture seam for recommendation handling:
  - `accept`
  - `defer`
  - `ignore`
  - `rewrite`
- Add deterministic rollups:
  - acceptance/override trends
  - defer/ignore hotspots
  - explanation of priority shifts
- Add `/chief-of-staff` weekly review panel and outcome-capture controls.
- Add deterministic tests for outcome capture, learning rollups, and summary visibility.

## Out of Scope

- new connector breadth or external automation
- autonomous external side effects
- redesign of shipped P7-S25/P7-S26/P7-S27 semantics

## Required Deliverables

- weekly review and outcome-capture API/artifact seam
- deterministic learning summary rollups
- `/chief-of-staff` weekly review UI panel
- unit/integration/web tests for outcome-learning behavior
- synced docs and sprint reports

## Acceptance Criteria

- weekly review supports deterministic close/defer/escalate guidance with explicit rationale.
- recommendation outcomes (`accept`, `defer`, `ignore`, `rewrite`) are captured deterministically and auditable.
- learning summaries explain recommendation behavior changes without opaque heuristics.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-priority-panel.test.tsx components/chief-of-staff-follow-through-panel.test.tsx components/chief-of-staff-preparation-panel.test.tsx components/chief-of-staff-weekly-review-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P7-S28 scope and preserve “Phase 6 complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6/P7-S25/P7-S26/P7-S27 semantics
- keep side effects approval-bounded and explicit
- keep outcome-learning behavior deterministic and test-backed

## Control Tower Task Cards

### Task 1: Weekly Review + Outcome Engine

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/memory.py`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`

### Task 2: Chief-of-Staff Weekly Review UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-priority-panel.tsx`
- `apps/web/components/chief-of-staff-priority-panel.test.tsx`
- `apps/web/components/chief-of-staff-follow-through-panel.tsx`
- `apps/web/components/chief-of-staff-follow-through-panel.test.tsx`
- `apps/web/components/chief-of-staff-preparation-panel.tsx`
- `apps/web/components/chief-of-staff-preparation-panel.test.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.test.tsx`

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6/P7-S25/P7-S26/P7-S27 relitigation
- verify deterministic outcome capture and learning summaries
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact weekly-review/outcome contract delta
- exact deterministic outcome-capture and learning summary behavior
- exact verification command outcomes
- explicit statement that Phase 7 scope is complete after P7-S28

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P7-S28 scoped
- weekly review and outcome-learning outputs are deterministic and explainable
- recommendation behavior changes are visible and auditable
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice closes the chief-of-staff loop with deterministic weekly review and outcome-learning artifacts that improve recommendation accountability without regressing shipped Phase 4/5/6/P7-S25/P7-S26/P7-S27 behavior.
