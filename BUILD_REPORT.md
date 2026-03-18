# BUILD_REPORT.md

## Sprint Objective
Implement Sprint 6R: add a bounded `/artifacts` artifact review workspace UI in the web shell that uses only shipped backend task-workspace/task-artifact/chunk read endpoints, with stable loading/empty/unavailable behavior and explicit live/fixture fallback.

## Completed Work
- Added new route files:
  - `apps/web/app/artifacts/page.tsx`
  - `apps/web/app/artifacts/loading.tsx`
- Implemented bounded artifact review components:
  - `apps/web/components/artifact-list.tsx`
  - `apps/web/components/artifact-detail.tsx`
  - `apps/web/components/artifact-workspace-summary.tsx`
  - `apps/web/components/artifact-chunk-list.tsx`
- Extended shared API layer in `apps/web/lib/api.ts` with typed read functions and contracts for:
  - task workspace list/detail
  - task artifact list/detail
  - task artifact chunk list
- Added fixture-backed artifact/workspace/chunk data and helpers in `apps/web/lib/fixtures.ts` to preserve explicit fallback behavior when live API is absent or partially unavailable.
- Integrated `/artifacts` into shell discoverability:
  - Added navigation entry in `apps/web/components/app-shell.tsx`
  - Added home route card and summary updates in `apps/web/app/page.tsx`
  - Updated shell metadata description in `apps/web/app/layout.tsx`
- Updated styling in `apps/web/app/globals.css` for artifact layouts and readable chunk evidence rendering.
- Added sprint-scope tests:
  - `apps/web/components/artifact-list.test.tsx`
  - `apps/web/components/artifact-chunk-list.test.tsx`
  - `apps/web/app/artifacts/page.test.tsx`
  - Expanded `apps/web/lib/api.test.ts` to verify workspace/artifact/chunk endpoint usage.
- Updated status handling in `apps/web/components/status-badge.tsx` for `ingested` and `registered` badge tones used by artifact surfaces.

## Artifact Surface Backing Mode
- Artifact list (`artifact-list`): mixed-capable (`live` when configured, `fixture` fallback, explicit unavailable note when live list read fails).
- Selected artifact detail (`artifact-detail`): mixed-capable (`live` detail with fixture fallback when available).
- Linked workspace summary (`artifact-workspace-summary`): mixed-capable (`live` workspace detail with fixture fallback when available, explicit unavailable state when neither is available).
- Chunk review (`artifact-chunk-list`): mixed-capable (`live` chunks with fixture fallback when available, explicit unavailable state when neither is available).

## Exact Backend Endpoints Consumed By `/artifacts` Runtime Flow
- `GET /v0/task-workspaces/{task_workspace_id}`
- `GET /v0/task-artifacts`
- `GET /v0/task-artifacts/{task_artifact_id}`
- `GET /v0/task-artifacts/{task_artifact_id}/chunks`

## Additional Endpoint Implemented/Tested In Shared API Helper Layer
- `GET /v0/task-workspaces` (implemented in `apps/web/lib/api.ts` and covered by `apps/web/lib/api.test.ts`, but not called in `/artifacts` page orchestration)

## Incomplete Work
- None within Sprint 6R acceptance scope.

## Files Changed
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/artifacts/page.tsx`
- `apps/web/app/artifacts/loading.tsx`
- `apps/web/app/artifacts/page.test.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/app-shell.tsx`
- `apps/web/components/status-badge.tsx`
- `apps/web/components/artifact-list.tsx`
- `apps/web/components/artifact-detail.tsx`
- `apps/web/components/artifact-workspace-summary.tsx`
- `apps/web/components/artifact-chunk-list.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/fixtures.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/components/artifact-list.test.tsx`
- `apps/web/components/artifact-chunk-list.test.tsx`
- `BUILD_REPORT.md`

## Exact Commands Run
- `npm run lint` (in `apps/web`)
- `npm test` (in `apps/web`)
- `npm run build` (in `apps/web`)

## Test and Verification Results
- `npm run lint`: PASS
- `npm test`: PASS (`25` test files, `79` tests passed)
- `npm run build`: PASS (Next.js production build completed, `/artifacts` route included in output)

## Desktop and Mobile Visual Verification Notes
- Desktop: `/artifacts` follows the bounded review flow in two stages: list/detail first, workspace/chunks second; card rhythm, badge patterns, and spacing are consistent with existing shell primitives.
- Mobile/tablet: artifact layouts collapse to single-column under existing responsive breakpoints; list/detail/chunk content remain contained with readable wrapping and scroll-bounded chunk text blocks.

## Blockers / Issues
- No blockers encountered.

## Intentionally Deferred (Out of Scope)
- Artifact registration or ingestion actions.
- Retrieval or semantic retrieval controls.
- Gmail account management UI.
- Backend contract changes or new endpoints.
- Calendar/auth/runner/connector expansion.
- Broad file-browser/document-manager features.

## Recommended Next Step
Run reviewer pass focused on Sprint 6R review criteria (scope containment, endpoint usage, bounded UI behavior), then open PR from `codex/sprint-6r-artifact-review-workspace-ui` once Control Tower approves.
