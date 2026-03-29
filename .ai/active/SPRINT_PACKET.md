# SPRINT_PACKET.md

## Sprint Title

Phase 5 Sprint 20 (P5-S20): Open Loops and Daily Review

## Sprint Type

feature

## Sprint Reason

P5-S19 shipped review/correction/freshness, but continuity still needs a deterministic executive-function surface. The next non-redundant step is open-loop review and deterministic daily/weekly briefing built on shipped continuity and correction contracts.

## Sprint Intent

Ship continuity open-loop dashboard plus deterministic daily/weekly review briefs with review actions (`done`, `deferred`, `still_blocked`) that immediately update resumption behavior.

## Git Instructions

- Branch Name: `codex/phase5-sprint-20-open-loops-daily-review`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It turns continuity into daily execution support, not just memory correctness.
- It is the planned final Phase 5 step after P5-S19 correction/freshness.
- It avoids redundant scope by not reopening capture, recall/resumption, or correction architecture.

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
- Already shipped in P5-S19:
  - continuity review queue (`GET /v0/continuity/review-queue`)
  - review detail + correction actions
  - append-only correction event ledger
  - immediate correction impact on recall/resumption
- Required now (P5-S20):
  - open-loop dashboard for waiting-for/blocker/stale/next-action posture
  - deterministic daily brief and weekly review endpoints
  - review-action workflow (`done`, `deferred`, `still_blocked`)
  - immediate resumption refresh after review actions
- Explicitly out of P5-S20:
  - connector/channel/platform expansion
  - new memory backbone or recall ranking redesign

## Design Truth

- Daily/weekly briefs must be deterministic for fixed input state.
- Open-loop posture must be explicit and auditable:
  - waiting_for
  - blocker
  - stale
  - next_action
- Review actions must map to deterministic lifecycle transitions.
- Resumption must reflect review actions immediately.
- Empty brief sections must be explicit empty states.

## Exact Surfaces In Scope

- continuity open-loop dashboard API
- deterministic daily brief API
- deterministic weekly review API
- review-action mutation API for open loops
- continuity workspace open-loop/brief UI
- tests for deterministic brief composition and action transitions

## Exact Files In Scope

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-open-loops-panel.tsx`
- `apps/web/components/continuity-open-loops-panel.test.tsx`
- `apps/web/components/continuity-daily-brief.tsx`
- `apps/web/components/continuity-daily-brief.test.tsx`
- `apps/web/components/continuity-weekly-review.tsx`
- `apps/web/components/continuity-weekly-review.test.tsx`
- `tests/unit/test_continuity_open_loops.py`
- `tests/integration/test_continuity_open_loops_api.py`
- `tests/integration/test_continuity_daily_weekly_review_api.py`
- `tests/unit/test_continuity_review.py`
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

- Add open-loop dashboard endpoint with deterministic grouping and ordering.
- Add daily brief endpoint that composes:
  - waiting_for highlights
  - blocker highlights
  - stale items
  - one next suggested action
- Add weekly review endpoint with deterministic rollup for open-loop posture.
- Add review-action endpoint for open-loop workflow:
  - done
  - deferred
  - still_blocked
- Ensure review actions update continuity resumption output immediately.
- Add continuity UI surfaces for:
  - open-loop dashboard list/group review
  - daily brief panel
  - weekly review panel
  - review-action controls with explicit outcome feedback

## Out of Scope

- reimplementation of P5-S17 capture backbone
- reimplementation of P5-S18 recall/resumption ranking contracts
- reimplementation of P5-S19 correction-event architecture
- broad `/memories` or `/tasks` redesign outside continuity workspace
- connector breadth changes
- broad runtime architecture changes

## Required Deliverables

- continuity open-loop dashboard API + deterministic ordering behavior
- deterministic daily brief and weekly review APIs
- open-loop review-action mutation API
- continuity open-loop/daily/weekly UI surfaces
- unit/integration/web tests for deterministic brief/action behavior
- synced docs and sprint reports

## Acceptance Criteria

- open-loop dashboard returns deterministic grouped ordering for waiting_for/blocker/stale/next_action posture.
- daily brief and weekly review endpoints are deterministic for fixed input state and emit explicit empty states when sections are empty.
- `done`/`deferred`/`still_blocked` actions are deterministic and auditable.
- continuity resumption reflects review-action outcomes immediately.
- `./.venv/bin/python -m pytest tests/unit/test_continuity_open_loops.py tests/integration/test_continuity_open_loops_api.py tests/integration/test_continuity_daily_weekly_review_api.py tests/unit/test_continuity_review.py tests/unit/test_continuity_resumption.py -q` passes.
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-open-loops-panel.test.tsx components/continuity-daily-brief.test.tsx components/continuity-weekly-review.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS (no Phase 4 regression).
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P5-S20 scope.

## Implementation Constraints

- do not introduce new dependencies
- preserve P5-S17 capture/backbone semantics
- preserve P5-S18 recall/resumption contracts
- preserve P5-S19 correction-event semantics
- keep brief composition deterministic and machine-auditable
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Open-Loop Backend

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `tests/unit/test_continuity_open_loops.py`
- `tests/integration/test_continuity_open_loops_api.py`

### Task 2: Daily/Weekly Brief + Actions API

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/memory.py`
- `tests/integration/test_continuity_daily_weekly_review_api.py`
- `tests/unit/test_continuity_review.py`
- `tests/unit/test_continuity_resumption.py`

### Task 3: Open-Loop/Daily/Weekly UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-open-loops-panel.tsx`
- `apps/web/components/continuity-open-loops-panel.test.tsx`
- `apps/web/components/continuity-daily-brief.tsx`
- `apps/web/components/continuity-daily-brief.test.tsx`
- `apps/web/components/continuity-weekly-review.tsx`
- `apps/web/components/continuity-weekly-review.test.tsx`

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

- verify no capture/recall/correction reimplementation
- verify no connector breadth or orchestration scope creep
- verify deterministic brief composition and review-action transitions
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact open-loop/daily/weekly delta
- exact brief composition and review-action behavior
- exact verification command outcomes
- explicit post-Phase-5 deferred scope (if any)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P5-S20 scoped
- open-loop dashboard and daily/weekly briefs are deterministic
- review actions map to deterministic lifecycle outcomes
- resumption reflects review-action updates immediately
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when continuity open-loop dashboard plus deterministic daily/weekly review flows are shipped with deterministic review-action outcomes and no Phase 4 regression.
