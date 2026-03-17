# SPRINT_PACKET.md

## Sprint Title

Sprint 6B: Governed Request Submission and Actionable Approval Workflow

## Sprint Type

ui

## Sprint Reason

Sprint 6A delivered the first real AliceBot web shell, but it is still mostly a review surface. The highest-value next MVP gap is not another Gmail or docs sprint; it is turning the shell into a usable governed workflow surface. The backend already ships approval request creation, approval resolution, and task/task-step reads, so the next safe step is to wire those existing seams into the web UI without expanding backend scope.

## Sprint Intent

Extend the web shell so the operator can submit governed requests, review live approval details, approve or reject them from the UI, and inspect the resulting task/task-step state, using existing backend endpoints only.

## Git Instructions

- Branch Name: `codex/sprint-6b-governed-request-approval-ui`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 6A proved the web shell can render a calm, high-trust operator interface aligned to `DESIGN_SYSTEM.md`.
- The current shell still leaves the key governed workflow mostly inert:
  - requests are not yet clearly submitted through the approval-request seam
  - approvals are inspectable but not actionable from the UI
  - tasks can be viewed but not as the immediate downstream result of a governed request
- The product brief requires web-based chat and task orchestration with explicit approval for consequential actions.
- The narrowest safe next step is to wire the existing approval and task seams into the shell, not to invent new backend features.

## Design Truth

- `DESIGN_SYSTEM.md` remains in force for this sprint.
- The UI must keep the calm, premium, restrained operator feel established in Sprint 6A.
- Interaction states must feel stable and explicit:
  - pending
  - submitting
  - approved
  - rejected
  - loading
  - empty
- Avoid noisy notification patterns or consumer-chat styling.

## Exact Screens In Scope

- `/chat`
  - governed request composer
  - request mode focused on the shipped approval-request seam
  - resulting request summary state
- `/approvals`
  - live approval inbox list
  - approval detail inspector
  - approve action
  - reject action
- `/tasks`
  - live task list
  - selected task summary
  - live task-step inspection
  - visible linkage from approval outcome to task state when available

## Exact Components In Scope

- existing shared shell primitives from Sprint 6A, refined as needed
- governed request form
- approval detail inspector
- approval action bar
- task summary panel
- task-step status list
- inline success/error state messaging for approval actions
- empty/loading state variants for live workflow screens

## Exact Files In Scope

- `DESIGN_SYSTEM.md`
  - reference only; do not rewrite unless the sprint reveals a concrete contradiction that must be corrected
- `apps/web/app/chat/page.tsx`
- `apps/web/app/approvals/page.tsx`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/request-composer.tsx`
- `apps/web/components/approval-list.tsx`
- `apps/web/components/task-list.tsx`
- `apps/web/components/task-step-list.tsx`
- `apps/web/components/section-card.tsx`
- `apps/web/components/status-badge.tsx`
- `apps/web/components/empty-state.tsx`
- `apps/web/components/approval-actions.tsx`
- `apps/web/components/approval-detail.tsx`
- `apps/web/components/task-summary.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/fixtures.ts`
- `apps/web/package.json`

## In Scope

- Wire `/chat` to the existing governed request path using shipped backend behavior only.
- Support governed request submission through existing endpoints such as:
  - `POST /v0/approvals/requests`
- Support live approval review using existing endpoints such as:
  - `GET /v0/approvals`
  - `GET /v0/approvals/{approval_id}` if already available through the current web layer pattern
  - `POST /v0/approvals/{approval_id}/approve`
  - `POST /v0/approvals/{approval_id}/reject`
- Support live task and task-step review using existing endpoints such as:
  - `GET /v0/tasks`
  - `GET /v0/tasks/{task_id}`
  - `GET /v0/tasks/{task_id}/steps`
- Keep fixture-backed fallback behavior explicit when API configuration is absent.
- Keep all workflow state user-scoped and visibly deterministic.

## Out of Scope

- No new backend endpoints.
- No backend schema changes.
- No approval execution from the web UI yet.
- No task-step mutations from the web UI beyond review.
- No general trace-event listing backend work.
- No Gmail breadth, Calendar UI, or connector expansion.
- No auth redesign.
- No full magnesium reorder workflow yet.
- No runner-style orchestration UI.

## Required Deliverables

- A governed request submission surface in `/chat`.
- Actionable approve and reject controls in `/approvals`.
- Live task and task-step inspection that reflects governed-request outcomes in `/tasks`.
- Stable loading, empty, success, and failure states for those workflow surfaces.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- `/chat` can submit a governed request through an existing shipped backend path when API configuration is present.
- `/approvals` can approve and reject approvals through existing shipped backend endpoints when API configuration is present.
- `/tasks` reflects live task/task-step state from existing shipped endpoints when API configuration is present.
- When API configuration is absent, the UI falls back to explicit fixture-backed or empty states instead of broken behavior.
- The sprint stays within the exact in-scope screens, components, and files listed above.
- The UI continues to follow `DESIGN_SYSTEM.md` materially.
- `npm run build` in `apps/web` passes.
- Any added checks pass if introduced.

## Implementation Constraints

- Keep the sprint narrow and boring.
- Reuse existing backend seams only; do not hide backend feature requests inside the UI sprint.
- Keep the governed-request flow explicit and reviewable, not magical.
- Preserve the visual calm and text containment established in Sprint 6A.
- If an endpoint or payload is not stable enough for live use, degrade cleanly to an explicit unavailable state rather than inventing new backend logic.

## Suggested Work Breakdown

1. Refactor the current shell data layer into a clearer shared API helper plus fixtures.
2. Wire governed request submission into `/chat`.
3. Add approval detail plus approve/reject actions in `/approvals`.
4. Strengthen `/tasks` to show the downstream task/task-step state from the governed workflow.
5. Add deterministic loading, success, error, and empty states.
6. Run frontend build and any introduced checks.
7. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact screens and components implemented or updated
- the exact files changed
- which routes are live-API-backed, fixture-backed, or mixed
- the exact shipped backend endpoints consumed by the UI
- exact commands run
- build and test results
- concise desktop and mobile visual verification notes
- what remains intentionally deferred after this sprint

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed a UI sprint and did not widen backend product scope
- the governed request, approval, and task workflow uses only existing shipped backend seams
- `DESIGN_SYSTEM.md` was followed materially
- loading, empty, success, and error states are stable and readable
- no hidden Gmail breadth, Calendar, runner, auth-scope, or backend-scope expansion entered the sprint

## Exit Condition

This sprint is complete when the AliceBot web shell can submit governed requests, resolve approvals through approve/reject UI actions, and reflect resulting task/task-step state through the existing backend seams, while staying within the current UI and backend boundaries.
