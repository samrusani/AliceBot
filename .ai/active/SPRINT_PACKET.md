# SPRINT_PACKET.md

## Sprint Title

Phase 8 Sprint 29 (P8-S29): Chief-of-Staff Action Handoff Artifacts

## Sprint Type

feature

## Sprint Reason

Phase 7 is complete through P7-S28. The next non-redundant seam is translating chief-of-staff guidance into deterministic, approval-bounded action handoff artifacts that can be executed through existing governed workflows.

Planning anchors:

- `docs/phase8-product-spec.md`
- `docs/phase8-sprint-29-32-plan.md`

## Sprint Intent

Ship deterministic action-handoff seams on top of shipped chief-of-staff outputs:

- action handoff artifact from priority/follow-through/preparation/weekly-review outputs
- approval-bounded execution posture metadata
- deterministic mapping into task/approval-ready draft structures (artifact-only, no autonomous execution)
- `/chief-of-staff` handoff panel visibility

## Git Instructions

- Branch Name: `codex/phase8-sprint-29-action-handoff-artifacts`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It starts Phase 8 with a clear product step after Phase 7 completion.
- It reuses shipped chief-of-staff intelligence instead of reopening ranking/learning semantics.
- It converts recommendations into operationally usable, governable action artifacts.

## Redundancy Guard

- Already shipped baseline:
  - Phase 4 release-control and MVP sign-off seams.
  - Phase 5 continuity capture/recall/review/open-loop seams.
  - Phase 6 trust calibration (`P6-S21` through `P6-S24`), complete as of March 31, 2026.
  - Phase 7 chief-of-staff layer complete (`P7-S25` through `P7-S28`).
- Required now (P8-S29):
  - deterministic recommendation-to-action handoff artifacts
  - explicit approval-bounded execution posture
  - visible and auditable handoff rationale/provenance
- Explicitly out of P8-S29:
  - autonomous external side effects
  - connector/channel/auth/orchestration expansion
  - redesign of Phase 7 ranking/follow-through/preparation/learning semantics

## Design Truth

- Handoff artifacts must be deterministic for fixed state.
- Handoff artifacts must remain guidance/execution-prep only, not direct side effects.
- Trust posture and confidence must remain explicit in handoff outputs.
- Every handoff recommendation must remain provenance-backed.

## Exact Surfaces In Scope

- chief-of-staff action-handoff artifact/API seam
- deterministic mapping to task/approval-ready draft structures
- `/chief-of-staff` action handoff panel
- deterministic tests for handoff mapping and approval-bounded posture

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
- `apps/web/components/chief-of-staff-weekly-review-panel.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.test.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.test.tsx`
- `tests/unit/test_chief_of_staff.py`
- `tests/integration/test_chief_of_staff_api.py`
- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `.ai/active/SPRINT_PACKET.md`

## In Scope

- Add deterministic action-handoff artifact/API fields:
  - `action_handoff_brief`
  - `handoff_items`
  - `task_draft`
  - `approval_draft`
  - `execution_posture`
- Add deterministic action handoff generation:
  - selects top actionable chief-of-staff recommendations
  - maps each item to task/approval draft structure with explicit rationale
  - carries trust-aware confidence and required-approval indicators
- Add `/chief-of-staff` action handoff panel with rationale/provenance visibility.
- Add deterministic tests for mapping order, execution posture, and no-autonomous-execution guarantees.

## Out of Scope

- automatic task execution or external sends
- connector/channel expansion
- changes to shipped P7 semantics

## Required Deliverables

- action-handoff API/artifact seam
- deterministic task/approval draft mapping behavior
- `/chief-of-staff` action handoff UI panel
- unit/integration/web tests for handoff behavior
- synced docs and sprint reports

## Acceptance Criteria

- action handoff outputs are deterministic and provenance-backed for fixed state.
- handoff payloads include explicit approval-bounded execution posture and non-autonomous guarantees.
- task/approval draft structures are coherent and directly usable by existing governed workflows.
- `./.venv/bin/python -m pytest tests/unit/test_chief_of_staff.py tests/integration/test_chief_of_staff_api.py -q` passes.
- `pnpm --dir apps/web test -- app/chief-of-staff/page.test.tsx components/chief-of-staff-weekly-review-panel.test.tsx components/chief-of-staff-action-handoff-panel.test.tsx lib/api.test.ts` passes.
- `python3 scripts/run_phase4_validation_matrix.py` remains PASS.
- `README.md`, `ROADMAP.md`, and `.ai/handoff/CURRENT_STATE.md` reflect active P8-S29 scope and preserve “Phase 7 complete” truth.

## Implementation Constraints

- do not introduce new dependencies
- preserve shipped P5/P6/P7 semantics
- keep side effects approval-bounded and explicit
- keep handoff behavior deterministic and test-backed

## Control Tower Task Cards

### Task 1: Handoff Engine + API

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

### Task 2: Chief-of-Staff Handoff UI

Owner: tooling operative

Write scope:

- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chief-of-staff/page.tsx`
- `apps/web/app/chief-of-staff/page.test.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.tsx`
- `apps/web/components/chief-of-staff-weekly-review-panel.test.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.tsx`
- `apps/web/components/chief-of-staff-action-handoff-panel.test.tsx`

### Task 3: Docs + Integration Review

Owner: control tower

Write scope:

- `README.md`
- `ROADMAP.md`
- `.ai/handoff/CURRENT_STATE.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Responsibilities:

- verify no P6/P7 relitigation
- verify deterministic handoff mapping and approval-bounded posture
- verify no hidden scope expansion
- verify no Phase 4 regression

## Build Report Requirements

`BUILD_REPORT.md` must include:

- exact action-handoff contract delta
- exact deterministic mapping/execution-posture behavior
- exact verification command outcomes
- explicit deferred Phase 8 scope beyond P8-S29

## Review Focus

`REVIEW_REPORT.md` should verify:

- sprint stayed P8-S29 scoped
- handoff outputs are deterministic and explainable
- approval-bounded execution posture is explicit and preserved
- no hidden scope expansion
- Phase 4 validation remains green

## Exit Condition

This sprint is complete when Alice can produce deterministic, provenance-backed, approval-bounded action handoff artifacts from chief-of-staff recommendations without regressing shipped Phase 4/5/6/7 behavior.
