# SPRINT_PACKET.md

## Sprint Title

Phase 8 Sprint 30 (P8-S30): Handoff Queue and Operational Review

## Sprint Type

feature

## Sprint Reason

P8-S29 shipped deterministic chief-of-staff action handoff artifacts and explicit approval-bounded execution posture. The next non-redundant seam is operationalizing those artifacts into a visible deterministic queue with explicit lifecycle states and operator review controls.

Planning anchors:

- `docs/phase8-product-spec.md`
- `docs/phase8-sprint-29-32-plan.md`

## Sprint Intent

Ship deterministic queue and review seams on top of shipped P8-S29 handoff artifacts:

- queue lifecycle states for handoff items
- deterministic queue ordering and grouped posture visibility
- explicit operator review actions for lifecycle transitions
- stale and expired handoff surfacing with no silent drops

## Git Instructions

- Branch Name: `codex/phase8-sprint-30-handoff-queue-operational-review`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the planned next Phase 8 seam after shipped P8-S29 artifacts.
- It reduces execution friction by making handoff backlog state explicit and actionable.
- It adds operational control without widening autonomy or connector scope.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP sign-off seams.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 trust calibration (`P6-S21` through `P6-S24`), complete as of March 31, 2026.
  - Phase 7 chief-of-staff layer complete (`P7-S25` through `P7-S28`).
  - Phase 8 Sprint 29 (`P8-S29`) deterministic action handoff artifacts and explicit non-autonomous execution posture.
- Required now (P8-S30):
  - queue lifecycle model for handoff items (`ready`, `pending_approval`, `executed`, `stale`, `expired`)
  - deterministic grouped queue visibility and ordering
  - explicit operator review actions to transition queue posture
- Explicitly out of P8-S30:
  - autonomous execution or connector side effects
  - redesign of P8-S29 handoff generation semantics
  - broader orchestration/channel/auth expansion

## Design Truth

- Queue behavior must be deterministic for fixed state.
- Queue transitions must be explicit and auditable.
- Handoff artifacts remain approval-bounded preparation outputs only.
- Stale and expired handoffs must remain visible, not silently dropped.

## Exact Surfaces In Scope

- chief-of-staff handoff queue artifact/API seam
- deterministic queue grouping and ordering metadata
- operator review-action transition seam
- `/chief-of-staff` handoff queue panel
- deterministic tests for queue ordering and transition behavior

## Exact Files In Scope

- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/tasks.py`
- `apps/api/src/alicebot_api/approvals.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.test.tsx`
- `apps/web/components/chief-of-staff-handoff-queue-panel.tsx`
- `apps/web/components/chief-of-staff-handoff-queue-panel.test.tsx`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic queue fields on chief-of-staff payloads:
  - `handoff_queue_summary`
  - `handoff_queue_groups`
  - `handoff_review_actions`
- Add lifecycle state model for handoff items:
  - `ready`
  - `pending_approval`
  - `executed`
  - `stale`
  - `expired`
- Add deterministic queue ordering and posture grouping behavior.
- Add explicit operator review-action seam for lifecycle transitions.
- Add `/chief-of-staff` handoff queue panel with grouped visibility and review controls.
- Add deterministic tests for ordering, grouping, and transition consistency.

## Out of Scope

- automatic execution of queue items
- connector/channel expansion
- changes to shipped P8-S29 artifact generation semantics

## Required Deliverables

- handoff queue API/artifact seam
- deterministic queue ordering/grouping behavior
- operator review-action transition behavior
- `/chief-of-staff` handoff queue UI panel
- unit/integration/web tests for queue behavior
- synced docs and sprint reports

## Acceptance Criteria

- queue states are explicit, deterministic, and auditable for fixed state.
- queue ordering/grouping is deterministic and surfaces stale/expired items explicitly.
- operator review actions update queue posture consistently without autonomous side effects.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-action-handoff-panel.test.tsx components/chief-of-staff-handoff-queue-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P8-S30 scope and preserve “P8-S29 shipped” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6/P7 semantics
- preserve shipped P8-S29 handoff generation semantics
- keep side effects approval-bounded and explicit
- keep queue behavior deterministic and test-backed

## Control Tower Task Cards

### Task 1: Handoff Queue Engine + API

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/tasks.py`
- `apps/api/src/alicebot_api/approvals.py`
- `apps/api/src/alicebot_api/memory.py`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`

### Task 2: Chief-of-Staff Queue UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.test.tsx`
- `apps/web/components/chief-of-staff-handoff-queue-panel.tsx`
- `apps/web/components/chief-of-staff-handoff-queue-panel.test.tsx`

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6/P7/P8-S29 relitigation
- verify deterministic queue ordering and transition posture
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact handoff-queue contract delta
- exact deterministic grouping/ordering/transition behavior
- exact verification command outcomes
- explicit deferred Phase 8 scope beyond P8-S30

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P8-S30 scoped
- queue outputs and transitions are deterministic and explainable
- approval-bounded execution posture remains explicit and preserved
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice can present and operate a deterministic chief-of-staff handoff queue with explicit lifecycle posture and operator review transitions, without regressing shipped Phase 4/5/6/7 and P8-S29 behavior.
