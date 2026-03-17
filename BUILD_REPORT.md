# BUILD_REPORT

## sprint objective

Implement Sprint 6A: replace the placeholder web app with the first real AliceBot operator shell for governed requests, approvals, tasks, task steps, and explain-why review, aligned to `DESIGN_SYSTEM.md` and bounded to existing backend seams only.

## exact screens implemented

- `/`
  - app shell landing view
  - summary metrics
  - primary navigation entry cards
- `/chat`
  - governed request composer
  - recent request/response history
  - trace reference display
- `/approvals`
  - approval inbox list
  - approval detail inspector
- `/tasks`
  - task list
  - selected task summary
  - task-step inspection list
- `/traces`
  - explainability trace list
  - trace detail review panel

## exact shared components implemented

- `app-shell`
- `page-header`
- `section-card`
- `status-badge`
- `empty-state`
- `request-composer`
- `approval-list`
- `task-list`
- `task-step-list`
- `trace-list`

## exact files changed

- `BUILD_REPORT.md`
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

## data-backing by screen

- `/`: fixture/static shell content
- `/chat`: mixed
  - live API when `NEXT_PUBLIC_ALICEBOT_API_BASE_URL` or `ALICEBOT_API_BASE_URL` plus user/thread ids are present
  - explicit local fixtures otherwise
- `/approvals`: mixed
  - live `GET /v0/approvals` when API base URL and user id are present
  - explicit local fixtures otherwise
- `/tasks`: mixed
  - live `GET /v0/tasks` and `GET /v0/tasks/{task_id}/steps` when API base URL and user id are present
  - explicit local fixtures otherwise
- `/traces`: fixture-backed
  - trace summaries and detail events are local fixtures because the repo does not currently expose a general trace-event listing endpoint in the shipped web scope

## commands run

- `npm install` in `apps/web`
- `npm run build` in `apps/web`

## build and test results

- `npm run build` in `apps/web`: PASS
- Production build output included the intended routes:
  - `/`
  - `/chat`
  - `/approvals`
  - `/tasks`
  - `/traces`
- `npm run lint`: not run
  - current project setup prompts interactively for ESLint initialization instead of providing a stable non-interactive check

## visual verification notes

- Desktop behavior:
  - left navigation rail remains persistent
  - top bar and page headers hold a clear hierarchy without crowding
  - approvals, tasks, and traces use split review layouts with bounded inspector panels
- Mobile and narrow-width behavior:
  - sidebar collapses into a horizontal mobile navigation row
  - grids stack to single-column layouts
  - cards, pills, IDs, and attributes use wrapping and containment rules to avoid overflow or clipping
- Screenshots:
  - no browser screenshots captured in this sprint report

## blockers or issues encountered

- Running `npm run build` caused Next.js to rewrite `apps/web/tsconfig.json` and `apps/web/next-env.d.ts` locally; those generated changes were reverted to keep the sprint diff inside the packet’s scoped file list.
- `npm install` generated `apps/web/package-lock.json`; that file was removed from the final diff for the same reason.

## deferred scope after this sprint

- live trace-event listing and deep explainability wiring beyond the current fixture-backed `/traces` screen
- approvals mutation actions from the web UI
- task-step mutations from the web UI
- authentication redesign
- Gmail breadth, Calendar connector UI, runner UI, or any new backend endpoints
