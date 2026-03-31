# SPRINT_PACKET.md

## Sprint Title

Phase 7 Sprint 25 (P7-S25): Priority Engine and Chief-of-Staff Dashboard

## Sprint Type

feature

## Sprint Reason

Phase 6 is complete through P6-S24. The next non-redundant seam is Phase 7 vertical productization: turning trusted continuity into an opinionated chief-of-staff layer that tells the user what matters now, why, and what to do next.

## Sprint Intent

Ship the first chief-of-staff product surface from `docs/phase7-chief-of-staff-agent-spec.md` and `docs/phase7-sprint-25-28-plan.md`:

- deterministic priority ranking posture (`urgent`, `important`, `waiting`, `blocked`, `stale`, `defer`)
- provenance-backed ranking rationale
- confidence downgrade behavior when trust/memory quality is weak
- deterministic next-action recommendation

## Git Instructions

- Branch Name: `codex/phase7-sprint-25-priority-engine-dashboard`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the defined Phase 7 kickoff sprint from the approved plan.
- It proves an opinionated chief-of-staff product layer without widening platform scope.
- It directly reuses shipped continuity + trust seams instead of inventing parallel systems.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP qualification/sign-off.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 quality gate, retrieval calibration, correction/freshness hygiene, and trust dashboard/evidence (`P6-S21` to `P6-S24`).
- Required now (P7-S25):
  - chief-of-staff dashboard for current priorities
  - deterministic priority ranking + rationale
  - deterministic recommended next action
  - trust-aware confidence posture in recommendations
- Explicitly out of P7-S25:
  - follow-up drafting/send flows (P7-S26 scope)
  - preparation briefs (P7-S27 scope)
  - weekly outcome-learning loop (P7-S28 scope)
  - connector/channel/auth/orchestration expansion

## Design Truth

- Rankings must be deterministic for fixed input state.
- Priority rationale must be explicit and provenance-backed.
- Low-trust memory posture must reduce confidence rather than silently guessing.
- Chief-of-staff outputs must be artifacts, not vague prose-only chat behavior.

## Exact Surfaces In Scope

- chief-of-staff priority brief/dashboard API seam
- priority posture model and deterministic ranking logic
- next-action recommendation seam
- chief-of-staff dashboard UI surface
- deterministic tests for ranking, rationale, and trust-aware confidence posture

## Exact Files In Scope

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-priority-panel.tsx`
- `apps/web/components/chief-of-staff-priority-panel.test.tsx`
- `apps/web/components/app-shell.tsx`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Introduce deterministic chief-of-staff priority artifact/API payload that includes:
  - ranked items
  - priority posture label (`urgent`, `important`, `waiting`, `blocked`, `stale`, `defer`)
  - provenance-backed rationale fields
  - trust-aware confidence posture
  - recommended next action
- Build ranking logic from shipped inputs:
  - open-loop posture and aging
  - recent continuity changes
  - trust/memory quality posture
  - existing continuity/resumption signals
- Add `/chief-of-staff` UI with:
  - current priority dashboard
  - rationale visibility
  - confidence visibility and low-trust downgrade rendering
- Add deterministic unit/integration/web tests for ranking, rationale, and confidence behavior.

## Out of Scope

- any P7-S26/P7-S27/P7-S28 functionality
- write-capable external actions
- connector/channel expansion
- redesign of P6 quality semantics

## Required Deliverables

- chief-of-staff priority API/artifact seam
- deterministic posture-based ranking implementation
- `/chief-of-staff` dashboard UI
- unit/integration/web tests for deterministic ranking + trust-aware confidence
- synced docs and sprint reports

## Acceptance Criteria

- dashboard answers “what needs attention now” with deterministic ordered priorities.
- each ranked item exposes provenance-backed rationale and posture label.
- low-trust memory posture downgrades recommendation confidence explicitly.
- recommended next action is deterministic for fixed input state.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-priority-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P7-S25 scope and preserve “Phase 6 complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6 semantics
- keep chief-of-staff behavior deterministic and provenance-backed
- keep side effects approval-bounded (no autonomous external writes)

## Control Tower Task Cards

### Task 1: Priority Engine + API

Owner: tooling operative

Write scope:

- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/memory.py`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`

### Task 2: Chief-of-Staff Dashboard UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-priority-panel.tsx`
- `apps/web/components/chief-of-staff-priority-panel.test.tsx`
- `apps/web/components/app-shell.tsx`

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6 relitigation
- verify deterministic ranking and rationale posture behavior
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact chief-of-staff priority contract delta
- exact ranking/rationale/trust-confidence behavior
- exact verification command outcomes
- explicit deferred scope (`P7-S26` to `P7-S28`)

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P7-S25 scoped
- ranking/recommendation logic is deterministic and explainable
- trust-aware confidence downgrade behavior is explicit
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice has a deterministic, provenance-backed chief-of-staff dashboard that reliably answers what matters now and what to do next, with trust-aware confidence posture and no regression to shipped Phase 4/5/6 contracts.
