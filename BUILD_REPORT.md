# BUILD_REPORT.md

## sprint objective
Implement Phase 8 Sprint 31 (P8-S31): deterministic governed execution routing for chief-of-staff handoff items, with explicit execution-readiness posture, auditable routing transitions, and draft-only approval-bounded behavior.

## completed work
- Added governed execution routing contract fields on `GET /v0/chief-of-staff`:
  - `execution_routing_summary`
  - `routed_handoff_items`
  - `routing_audit_trail`
  - `execution_readiness_posture`
- Added governed execution routing capture seam:
  - endpoint `POST /v0/chief-of-staff/execution-routing-actions`
  - explicit route targets: `task_workflow_draft`, `approval_workflow_draft`, `follow_up_draft_only`
  - explicit transitions: `routed`, `reaffirmed`
  - immutable continuity-note capture (`kind=chief_of_staff_execution_routing_action`)
- Added deterministic routing artifact assembly in chief-of-staff brief compilation:
  - deterministic routed-item ordering (`handoff_rank_asc`, `handoff_item_id_asc`)
  - deterministic routing audit ordering (`created_at_desc`, `id_desc`)
  - explicit approval-required non-autonomous readiness posture
- Added `/chief-of-staff` execution routing panel:
  - readiness posture visibility
  - live route controls for allowed targets
  - auditable routing transition history
- Added deterministic backend/web tests for routing seam and payload propagation.
- Tightened routing contract/test semantics:
  - execution-readiness `transition_order` now uses transition vocabulary (`routed`, `reaffirmed`)
  - routing integration test now asserts first transition is `routed` and repeat transition is `reaffirmed`
- Updated required docs for active sprint truth:
  - `README.md`
  - `ROADMAP.md`
  - `.ai/handoff/CURRENT_STATE.md`

## exact governed-routing contract delta
- `apps/api/src/alicebot_api/contracts.py`
  - Added literals/constants:
    - `ChiefOfStaffExecutionReadinessPosture = "approval_required_draft_only"`
    - `ChiefOfStaffExecutionRouteTarget`
    - `ChiefOfStaffExecutionRoutingTransition`
    - `CHIEF_OF_STAFF_EXECUTION_READINESS_POSTURE_ORDER`
    - `CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER`
    - `CHIEF_OF_STAFF_EXECUTION_ROUTED_ITEM_ORDER`
    - `CHIEF_OF_STAFF_EXECUTION_ROUTING_AUDIT_ORDER`
    - `CHIEF_OF_STAFF_EXECUTION_ROUTING_TRANSITIONS`
  - Added request input:
    - `ChiefOfStaffExecutionRoutingActionInput`
  - Added response/data records:
    - `ChiefOfStaffExecutionReadinessPostureRecord`
    - `ChiefOfStaffExecutionRoutingAuditRecord`
    - `ChiefOfStaffRoutedHandoffItemRecord`
    - `ChiefOfStaffExecutionRoutingSummary`
    - `ChiefOfStaffExecutionRoutingActionCaptureResponse`
  - Extended `ChiefOfStaffPriorityBriefRecord` with new routing/readiness fields.
- `apps/api/src/alicebot_api/chief_of_staff.py`
  - Added deterministic routing audit parse/list helpers and routing artifact builder.
  - Added `capture_chief_of_staff_execution_routing_action(...)`.
  - Extended `compile_chief_of_staff_priority_brief(...)` to emit routing/readiness artifacts.
- `apps/api/src/alicebot_api/main.py`
  - Added request model `ChiefOfStaffExecutionRoutingActionCaptureRequest`.
  - Added endpoint `POST /v0/chief-of-staff/execution-routing-actions`.
- `apps/web/lib/api.ts`
  - Added routing/readiness types and action capture payload/result types.
  - Added `captureChiefOfStaffExecutionRoutingAction(...)`.

## exact deterministic routing/execution-readiness behavior
- Routing actions are explicit operator actions only; no autonomous execution is introduced.
- For each handoff item, available route targets are deterministic by source kind.
- Routing status is inferred deterministically from latest routing transition per `(handoff_item_id, route_target)`.
- Routing transitions are auditable and deterministic for fixed state:
  - sorted by `created_at_desc`, then `id_desc`
  - transition vocabulary constrained to `routed`/`reaffirmed`
- Execution-readiness posture remains explicit and approval-required:
  - draft-only
  - no autonomous execution
  - no external side effects
  - approval path explicitly visible

## incomplete work
- None.

## files changed
- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.test.tsx`
- `apps/web/components/chief-of-staff-execution-routing-panel.tsx`
- `apps/web/components/chief-of-staff-execution-routing-panel.test.tsx`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `docs/phase8-product-spec.md`
- `docs/phase8-sprint-29-32-plan.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `.ai/active/SPRINT_PACKET.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py -q`
  - PASS (`9 passed`)
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q`
  - PASS (`13 passed`)
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-action-handoff-panel.test.tsx components/chief-of-staff-handoff-queue-panel.test.tsx components/chief-of-staff-execution-routing-panel.test.tsx lib/api.test.ts`
  - PASS (`5 files`, `45 tests`)
- `python3 scripts/run_phase4_validation_matrix.py`
  - PASS (`Phase 4 validation matrix result: PASS`)

## blockers/issues
- None.

## explicit deferred phase 8 scope beyond P8-S31
- autonomous execution of routed items
- connector/channel/auth/orchestration expansion
- redesign of shipped P8-S29 handoff generation semantics
- redesign of shipped P8-S30 queue/review lifecycle semantics
- outcome-learning seam planned for P8-S32

## recommended next step
Proceed to P8-S32 outcome-learning seam on top of the now-green P8-S31 verification gates.
