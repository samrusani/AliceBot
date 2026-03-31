# SPRINT_PACKET.md

## Sprint Title

Phase 7 Sprint 26 (P7-S26): Follow-Through Supervision

## Sprint Type

feature

## Sprint Reason

P7-S25 shipped the deterministic chief-of-staff priority dashboard. The next non-redundant step is turning prioritized items into supervised follow-through so commitments and waiting-fors do not silently slip.

## Sprint Intent

Ship deterministic follow-through supervision on top of the shipped chief-of-staff artifact:

- overdue follow-up detection
- stale waiting-for detection
- slipped-commitment surfacing
- governed draft follow-up preparation (no autonomous send)

## Git Instructions

- Branch Name: `codex/phase7-sprint-26-follow-through-supervision`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the defined next sprint in the approved Phase 7 sequence.
- It deepens the value of P7-S25 without redesigning ranking foundations.
- It creates explicit loop-closing behavior while preserving approval boundaries.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP sign-off seams.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 trust calibration (`P6-S21` through `P6-S24`), complete as of March 31, 2026.
  - P7-S25 chief-of-staff priority engine and dashboard.
- Required now (P7-S26):
  - follow-through queue for overdue/stale/slipping items
  - deterministic escalation posture and action recommendations
  - draft follow-up artifact generation with approval-bounded execution posture
- Explicitly out of P7-S26:
  - preparation briefs (P7-S27 scope)
  - weekly outcome-learning loop (P7-S28 scope)
  - connector/channel/auth/orchestration expansion
  - autonomous external sends

## Design Truth

- Follow-through ordering and escalation must be deterministic for fixed state.
- Blocked vs waiting vs overdue posture must be explicit and distinct.
- Draft follow-ups are artifacts, not autonomous side effects.
- Trust posture continues to cap confidence and action strength.

## Exact Surfaces In Scope

- chief-of-staff follow-through artifact/API seam
- overdue/stale/slipping classification logic
- draft follow-up artifact generation seam
- `/chief-of-staff` follow-through view
- deterministic tests for classification, ordering, and draft generation

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
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic follow-through artifact/API fields:
  - `overdue_items`
  - `stale_waiting_for_items`
  - `slipped_commitments`
  - `escalation_posture`
  - `draft_follow_up` (artifact content + target metadata, no send)
- Add explicit posture labels and reasons for each follow-through item.
- Add deterministic recommendation actions for each item (`nudge`, `defer`, `escalate`, `close_loop_candidate`).
- Add `/chief-of-staff` follow-through panel with clear state separation and rationale visibility.
- Add tests for deterministic classification/order and artifact generation.

## Out of Scope

- P7-S27 preparation brief generation
- P7-S28 learning/feedback adaptation
- external send execution
- new connector breadth or side-effect automation

## Required Deliverables

- follow-through supervision API/artifact seam
- deterministic overdue/stale/slipping classification and ordering
- governed draft follow-up artifact generation
- `/chief-of-staff` follow-through UI panel
- unit/integration/web tests for follow-through behavior
- synced docs and sprint reports

## Acceptance Criteria

- overdue/stale/slipping items are surfaced deterministically with explicit posture and rationale.
- blocked/waiting/overdue states are clearly distinguished in API and UI.
- draft follow-up artifacts are generated deterministically and remain non-sending by default.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-priority-panel.test.tsx components/chief-of-staff-follow-through-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P7-S26 scope and preserve “Phase 6 complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6/P7-S25 semantics
- keep side effects approval-bounded and explicit
- keep follow-through behavior deterministic and test-backed

## Control Tower Task Cards

### Task 1: Follow-Through Engine + API

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

### Task 2: Chief-of-Staff Follow-Through UI

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

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6/P7-S25 relitigation
- verify deterministic follow-through classification and draft generation
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact follow-through contract delta
- exact deterministic classification/escalation behavior
- exact draft artifact behavior and non-send guarantees
- exact verification command outcomes
- explicit deferred scope (`P7-S27` and `P7-S28`)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P7-S26 scoped
- follow-through behavior is deterministic and explainable
- draft artifacts remain approval-bounded and non-autonomous
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice reliably supervises follow-through with deterministic overdue/stale/slipping visibility and governed draft follow-up artifacts, without regressing shipped Phase 4/5/6/P7-S25 behavior.
