# SPRINT_PACKET.md

## Sprint Title

Phase 8 Sprint 32 (P8-S32): Outcome Learning and Closure Quality

## Sprint Type

feature

## Sprint Reason

P8-S31 shipped deterministic governed execution routing on top of P8-S29/P8-S30. The next non-redundant seam is closing the Phase 8 loop by capturing handoff outcomes, exposing closure quality signals, and feeding deterministic learning signals back into chief-of-staff supervision.

Planning anchors:

- `docs/phase8-product-spec.md`
- `docs/phase8-sprint-29-32-plan.md`

## Sprint Intent

Ship deterministic outcome-learning seams on top of shipped P8-S29/P8-S30/P8-S31:

- explicit handoff outcome capture/status semantics
- closure quality and conversion signal summaries
- stale/ignored escalation posture visibility
- `/chief-of-staff` outcome-learning and closure panel

## Git Instructions

- Branch Name: `codex/phase8-sprint-32-outcome-learning-closure-quality`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the planned final Phase 8 seam after shipped routing capability.
- It turns routed handoffs into measurable closure outcomes.
- It completes recommendation-to-handoff-to-routing-to-learning feedback without widening autonomy.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP sign-off seams.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 trust calibration (`P6-S21` through `P6-S24`), complete as of March 31, 2026.
  - Phase 7 chief-of-staff layer complete (`P7-S25` through `P7-S28`).
  - Phase 8 Sprint 29 (`P8-S29`) action handoff artifacts and explicit non-autonomous posture.
  - Phase 8 Sprint 30 (`P8-S30`) handoff queue lifecycle and operator review transitions.
  - Phase 8 Sprint 31 (`P8-S31`) governed execution routing transitions and readiness posture.
- Required now (P8-S32):
  - deterministic handoff outcome capture semantics
  - closure quality summary and recommendation-to-execution conversion signals
  - explicit stale/ignored escalation posture and feedback visibility
- Explicitly out of P8-S32:
  - autonomous execution or external connector side effects
  - redesign of P8-S29 handoff generation semantics
  - redesign of P8-S30 queue/review lifecycle semantics
  - redesign of P8-S31 routing semantics
  - connector/channel/auth/orchestration expansion

## Design Truth

- Outcome learning must be deterministic for fixed state.
- Outcome capture must be explicit and auditable.
- Closure quality signals must be visible and explainable.
- Execution posture remains approval-bounded and non-autonomous.

## Exact Surfaces In Scope

- chief-of-staff handoff outcome-learning artifact/API seam
- closure quality and conversion summary seam
- stale/ignored escalation signal seam
- `/chief-of-staff` outcome-learning panel
- deterministic tests for outcome capture and learning rollups

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
- `apps/web/components/chief-of-staff-execution-routing-panel.tsx`
- `apps/web/components/chief-of-staff-execution-routing-panel.test.tsx`
- `apps/web/components/chief-of-staff-outcome-learning-panel.tsx`
- `apps/web/components/chief-of-staff-outcome-learning-panel.test.tsx`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic outcome-learning fields on chief-of-staff payloads:
  - `handoff_outcome_summary`
  - `handoff_outcomes`
  - `closure_quality_summary`
  - `conversion_signal_summary`
  - `stale_ignored_escalation_posture`
- Add explicit outcome-capture seam for routed handoff items:
  - statuses: `reviewed`, `approved`, `rejected`, `rewritten`, `executed`, `ignored`, `expired`
  - deterministic capture ordering and latest-state derivation
  - immutable outcome capture records
- Add deterministic closure-learning behavior:
  - recommendation-to-execution conversion signals
  - stale/ignored escalation rollups
  - explicit explanation payload for how outcome history affects guidance posture
- Add `/chief-of-staff` outcome-learning panel with outcome capture controls and closure metrics visibility.
- Add deterministic tests for outcome capture/status rollups and closure-learning summary behavior.

## Out of Scope

- automatic execution based on outcomes
- connector/channel expansion
- changes to shipped P8-S29 generation semantics
- changes to shipped P8-S30 queue/review semantics
- changes to shipped P8-S31 routing semantics

## Required Deliverables

- outcome-learning API/artifact seam
- deterministic outcome capture and closure rollup behavior
- stale/ignored escalation posture visibility
- `/chief-of-staff` outcome-learning UI panel
- unit/integration/web tests for outcome-learning behavior
- synced docs and sprint reports

## Acceptance Criteria

- routed handoff outcomes are captured with deterministic, explicit status semantics.
- closure quality and conversion signals are deterministic, auditable, and explainable.
- stale/ignored escalation posture is explicit and visible.
- approval-bounded non-autonomous posture remains preserved.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-execution-routing-panel.test.tsx components/chief-of-staff-outcome-learning-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P8-S32 scope and preserve “P8-S29/P8-S30/P8-S31 shipped” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6/P7 semantics
- preserve shipped P8-S29 handoff-generation semantics
- preserve shipped P8-S30 queue/review semantics
- preserve shipped P8-S31 routing semantics
- keep side effects approval-bounded and explicit
- keep outcome-learning behavior deterministic and test-backed

## Control Tower Task Cards

### Task 1: Outcome Learning Engine + API

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

### Task 2: Chief-of-Staff Outcome UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-execution-routing-panel.tsx`
- `apps/web/components/chief-of-staff-execution-routing-panel.test.tsx`
- `apps/web/components/chief-of-staff-outcome-learning-panel.tsx`
- `apps/web/components/chief-of-staff-outcome-learning-panel.test.tsx`

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6/P7/P8-S29/P8-S30/P8-S31 relitigation
- verify deterministic outcome capture and closure-learning semantics
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact outcome-learning contract delta
- exact deterministic outcome/closure summary behavior
- exact verification command outcomes
- explicit deferred Phase 8 follow-up scope after P8-S32

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P8-S32 scoped
- outcome-learning outputs are deterministic and explainable
- approval-bounded execution posture is explicit and preserved
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice can deterministically capture handoff outcomes and present closure-quality learning signals that feed back into chief-of-staff supervision, without regressing shipped Phase 4/5/6/7 and P8-S29/P8-S30/P8-S31 behavior.
