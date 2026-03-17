# SPRINT_PACKET.md

## Sprint Title

Sprint 6A: MVP Web Shell and Core Operator Views

## Sprint Type

ui

## Sprint Reason

Sprint 5U is implemented and the project is on track, but the largest remaining MVP gap is no longer Gmail auth hardening. The backend now has enough governed capability to support a real human-usable shell, and `DESIGN_SYSTEM.md` exists as a design truth source. To avoid looping on narrow connector internals while the product remains invisible, the next sprint should open the thinnest serious web surface for the shipped backend seams.

## Sprint Intent

Build the first real web shell for AliceBot on top of the existing backend by adding a calm, high-trust operator interface for navigation, request submission, approvals review, task and task-step inspection, and explain-why/traces viewing, without expanding backend product scope.

## Git Instructions

- Branch Name: `codex/sprint-6a-mvp-web-shell`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- The accepted repo state through Sprint 5T already ships the core backend substrate:
  - governed context compilation
  - approvals and execution review
  - tasks and task steps
  - explainable traces
  - rooted workspaces, artifacts, document ingestion, and Gmail-backed artifacts
- `DESIGN_SYSTEM.md` now exists and should be treated as a source of truth alongside `ARCHITECTURE.md`.
- The product brief requires web-based chat and task orchestration, plus explain-why visibility.
- Continuing with another Gmail-only sprint right now would optimize one backend seam while the MVP still lacks a usable interface.
- The narrowest safe UI slice is the shell plus core operator views only, not full workflow completion or new backend scope.

## Design Truth

- `DESIGN_SYSTEM.md` is in force for this sprint.
- The UI must follow its calm, premium, restrained visual language.
- This sprint must preserve strong hierarchy, readable density, stable navigation, and explicit containment rules.
- Do not introduce playful AI styling, loud gradients, decorative clutter, or unstable layout behavior.

## Exact Screens In Scope

- `/`
  - app shell landing view
  - primary navigation
  - summary cards for the existing backend seams
- `/chat`
  - request composer surface
  - recent request/response panel
  - explicit “governed request” framing, not a consumer chat skin
- `/approvals`
  - approval inbox list
  - approval detail panel or inline inspector
- `/tasks`
  - task list
  - task detail panel
  - task-step list/inspection area
- `/traces`
  - trace or explain-why review view for context compile and governed actions

## Exact Components In Scope

- app shell frame
  - top bar
  - left navigation rail or sidebar
  - main content container
- shared primitives
  - page header
  - section card
  - metric card
  - status badge
  - empty state
  - list row
  - split-panel or inspector layout
- domain views
  - request composer
  - approval list
  - approval detail inspector
  - task list
  - task detail summary
  - task-step timeline or ordered list
  - trace event list
  - explainability summary panel

## Exact Files In Scope

- `DESIGN_SYSTEM.md`
  - reference only; do not rewrite unless the sprint reveals a concrete contradiction that must be corrected
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/chat/page.tsx`
- `apps/web/app/approvals/page.tsx`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/traces/page.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/app-shell.tsx`
- `apps/web/components/page-header.tsx`
- `apps/web/components/section-card.tsx`
- `apps/web/components/status-badge.tsx`
- `apps/web/components/empty-state.tsx`
- `apps/web/components/request-composer.tsx`
- `apps/web/components/approval-list.tsx`
- `apps/web/components/task-list.tsx`
- `apps/web/components/task-step-list.tsx`
- `apps/web/components/trace-list.tsx`
- `apps/web/package.json`

## In Scope

- Replace the current placeholder Next.js landing page with a real app shell aligned to `DESIGN_SYSTEM.md`.
- Add the exact screens and components listed above.
- Use only existing backend concepts already shipped in the repo:
  - context compilation
  - approvals
  - tasks and task steps
  - traces or explain-why data
- Implement a thin frontend data layer only as needed to render those views.
- If live API wiring is used, it must consume existing endpoints only.
- If mocked or fixture-backed UI data is used for part of the shell, keep the mock layer explicit and local to the web app.
- Ensure the shell is usable on desktop and mobile widths.

## Out of Scope

- No new backend endpoints.
- No backend schema changes.
- No Gmail search or broader connector work.
- No Calendar connector UI.
- No write-capable action UI beyond the existing governed-request framing.
- No authentication/product auth redesign.
- No full end-to-end magnesium reorder workflow yet.
- No design-system rewrite.
- No runner-style orchestration UI.

## Required Deliverables

- A real Next.js app shell aligned to `DESIGN_SYSTEM.md`.
- The exact screens listed in this packet, implemented in the exact in-scope file set or a narrower subset of it.
- Stable layout, navigation, responsive behavior, and readable empty states.
- A thin request submission surface for the governed request path.
- Approval, task, task-step, and trace/explain-why review views.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- The web app no longer renders only the current placeholder foundation card at `/`.
- The app exposes the exact in-scope screens:
  - `/`
  - `/chat`
  - `/approvals`
  - `/tasks`
  - `/traces`
- The UI visibly follows `DESIGN_SYSTEM.md` and feels calm, premium, and high-trust rather than demo-like.
- Text remains contained within cards and panels across responsive breakpoints.
- Navigation is stable and the current location is obvious.
- The UI uses only existing backend concepts and does not widen product scope.
- `pnpm build` or `npm run build` for `apps/web` passes.
- Any added frontend tests or lint checks pass if introduced.

## Implementation Constraints

- Keep the sprint narrow and boring.
- Treat this as the first operator shell, not the finished product.
- Prefer a few strong views over too many half-finished surfaces.
- Reuse existing backend seams; do not invent placeholder product capabilities that the backend does not support.
- Keep interaction restrained and calm.
- Preserve mobile usability and text containment.
- If any API wiring is unstable, degrade to explicit empty, loading, or fixture-backed states instead of inventing hidden backend changes.

## Suggested Work Breakdown

1. Replace the placeholder root page with a real shell and shared layout primitives.
2. Add the in-scope routes and core shared components.
3. Implement the request, approvals, tasks, and traces views using existing backend concepts only.
4. Apply responsive layout and empty-state handling.
5. Run frontend build and any introduced checks.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact screens and components implemented
- the exact files changed
- whether each screen is live-API-backed, fixture-backed, or mixed
- exact commands run
- build and test results
- screenshots or concise visual verification notes for desktop and mobile behavior
- what remains intentionally deferred after this UI sprint

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed a UI sprint and did not widen backend product scope
- `DESIGN_SYSTEM.md` was followed materially
- the exact in-scope screens, components, and files were respected
- layout quality, text containment, hierarchy, and responsive behavior are acceptable
- no hidden Gmail breadth, Calendar, runner, or auth-scope expansion entered the sprint

## Exit Condition

This sprint is complete when AliceBot has a real web shell with stable navigation plus the first operator-facing views for requests, approvals, tasks, task steps, and traces, aligned to `DESIGN_SYSTEM.md`, built on existing backend concepts only, and verified by frontend build checks.
