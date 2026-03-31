# SPRINT_PACKET.md

## Sprint Title

Phase 7 Sprint 27 (P7-S27): Preparation Briefs and Resumption Supervision

## Sprint Type

feature

## Sprint Reason

P7-S26 shipped deterministic follow-through supervision. The next non-redundant sprint is proactive preparation and interruption recovery so users can resume faster before meetings, conversations, and tasks.

## Sprint Intent

Ship deterministic chief-of-staff preparation artifacts on top of shipped P7-S25/P7-S26 seams:

- preparation briefs for project/person/conversation/task
- what-changed summaries
- resumption supervision recommendations
- suggested talking points and prep checklist artifacts

## Git Instructions

- Branch Name: `codex/phase7-sprint-27-preparation-resumption-supervision`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the planned next step in the Phase 7 sequence.
- It extends from “what matters now” and “what is slipping” into “what to prepare now”.
- It keeps scope narrow by reusing shipped continuity, trust, and chief-of-staff artifacts.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP sign-off seams.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 trust calibration (`P6-S21` through `P6-S24`), complete as of March 31, 2026.
  - P7-S25 chief-of-staff priority dashboard.
  - P7-S26 chief-of-staff follow-through supervision.
- Required now (P7-S27):
  - deterministic preparation brief artifact seam
  - deterministic what-changed summary seam
  - deterministic prep checklist and talking-point generation
  - resumption supervision recommendations for upcoming context
- Explicitly out of P7-S27:
  - weekly outcome-learning loop and adaptive ranking changes (P7-S28 scope)
  - connector/channel/auth/orchestration expansion
  - autonomous external sends or writes

## Design Truth

- Preparation and resumption outputs must be deterministic for fixed state.
- Every recommendation must be provenance-backed and trust-calibrated.
- Low-trust memory posture must visibly downgrade recommendation confidence.
- Prep artifacts are guidance artifacts, not autonomous action execution.

## Exact Surfaces In Scope

- chief-of-staff preparation brief/API seam
- what-changed summary seam
- prep checklist and talking-points generation seam
- `/chief-of-staff` preparation/resumption view
- deterministic tests for preparation and resumption artifact behavior

## Exact Files In Scope

- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
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
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic preparation artifact/API fields:
  - `preparation_brief`
  - `what_changed_summary`
  - `prep_checklist`
  - `suggested_talking_points`
  - `resumption_supervision`
- Support scoped preparation requests by project/person/conversation/task.
- Add explicit trust-aware confidence posture for preparation/resumption guidance.
- Add `/chief-of-staff` preparation panel with rationale and provenance visibility.
- Add deterministic tests for output shape, ordering, and trust-aware confidence downgrade behavior.

## Out of Scope

- P7-S28 outcome-learning/adaptive feedback loop
- any autonomous external send/write behavior
- connector or channel breadth expansion
- redesign of shipped P7-S25/P7-S26 semantics

## Required Deliverables

- preparation/resumption artifact API seam
- deterministic what-changed and prep checklist behavior
- `/chief-of-staff` preparation UI panel
- unit/integration/web tests for preparation and resumption behavior
- synced docs and sprint reports

## Acceptance Criteria

- preparation briefs include relevant context, last decisions, open loops, and suggested talking points.
- what-changed and prep checklist outputs are deterministic for fixed input state.
- resumption supervision reduces ambiguity on “what to do next” and is trust-calibrated.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-priority-panel.test.tsx components/chief-of-staff-follow-through-panel.test.tsx components/chief-of-staff-preparation-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P7-S27 scope and preserve “Phase 6 complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6/P7-S25/P7-S26 semantics
- keep side effects approval-bounded and explicit
- keep preparation/resumption behavior deterministic and test-backed

## Control Tower Task Cards

### Task 1: Preparation Engine + API

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/memory.py`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`

### Task 2: Chief-of-Staff Preparation UI

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

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6/P7-S25/P7-S26 relitigation
- verify deterministic preparation/resumption behavior
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact preparation/resumption contract delta
- exact deterministic what-changed/checklist/talking-points behavior
- exact verification command outcomes
- explicit deferred scope (`P7-S28`)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P7-S27 scoped
- preparation and resumption outputs are deterministic and provenance-backed
- trust-aware confidence posture is explicit
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice provides deterministic preparation and resumption supervision artifacts that reduce interruption recovery and pre-meeting planning effort, without regressing shipped Phase 4/5/6/P7-S25/P7-S26 behavior.
