# SPRINT_PACKET.md

## Sprint Title

Phase 8 Sprint 31 (P8-S31): Governed Execution Routing

## Sprint Type

feature

## Sprint Reason

P8-S30 shipped deterministic handoff queue and operational review seams on top of P8-S29 artifacts. The next non-redundant seam is routing high-value handoffs into existing governed task/approval workflows with explicit execution-readiness posture and auditable transition history.

Planning anchors:

- `docs/phase8-product-spec.md`
- `docs/phase8-sprint-29-32-plan.md`

## Sprint Intent

Ship deterministic governed-routing seams on top of shipped P8-S29/P8-S30:

- route selected handoff items into existing task/approval workflow drafts
- add explicit execution-readiness and approval-required visibility
- preserve draft-only, approval-bounded posture with no autonomous side effects
- expose routing transition audit trail in API and `/chief-of-staff`

## Git Instructions

- Branch Name: `codex/phase8-sprint-31-governed-execution-routing`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the planned next Phase 8 seam after shipped P8-S30 queue/review.
- It turns queueed handoffs into governed workflow transitions without widening autonomy.
- It establishes a deterministic execution bridge before outcome-learning work in P8-S32.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP sign-off seams.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 trust calibration (`P6-S21` through `P6-S24`), complete as of March 31, 2026.
  - Phase 7 chief-of-staff layer complete (`P7-S25` through `P7-S28`).
  - Phase 8 Sprint 29 (`P8-S29`) action handoff artifacts and explicit non-autonomous execution posture.
  - Phase 8 Sprint 30 (`P8-S30`) handoff queue lifecycle and operator review transitions.
- Required now (P8-S31):
  - deterministic routing of selected handoff items into existing task/approval workflow drafts
  - explicit execution-readiness posture and approval-required path visibility
  - auditable routing transition history from handoff queue toward governed execution
- Explicitly out of P8-S31:
  - autonomous execution or external connector side effects
  - redesign of P8-S29 handoff generation semantics
  - redesign of P8-S30 queue lifecycle semantics
  - connector/channel/auth/orchestration expansion

## Design Truth

- Routing behavior must be deterministic for fixed state.
- Routing must stay approval-bounded and draft-first.
- Every routing transition must be explicit and auditable.
- Existing governance and policy boundaries remain authoritative.

## Exact Surfaces In Scope

- chief-of-staff governed-routing artifact/API seam
- execution-readiness posture and approval-path visibility
- routing transition audit trail seam
- `/chief-of-staff` execution routing panel
- deterministic tests for routing behavior and posture preservation

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
- `apps/web/components/chief-of-staff-execution-routing-panel.tsx`
- `apps/web/components/chief-of-staff-execution-routing-panel.test.tsx`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic routing fields on chief-of-staff payloads:
  - `execution_routing_summary`
  - `routed_handoff_items`
  - `routing_audit_trail`
  - `execution_readiness_posture`
- Add explicit governed routing seam for selected handoff items:
  - task-workflow draft routing
  - approval-workflow draft routing
  - draft-only follow-up routing where applicable
- Add deterministic routing posture behavior:
  - approval-required path visibility
  - explicit non-autonomous guarantees
  - deterministic transition ordering metadata
- Add `/chief-of-staff` execution routing panel with posture, route controls, and transition history.
- Add deterministic tests for routing transitions, approval posture preservation, and no-autonomous-side-effect guarantees.

## Out of Scope

- automatic execution of routed items
- connector/channel expansion
- changes to shipped P8-S29 generation semantics
- changes to shipped P8-S30 queue lifecycle semantics

## Required Deliverables

- governed execution routing API/artifact seam
- deterministic routing transition behavior
- execution-readiness and approval-path visibility
- `/chief-of-staff` execution routing UI panel
- unit/integration/web tests for routing behavior
- synced docs and sprint reports

## Acceptance Criteria

- selected handoff items can be routed into existing governed task/approval draft flows without manual reconstruction.
- routing transitions are deterministic, explicit, and auditable for fixed state.
- approval-required and non-autonomous posture remains explicit and preserved.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-action-handoff-panel.test.tsx components/chief-of-staff-handoff-queue-panel.test.tsx components/chief-of-staff-execution-routing-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P8-S31 scope and preserve “P8-S29/P8-S30 shipped” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6/P7 semantics
- preserve shipped P8-S29 handoff-generation semantics
- preserve shipped P8-S30 queue/review semantics
- keep side effects approval-bounded and explicit
- keep routing behavior deterministic and test-backed

## Control Tower Task Cards

### Task 1: Governed Routing Engine + API

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

### Task 2: Chief-of-Staff Routing UI

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
- `apps/web/components/chief-of-staff-execution-routing-panel.tsx`
- `apps/web/components/chief-of-staff-execution-routing-panel.test.tsx`

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6/P7/P8-S29/P8-S30 relitigation
- verify deterministic routing transitions and posture guarantees
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact governed-routing contract delta
- exact deterministic routing/execution-readiness behavior
- exact verification command outcomes
- explicit deferred Phase 8 scope beyond P8-S31

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P8-S31 scoped
- routing outputs/transitions are deterministic and explainable
- approval-bounded execution posture is explicit and preserved
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice can deterministically route selected chief-of-staff handoff items into existing governed task/approval draft workflows with explicit execution-readiness posture and auditable transition history, without regressing shipped Phase 4/5/6/7 and P8-S29/P8-S30 behavior.
