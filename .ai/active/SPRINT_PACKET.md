# SPRINT_PACKET.md

## Sprint Title

Phase 5 Sprint 17 (P5-S17): Continuity Backbone and Fast Capture

## Sprint Type

feature

## Sprint Reason

Phase 4 MVP qualification/sign-off is complete. The first Phase 5 non-redundant delivery is the typed continuity backbone and one fast capture flow, because all later Phase 5 recall/resumption/review work depends on it.

## Sprint Intent

Ship a deterministic typed continuity object backbone plus fast capture inbox flow that always preserves immutable capture events and only promotes durable objects when signals are explicit or high-confidence.

## Git Instructions

- Branch Name: `codex/phase5-sprint-17-continuity-backbone-fast-capture`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It starts Phase 5 with the minimum shared data model required by all later sprints.
- It creates immediate user value (capture without loss) while keeping admission conservative.
- It avoids redundant work by not touching recall/resumption/review dashboards yet.

## Redundancy Guard

- Already shipped in Phase 4:
  - release-control, RC rehearsal, archive/index, sign-off tooling
- Required now (P5-S17):
  - continuity object contracts
  - fast capture API/UI
  - triage posture for ambiguous captures
- Explicitly out of P5-S17:
  - broad recall UX
  - deterministic resumption briefs
  - memory correction queues
  - daily/weekly review dashboards

## Design Truth

- Every capture produces an immutable capture event.
- Durable continuity objects are typed and provenance-backed.
- Admission defaults to conservative behavior (`NOOP`/triage) for ambiguous inputs.
- Raw capture events and derived continuity objects remain distinct.

## Exact Surfaces In Scope

- typed continuity object contracts and persistence seams
- capture intake endpoint(s) with explicit signal typing
- capture inbox review surface (list/detail)
- triage posture visibility for uncertain captures

## Exact Files In Scope

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
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add minimal typed object model for:
  - `Note`
  - `MemoryFact`
  - `Decision`
  - `Commitment`
  - `WaitingFor`
  - `Blocker`
  - `NextAction`
- Implement capture endpoint that:
  - always writes capture event
  - accepts optional explicit signal (`remember_this`, `task`, `decision`, etc.)
  - creates typed continuity object when explicit/high-confidence
  - records triage posture when ambiguous
- Implement capture inbox UI:
  - submit capture
  - list recent captures with posture
  - view derived object/provenance summary
- Keep provenance visible for all derived objects.

## Out of Scope

- recall query and ranking UX
- deterministic resumption brief generation
- correction queue and supersession flows
- daily/weekly open-loop review dashboard
- connector/channel/platform expansion

## Required Deliverables

- migration + persistence seam for typed continuity backbone
- capture API and conservative admission behavior
- capture inbox UI surface
- unit/integration/web tests for deterministic capture + triage behavior
- synced phase/control docs

## Acceptance Criteria

- capture API always persists an immutable capture event.
- explicit signals deterministically map to correct typed continuity object.
- ambiguous captures are persisted and marked triage instead of creating unsafe durable objects.
- provenance references are present for every derived continuity object.
- `./.venv/bin/python -m pytest tests/unit/test_20260329_0041_phase5_continuity_backbone.py tests/unit/test_continuity_capture.py tests/unit/test_continuity_objects.py tests/integration/test_continuity_capture_api.py -q` passes.
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-capture-form.test.tsx components/continuity-inbox-list.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS (no Phase 4 regression).
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P5-S17 scope.

## Implementation Constraints

- do not introduce new dependencies
- preserve Phase 4 release-control commands and artifacts
- keep admission conservative by default
- keep machine-independent docs/paths

## Control Tower Task Cards

### Task 1: Backbone Schema + Store

Owner: tooling operative

Write scope:

- `apps/api/alembic/versions/20260329_0041_phase5_continuity_backbone.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/continuity_objects.py`
- `tests/unit/test_20260329_0041_phase5_continuity_backbone.py`
- `tests/unit/test_continuity_objects.py`

### Task 2: Capture API + Admission

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_capture.py`
- `tests/unit/test_continuity_capture.py`
- `tests/integration/test_continuity_capture_api.py`

### Task 3: Capture Inbox UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-capture-form.tsx`
- `apps/web/components/continuity-capture-form.test.tsx`
- `apps/web/components/continuity-inbox-list.tsx`
- `apps/web/components/continuity-inbox-list.test.tsx`

### Task 4: Docs + Integration Review

Owner: control tower

Write scope:

- `docs/phase5-product-spec.md`
- `docs/phase5-sprint-17-20-plan.md`
- `docs/phase5-continuity-object-model.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify sprint stayed P5-S17 scoped
- verify no recall/resumption/review-dashboard scope creep
- verify conservative admission posture and provenance guarantees
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact capture/backbone delta
- exact triage/admission behavior
- exact verification command outcomes
- explicit deferred Phase 5 scope (P5-S18/19/20 work)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed in capture/backbone scope
- typed object mapping and triage behavior are deterministic
- provenance is visible and consistent
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when typed continuity backbone + fast capture inbox are shipped with deterministic admission/triage behavior, provenance visibility, and no Phase 4 regression.
