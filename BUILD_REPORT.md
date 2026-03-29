# BUILD_REPORT.md

## Sprint Objective
Implement Phase 5 Sprint 17: ship typed continuity backbone plus fast capture inbox with conservative admission and provenance visibility.

## Completed Work
- Added migration `20260329_0041_phase5_continuity_backbone` with:
  - immutable `continuity_capture_events`
  - typed `continuity_objects`
  - deterministic constraints for object types, explicit signals, posture, confidence bounds
  - RLS/policies/grants and inbox/object indexes
- Added backend continuity contracts and persistence seams:
  - typed literals/records for capture create/list/detail and continuity objects
  - store methods for capture event create/list/count/detail and object create/list/detail
- Added continuity admission logic:
  - always persist capture event
  - explicit signal mapping:
    - `remember_this -> MemoryFact`
    - `task/next_action -> NextAction`
    - `decision -> Decision`
    - `commitment -> Commitment`
    - `waiting_for -> WaitingFor`
    - `blocker -> Blocker`
    - `note -> Note`
  - high-confidence prefix mapping for deterministic no-signal capture (`decision:`, `task:`, `todo:`, `next:`, `commitment:`, `waiting for:`, `blocker:`, `remember:`, `fact:`, `note:`)
  - ambiguous capture posture: `TRIAGE`
  - provenance on every derived object (`capture_event_id`, `source_kind`, `admission_reason`)
- Added API routes:
  - `POST /v0/continuity/captures`
  - `GET /v0/continuity/captures`
  - `GET /v0/continuity/captures/{capture_event_id}`
- Added web fast-capture inbox surface:
  - `apps/web/app/continuity/page.tsx`
  - submit capture with optional explicit signal
  - list recent captures with `DERIVED`/`TRIAGE` posture
  - detail panel with derived object/provenance or triage posture
  - live API + fixture fallback behavior
- Added/updated tests for migration, capture/object services, API integration, and web page/components.
- Synced phase/control docs for active P5-S17 scope and deferred P5-S18/19/20 scope.

## Exact Capture/Backbone Delta
- New immutable capture backbone table and typed continuity object table.
- Capture and durable object flows are now distinct.
- Durable object admission is conservative and deterministic, with explicit triage for ambiguity.
- Capture detail and inbox expose provenance/posture directly.

## Exact Triage/Admission Behavior
- Admission default: `TRIAGE` with reason `ambiguous_capture_requires_triage`.
- Admission upgrades to `DERIVED` only when:
  - explicit signal is supplied, or
  - deterministic high-confidence prefix rule matches.
- Every capture persists even when no durable object is created.

## Incomplete Work
- No implementation gaps inside P5-S17 code scope.

## Files Changed
- `apps/api/alembic/versions/20260329_0041_phase5_continuity_backbone.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/continuity_objects.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-capture-form.tsx`
- `apps/web/components/continuity-capture-form.test.tsx`
- `apps/web/components/continuity-inbox-list.tsx`
- `apps/web/components/continuity-inbox-list.test.tsx`
- `tests/unit/test_20260329_0041_phase5_continuity_backbone.py`
- `tests/unit/test_continuity_capture.py`
- `tests/unit/test_continuity_objects.py`
- `tests/integration/test_continuity_capture_api.py`
- `docs/phase5-product-spec.md`
- `docs/phase5-sprint-17-20-plan.md`
- `docs/phase5-continuity-object-model.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
- `./.venv/bin/python -m pytest tests/unit/test_20260329_0041_phase5_continuity_backbone.py tests/unit/test_continuity_capture.py tests/unit/test_continuity_objects.py tests/integration/test_continuity_capture_api.py -q`
  - PASS (`15 passed in 1.51s`, elevated run)
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-capture-form.test.tsx components/continuity-inbox-list.test.tsx lib/api.test.ts`
  - PASS (`32 passed`)
- `python3 scripts/run_phase4_validation_matrix.py`
  - PASS (`Phase 4 validation matrix result: PASS`, elevated run)

## Blockers/Issues
- Sandbox-localhost restriction blocks DB-backed integration tests and matrix runs in non-elevated mode.
  - resolved by re-running with elevated execution

## Explicit Deferred Phase 5 Scope (P5-S18/P5-S19/P5-S20)
- broad recall query UX and ranking surface
- deterministic resumption brief product surface
- memory correction queue and supersession workflows
- daily/weekly open-loop review dashboards

## Recommended Next Step
Open the sprint PR for Control Tower review; acceptance commands now run in repo-compatible form and Phase 4 compatibility remains PASS.
