# SPRINT_PACKET.md

## Sprint Title

Sprint 6C: Web Workspace Verification Stabilization

## Sprint Type

repair

## Sprint Reason

Sprint 6B successfully turned the shell into a governed workflow surface, but the accepted review still identified two recurring frontend quality issues: `npm run lint` is not a usable non-interactive check, and `next build` still rewrites `apps/web/tsconfig.json` plus `apps/web/next-env.d.ts` during verification. Before stacking more UI work on top of the shell, the web workspace needs one narrow stabilization sprint so future UI delivery is not slowed down by avoidable tooling churn.

## Sprint Intent

Stabilize the `apps/web` workspace so lint and build are clean, repeatable, non-interactive verification steps, while preserving the Sprint 6A and Sprint 6B operator shell behavior and avoiding any backend scope changes.

## Git Instructions

- Branch Name: `codex/sprint-6c-web-workspace-verification-stabilization`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 6A opened the first real web shell.
- Sprint 6B made the shell workflow-bearing with governed request submission, approvals, and live task inspection.
- The accepted review for Sprint 6B called out:
  - `npm run lint` is still interactive because the web workspace lacks a committed lint setup
  - `next build` still rewrites `apps/web/tsconfig.json` and `apps/web/next-env.d.ts`
- Those are not merge blockers for 6B, but they will keep generating review friction and workspace churn if not fixed now.
- The narrowest safe next step is to stabilize the web workspace itself, not to widen UI scope or reopen backend work.

## Design Truth

- `DESIGN_SYSTEM.md` remains the design source of truth.
- This sprint is not a new visual redesign sprint.
- UI behavior and styling should remain materially unchanged except where small markup or styling adjustments are needed to support stable lint/build verification.

## Exact Files In Scope

- `apps/web/package.json`
- `apps/web/tsconfig.json`
- `apps/web/next-env.d.ts`
- `apps/web/next.config.mjs`
- `apps/web/eslint.config.mjs`
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/chat/page.tsx`
- `apps/web/app/approvals/page.tsx`
- `apps/web/app/tasks/page.tsx`
- `apps/web/app/traces/page.tsx`
- `apps/web/app/approvals/loading.tsx`
- `apps/web/app/tasks/loading.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/app-shell.tsx`
- `apps/web/components/page-header.tsx`
- `apps/web/components/section-card.tsx`
- `apps/web/components/status-badge.tsx`
- `apps/web/components/empty-state.tsx`
- `apps/web/components/request-composer.tsx`
- `apps/web/components/approval-list.tsx`
- `apps/web/components/approval-actions.tsx`
- `apps/web/components/approval-detail.tsx`
- `apps/web/components/task-list.tsx`
- `apps/web/components/task-summary.tsx`
- `apps/web/components/task-step-list.tsx`
- `apps/web/components/trace-list.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/fixtures.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/components/approval-actions.test.tsx`
- `apps/web/test/setup.ts`
- `apps/web/vitest.config.ts`
- `BUILD_REPORT.md`

## In Scope

- Commit a stable non-interactive lint configuration for `apps/web`.
- Ensure `npm run lint` runs without prompting for ESLint initialization.
- Ensure `npm run build` no longer creates uncommitted churn in `apps/web/tsconfig.json` or `apps/web/next-env.d.ts`.
- Adopt or normalize any framework-generated TypeScript config changes deliberately so future builds stay clean.
- Keep the Sprint 6A and 6B screens, routes, and workflow behavior intact.
- Update or add narrow frontend tests only as needed to preserve current behavior while the workspace config is being stabilized.

## Out of Scope

- No new backend endpoints.
- No backend schema changes.
- No new product workflow features.
- No Gmail breadth, Calendar UI, or connector expansion.
- No auth redesign.
- No new pages or routes beyond what already shipped in 6A/6B.
- No visual redesign of the shell.
- No runner-style orchestration UI.

## Required Deliverables

- A committed non-interactive lint setup for `apps/web`.
- A stable build setup that does not rewrite tracked web config files during routine verification.
- Preserved Sprint 6A and 6B behavior across the shipped routes and workflow surfaces.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- `npm run lint` in `apps/web` runs non-interactively and passes.
- `npm run build` in `apps/web` passes.
- Running `npm run build` after a clean checkout does not create uncommitted churn in `apps/web/tsconfig.json` or `apps/web/next-env.d.ts`.
- The shipped routes remain intact:
  - `/`
  - `/chat`
  - `/approvals`
  - `/tasks`
  - `/traces`
- The governed request, approval, and task UI behavior from Sprint 6B remains intact.
- No backend scope expansion enters the sprint.

## Implementation Constraints

- Keep the sprint narrow and boring.
- Treat this as workspace stabilization, not a feature sprint.
- Prefer adopting framework-required config intentionally over repeatedly reverting generated files.
- Do not hide UI redesign work inside lint/build cleanup.
- If markup changes are needed to satisfy the committed lint rules, keep them minimal and behavior-preserving.

## Suggested Work Breakdown

1. Add a committed ESLint configuration for `apps/web`.
2. Normalize package scripts so lint/test/build form a stable non-interactive verification set.
3. Resolve the `next build` config churn by adopting or normalizing the generated TypeScript settings deliberately.
4. Run lint, tests, and build to confirm a clean repeatable web workspace.
5. Update `BUILD_REPORT.md` with exact verification and any intentionally adopted config changes.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact workspace/config files changed
- the lint command and build command used
- whether TypeScript or Next-generated config changes were intentionally adopted
- exact verification results for lint, test, and build
- confirmation that Sprint 6A/6B route behavior remained intact
- what remains intentionally deferred after this repair sprint

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed a repair sprint and did not widen backend or product scope
- `npm run lint` is now non-interactive and passes
- `npm run build` is stable and no longer rewrites tracked config files during routine verification
- Sprint 6A/6B route behavior remains intact
- no hidden UI redesign, Gmail breadth, Calendar, auth, runner, or backend-scope expansion entered the sprint

## Exit Condition

This sprint is complete when the `apps/web` workspace has stable non-interactive lint/build verification, no longer creates routine config churn during `next build`, and preserves the shipped operator shell behavior from Sprints 6A and 6B.
