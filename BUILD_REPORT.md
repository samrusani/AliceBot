# BUILD_REPORT

## sprint objective

Deliver Sprint 6L by extending `/chat` with bounded selected-thread governed workflow review so approval, task, and execution state stay visible beside the durable transcript without widening backend scope.

## exact `/chat` workflow files and components updated

- `apps/web/app/chat/page.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/approval-detail.tsx`
- `apps/web/components/task-summary.tsx`
- `apps/web/components/thread-workflow-panel.tsx`
- `apps/web/components/thread-workflow-panel.test.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `BUILD_REPORT.md`

## thread-linked workflow backing mode

- Mixed.
- Live workflow review uses existing shipped reads from approvals, tasks, and tool executions when API configuration is present.
- Fixture workflow review is used when API configuration is absent.
- Live workflow failures degrade to explicit unavailable states inside the chat workflow panel instead of implying missing workflow.

## shipped backend endpoints consumed

- `GET /v0/threads`
- `GET /v0/threads/{thread_id}`
- `GET /v0/threads/{thread_id}/events`
- `GET /v0/threads/{thread_id}/sessions`
- `GET /v0/approvals`
- `GET /v0/tasks`
- `GET /v0/tool-executions`
- `POST /v0/approvals/{approval_id}/approve`
- `POST /v0/approvals/{approval_id}/reject`
- `POST /v0/approvals/{approval_id}/execute`
- `POST /v0/approvals/requests`
- `POST /v0/threads`
- `POST /v0/responses`

## completed work

- Added a new `thread-workflow-panel` to `/chat` so selected-thread workflow state now appears in the rail as a bounded secondary review surface.
- Derived the latest relevant approval and task state client-side from shipped list endpoints and existing fixtures, keyed by the selected thread.
- Restricted execution review to explicit linkage only: selected-task `latest_execution_id` first, then execution records explicitly linked to the selected approval, with no thread-level fallback.
- Reused `approval-detail`, `approval-actions`, `task-summary`, and `execution-summary` inside compact embedded cards so the chat route inherits the same workflow semantics as `/approvals` and `/tasks`.
- Restored bounded execution review when approval detail is absent by rendering execution review through the task summary or a standalone embedded execution block when needed.
- Preserved transcript-first hierarchy by keeping workflow review secondary and visually quieter than the conversation column.
- Tightened rail containment with embedded card chrome, single-column key-value layouts, bounded execution code blocks, and full-width action layouts that avoid cramped wrapping.
- Added in-scope regression coverage for mixed-history execution linkage and approval-missing execution review in `apps/web/lib/api.test.ts` and `apps/web/components/thread-workflow-panel.test.tsx`.

## exact commands run

- `npm run lint`
- `npm test`
- `npm run build`

## verification results

- `npm run lint`: passed
- `npm test`: passed, `13` test files and `46` tests passed
- `npm run build`: passed

## concise desktop visual verification notes

- No fresh interactive desktop browser verification was performed during this fix turn.
- Desktop layout expectations were reviewed by component and CSS inspection only, alongside a successful production build.
- A manual desktop pass for real long-thread and long-execution payloads remains advisable before merge.

## concise mobile visual verification notes

- No fresh interactive mobile or responsive browser verification was performed during this fix turn.
- Mobile behavior expectations were reviewed from the existing responsive CSS and component structure only.
- A manual narrow-viewport pass remains advisable before merge.

## deferred scope

- No backend changes or new thread-specific workflow endpoints.
- No redesign of `/approvals` or `/tasks`.
- No task-step mutation UI beyond the shipped approval resolution and execute actions.
- No inbox, dashboard, pagination, search, or broader workflow surfacing beyond the selected thread.
- No changes to `DESIGN_SYSTEM.md`; the sprint did not reveal a concrete contradiction that required rewriting the design system.

## worktree notes

- `.ai/active/SPRINT_PACKET.md` was already modified before this sprint work and was not changed here.
