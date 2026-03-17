# BUILD_REPORT

## sprint objective

Implement Sprint 6B: turn the web shell into a governed workflow surface that can submit approval requests, resolve approvals from the UI, and inspect downstream task and task-step state using existing shipped backend seams only.

## completed work

- `/chat`
  - replaced the old response-oriented composer with governed approval-request submission
  - added explicit request fields for `thread_id`, `tool_id`, `action`, `scope`, optional hints, and JSON attributes
  - added resulting request summary cards with decision, approval linkage, task linkage, and trace references
- `/approvals`
  - kept the live inbox list
  - added a dedicated approval detail inspector component
  - added actionable approve and reject controls backed by existing resolution endpoints
  - added an explicit route-level `loading.tsx` boundary for slow live reads
  - added inline action-state messaging for ready, submitting, success, and failure states
- `/tasks`
  - kept the live task list
  - added a dedicated task summary panel
  - added live task detail reads through `GET /v0/tasks/{task_id}`
  - added an explicit route-level `loading.tsx` boundary for slow live reads
  - strengthened task-step inspection with sequencing metadata and approval linkage
- shared web layer
  - created `apps/web/lib/api.ts` for shared types, config, endpoint helpers, and live-mode detection
  - created `apps/web/lib/fixtures.ts` for explicit fixture-backed fallback data
  - added new shared components:
    - `approval-actions`
    - `approval-detail`
    - `task-summary`
  - added a minimal Vitest-based web test setup with unit coverage for the API helper layer and a UI flow boundary test for approval resolution
  - updated styling in `apps/web/app/globals.css` for governed form layout, action bars, responsive field grids, and richer workflow state presentation

## incomplete work

- no approval execution from the web UI
- no task-step mutations from the web UI beyond inspection
- no live request-history read endpoint in `/chat`; the screen submits live requests but keeps local summary history plus explicit fixture fallback
- no Gmail, Calendar, runner, auth, or backend-scope expansion

## exact screens and components implemented or updated

- screens
- `/chat`
- `/approvals`
- `/tasks`
- `/approvals/loading`
- `/tasks/loading`
- components
  - `request-composer`
  - `approval-list`
  - `approval-actions`
  - `approval-detail`
  - `task-list`
  - `task-summary`
  - `task-step-list`
  - `status-badge`

## files changed

- `BUILD_REPORT.md`
- `apps/web/app/chat/page.tsx`
- `apps/web/app/approvals/page.tsx`
- `apps/web/app/approvals/loading.tsx`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/tasks/loading.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/request-composer.tsx`
- `apps/web/components/approval-list.tsx`
- `apps/web/components/approval-actions.tsx`
- `apps/web/components/approval-detail.tsx`
- `apps/web/components/task-list.tsx`
- `apps/web/components/task-summary.tsx`
- `apps/web/components/task-step-list.tsx`
- `apps/web/components/status-badge.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/lib/fixtures.ts`
- `apps/web/components/approval-actions.test.tsx`
- `apps/web/test/setup.ts`
- `apps/web/vitest.config.ts`
- `apps/web/package.json`

## route backing

- `/chat`: mixed
  - live submission when `apiBaseUrl` and `userId` are configured
  - explicit fixture preview and local summary fallback otherwise
- `/approvals`: mixed
  - live inbox, live detail, and live approve/reject when configured
  - explicit fixture fallback for list and detail when live data is unavailable
  - explicit route-level loading UI while server reads are in flight
- `/tasks`: mixed
  - live task list, live task detail, and live task-step reads when configured
  - explicit fixture fallback for list, detail, and steps when live data is unavailable
  - explicit route-level loading UI while server reads are in flight

## shipped backend endpoints consumed

- `POST /v0/approvals/requests`
- `GET /v0/approvals`
- `GET /v0/approvals/{approval_id}`
- `POST /v0/approvals/{approval_id}/approve`
- `POST /v0/approvals/{approval_id}/reject`
- `GET /v0/tasks`
- `GET /v0/tasks/{task_id}`
- `GET /v0/tasks/{task_id}/steps`

## commands run

- `npm install --no-package-lock` in `apps/web`
- `npm run test` in `apps/web`
- `npm run build` in `apps/web`

## tests run

- `npm run test` in `apps/web`
- `npm run build` in `apps/web`

## build and test results

- `npm run test`: PASS
- production build completed successfully
- generated routes included:
  - `/`
  - `/chat`
  - `/approvals`
  - `/tasks`
  - `/traces`
- automated coverage now includes:
  - API helper request and error-envelope behavior
  - approval action-bar UI flow and route refresh behavior

## concise visual verification notes

- desktop: split review layouts remain intact for approvals and tasks, the governed request form still uses bounded two-column field groupings, and route-level loading cards now preserve the same shell hierarchy during slow reads
- mobile: the existing responsive breakpoints still collapse the sidebar layouts to one column, and the new loading cards and field groups stack cleanly at narrow widths
- browser screenshots were not captured; these notes are from code-path and responsive-layout verification only

## blockers/issues

- `next build` rewrote `apps/web/tsconfig.json` and `apps/web/next-env.d.ts` during type checking; those generated edits were manually reverted to keep the final diff inside the sprint packet’s scoped file list
- `npm run lint` is still not a usable project check because `next lint` drops into interactive ESLint setup instead of running repo-defined rules

## recommended next step

Open a follow-up UI sprint only if you want to reduce operator friction around request submission, most likely by introducing a bounded live selector for known thread and tool IDs through already-shipped seams or explicitly approved new scope.

## intentionally deferred after this sprint

- approval execution UI
- task-step mutation UI
- general trace-event listing work
- connector expansion
- auth redesign
