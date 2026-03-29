# SPRINT_PACKET.md

## Sprint Title

Phase 5 Sprint 19 (P5-S19): Memory Review, Correction, and Freshness

## Sprint Type

feature

## Sprint Reason

P5-S18 shipped deterministic recall/resumption, but trust still depends on explicit correction. The next non-redundant step is a continuity review/correction path that updates retrieval behavior immediately and preserves historical truth.

## Sprint Intent

Ship continuity review queue and correction-event workflows (confirm/edit/delete/supersede/mark_stale) with immediate recall/resumption impact, explicit freshness metadata, and preserved supersession history.

## Git Instructions

- Branch Name: `codex/phase5-sprint-19-memory-review-correction-freshness`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It closes the trust loop: corrections now change future retrieval deterministically.
- It is the planned Phase 5 step after P5-S18 recall/resumption.
- It avoids redundant scope by not reopening capture or recall/resumption implementation.

## Redundancy Guard

- Already shipped in P5-S17:
  - immutable capture events
  - typed continuity objects
  - conservative admission posture (`DERIVED`/`TRIAGE`)
  - `/continuity` capture inbox
- Already shipped in P5-S18:
  - provenance-backed recall (`GET /v0/continuity/recall`)
  - deterministic resumption briefs (`GET /v0/continuity/resumption-brief`)
  - `/continuity` recall/resumption panels
- Required now (P5-S19):
  - review queue for correction-ready continuity objects
  - correction event ledger + lifecycle transitions
  - retrieval/resumption behavior that reflects corrections immediately
  - superseded-chain visibility and freshness posture
- Explicitly out of P5-S19:
  - daily/weekly open-loop dashboard (P5-S20)
  - channel/connector/platform expansion

## Design Truth

- Corrections are append-only events; no silent overwrite of history.
- Corrected objects must affect next recall/resumption output immediately.
- Supersession must preserve chain links (`supersedes`/`superseded_by`) for auditability.
- Freshness posture must be explicit (`last_confirmed_at` and stale status behavior).
- Confirmed/unconfirmed/stale/superseded posture must remain visible in API/UI.

## Exact Surfaces In Scope

- continuity review queue API and correction-action API
- correction event persistence + continuity object lifecycle transitions
- recall/resumption integration for corrected/superseded/stale objects
- continuity workspace review/correction UI
- tests for deterministic correction and supersession behavior

## Exact Files In Scope

- `apps/api/alembic/versions/20260330_0042_phase5_continuity_corrections.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-review-queue.tsx`
- `apps/web/components/continuity-review-queue.test.tsx`
- `apps/web/components/continuity-correction-form.tsx`
- `apps/web/components/continuity-correction-form.test.tsx`
- `tests/unit/test_20260330_0042_phase5_continuity_corrections.py`
- `tests/unit/test_continuity_review.py`
- `tests/integration/test_continuity_review_api.py`
- `tests/unit/test_continuity_recall.py`
- `tests/unit/test_continuity_resumption.py`
- `docs/phase5-product-spec.md`
- `docs/phase5-sprint-17-20-plan.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add correction-event model and persistence for:
  - confirm
  - edit
  - delete
  - supersede
  - mark_stale
- Add review queue endpoint for correction-ready continuity objects.
- Add correction action endpoint(s) on continuity objects.
- Add object-lifecycle fields required for correction/freshness semantics.
- Ensure recall/resumption treat superseded/deleted/stale posture deterministically.
- Add continuity UI surfaces for:
  - review queue list/filter
  - correction action submit/feedback
  - superseded-chain visibility on reviewed object detail

## Out of Scope

- daily/weekly open-loop dashboard and briefing generation
- broad cross-connector memory normalization
- broad `/memories` redesign outside continuity workspace
- connector breadth changes
- broad runtime architecture changes

## Required Deliverables

- continuity correction event schema + store contracts
- continuity review queue + correction action APIs
- recall/resumption correction-awareness updates
- continuity review/correction UI surfaces
- unit/integration/web tests for deterministic correction/supersession behavior
- synced docs and sprint reports

## Acceptance Criteria

- correction actions append correction events before lifecycle state mutation.
- confirm/edit/delete/supersede/mark_stale actions are deterministic for fixed input state.
- recall and resumption reflect corrections immediately after action commit.
- superseded chain is queryable and visible in continuity review detail.
- freshness posture is explicit in API responses (`last_confirmed_at`, status transitions).
- `./.venv/bin/python -m pytest tests/unit/test_20260330_0042_phase5_continuity_corrections.py tests/unit/test_continuity_review.py tests/integration/test_continuity_review_api.py tests/unit/test_continuity_recall.py tests/unit/test_continuity_resumption.py -q` passes.
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-review-queue.test.tsx components/continuity-correction-form.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS (no Phase 4 regression).
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P5-S19 scope.

## Implementation Constraints

- do not introduce new dependencies
- preserve P5-S17 capture/backbone semantics
- preserve P5-S18 recall/resumption contracts
- keep correction events append-only and machine-auditable
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Schema + Store Corrections

Owner: tooling operative

Write scope:

- `apps/api/alembic/versions/20260330_0042_phase5_continuity_corrections.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/unit/test_20260330_0042_phase5_continuity_corrections.py`

### Task 2: Review + Correction API

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `tests/unit/test_continuity_review.py`
- `tests/integration/test_continuity_review_api.py`
- `tests/unit/test_continuity_recall.py`
- `tests/unit/test_continuity_resumption.py`

### Task 3: Continuity Review UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-review-queue.tsx`
- `apps/web/components/continuity-review-queue.test.tsx`
- `apps/web/components/continuity-correction-form.tsx`
- `apps/web/components/continuity-correction-form.test.tsx`

### Task 4: Docs + Integration Review

Owner: control tower

Write scope:

- `docs/phase5-product-spec.md`
- `docs/phase5-sprint-17-20-plan.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no capture or recall/resumption reimplementation
- verify no P5-S20 dashboard scope creep
- verify deterministic correction behavior and supersession chain visibility
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact correction/freshness delta
- exact correction-event and lifecycle transition behavior
- exact verification command outcomes
- explicit deferred Phase 5 scope (P5-S20 work)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P5-S19 scoped
- correction events are append-only and audit-safe
- recall/resumption behavior reflects correction/supersession immediately
- superseded/freshness posture is visible and deterministic
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when continuity review and correction flows (confirm/edit/delete/supersede/mark_stale) are shipped with immediate recall/resumption impact, explicit freshness/supersession posture, and no Phase 4 regression.
