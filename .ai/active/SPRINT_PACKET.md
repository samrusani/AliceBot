# SPRINT_PACKET.md

## Sprint Title

Phase 5 Sprint 18 (P5-S18): Recall and Resumption

## Sprint Type

feature

## Sprint Reason

P5-S17 shipped typed continuity capture/backbone. The next non-redundant dependency is retrieval and deterministic resumption so captured continuity becomes usable without transcript reconstruction.

## Sprint Intent

Ship provenance-backed recall queries and deterministic resumption briefs for thread/task/project/person scope using the continuity object backbone from P5-S17.

## Git Instructions

- Branch Name: `codex/phase5-sprint-18-recall-resumption`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It turns stored continuity into practical product value.
- It is the planned Phase 5 step after capture/backbone.
- It avoids redundant scope by not reopening capture architecture or correction/open-loop dashboards.

## Redundancy Guard

- Already shipped in P5-S17:
  - immutable capture events
  - typed continuity objects
  - conservative admission posture (`DERIVED`/`TRIAGE`)
  - `/continuity` capture inbox
- Required now (P5-S18):
  - recall query surfaces with provenance and confirmation posture
  - deterministic resumption briefs
  - recent-change and open-loop summary sections in resumption output
- Explicitly out of P5-S18:
  - memory correction queue/supersession UX (P5-S19)
  - daily/weekly open-loop dashboard (P5-S20)
  - channel/connector/platform expansion

## Design Truth

- Recall results must be provenance-backed and scoped.
- Resumption briefs must be deterministic for fixed input state.
- Required resumption sections:
  - last decision
  - open loops
  - recent changes
  - next action
- Missing sections must be explicit empty states, not silent omission.

## Exact Surfaces In Scope

- continuity recall API + ranking/filter behavior
- continuity resumption brief API/compiler behavior
- recall/resumption UI in continuity workspace
- tests for deterministic output contracts

## Exact Files In Scope

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-recall-panel.tsx`
- `apps/web/components/continuity-recall-panel.test.tsx`
- `apps/web/components/resumption-brief.tsx`
- `apps/web/components/resumption-brief.test.tsx`
- `tests/unit/test_continuity_recall.py`
- `tests/unit/test_continuity_resumption.py`
- `tests/integration/test_continuity_recall_api.py`
- `tests/integration/test_continuity_resumption_api.py`
- `docs/phase5-product-spec.md`
- `docs/phase5-sprint-17-20-plan.md`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add recall query endpoints with scoped filters:
  - thread
  - task
  - project
  - person
  - time window
- Return recall results with:
  - object type
  - confirmation/posture
  - provenance references
  - relevance/ordering metadata
- Add deterministic resumption brief endpoint(s) for scoped contexts.
- Ensure resumption briefs always include required sections with explicit empty states.
- Add continuity UI panels for:
  - recall query + results
  - resumption brief view

## Out of Scope

- correction/confirm/edit/delete queue work
- contradiction/superseded-chain editing UX
- daily/weekly review dashboard
- connector breadth changes
- broad runtime architecture changes

## Required Deliverables

- recall API + deterministic filter/ranking behavior
- deterministic resumption brief compiler/API
- recall/resumption continuity UI surfaces
- unit/integration/web tests for contract behavior
- synced docs and sprint reports

## Acceptance Criteria

- recall query returns provenance-backed results for scoped filters.
- recall results expose confirmation/posture and deterministic ordering for fixed input state.
- resumption briefs include `last_decision`, `open_loops`, `recent_changes`, `next_action` sections deterministically.
- missing sections are explicit empty states.
- `./.venv/bin/python -m pytest tests/unit/test_continuity_recall.py tests/unit/test_continuity_resumption.py tests/integration/test_continuity_recall_api.py tests/integration/test_continuity_resumption_api.py -q` passes.
- `pnpm --dir apps/web test -- app/continuity/page.test.tsx components/continuity-recall-panel.test.tsx components/resumption-brief.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS (no Phase 4 regression).
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P5-S18 scope.

## Implementation Constraints

- do not introduce new dependencies
- preserve P5-S17 capture/backbone semantics
- keep deterministic output for recall/resumption contracts
- keep docs machine-independent

## Control Tower Task Cards

### Task 1: Recall Backend

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `tests/unit/test_continuity_recall.py`
- `tests/integration/test_continuity_recall_api.py`

### Task 2: Resumption Backend

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `tests/unit/test_continuity_resumption.py`
- `tests/integration/test_continuity_resumption_api.py`

### Task 3: Recall/Resumption UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/continuity/page.tsx`
- `apps/web/app/continuity/page.test.tsx`
- `apps/web/components/continuity-recall-panel.tsx`
- `apps/web/components/continuity-recall-panel.test.tsx`
- `apps/web/components/resumption-brief.tsx`
- `apps/web/components/resumption-brief.test.tsx`

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

- verify no capture-backbone reimplementation
- verify no correction/dashboard scope creep
- verify deterministic recall/resumption behavior
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact recall/resumption delta
- exact deterministic output behavior
- exact verification command outcomes
- explicit deferred Phase 5 scope (P5-S19/P5-S20 work)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P5-S18 scoped
- recall results and resumption briefs are deterministic and provenance-backed
- required resumption sections are always present
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when provenance-backed recall and deterministic resumption are shipped on top of the Phase 5 backbone with no Phase 4 regression.
