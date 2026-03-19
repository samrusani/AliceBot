# BUILD_REPORT.md

## Sprint Objective
Implement Sprint 6V: add a bounded `/calendar` workspace in the web shell for Calendar account review, selected account detail, explicit Calendar account connection, and explicit single-event ingestion into one selected task workspace using only shipped backend seams.

## Completed Work
- Added Calendar API typing + helper methods in `apps/web/lib/api.ts` for:
  - `POST /v0/calendar-accounts`
  - `GET /v0/calendar-accounts`
  - `GET /v0/calendar-accounts/{calendar_account_id}`
  - `POST /v0/calendar-accounts/{calendar_account_id}/events/{provider_event_id}/ingest`
  - `GET /v0/task-workspaces` (already present; reused for Calendar ingestion target selection)
- Added Calendar fixtures/helpers in `apps/web/lib/fixtures.ts`:
  - `calendarAccountFixtures`
  - `calendarAccountListSummaryFixture`
  - `getFixtureCalendarAccount(...)`
- Added `/calendar` route and loading state:
  - `apps/web/app/calendar/page.tsx`
  - `apps/web/app/calendar/loading.tsx`
- Added scoped Calendar components:
  - `calendar-account-list`
  - `calendar-account-detail`
  - `calendar-account-connect-form`
  - `calendar-event-ingest-form`
  - `calendar-ingestion-summary`
- Added shell integration for discoverability:
  - Calendar navigation item in `apps/web/components/app-shell.tsx`
  - Calendar card and updated counts in `apps/web/app/page.tsx`
  - Calendar mention in `apps/web/app/layout.tsx` metadata
- Added minimal style integration for Calendar layout wrappers in `apps/web/app/globals.css`:
  - `calendar-layout`
  - `calendar-action-grid`
  - responsive collapse at existing breakpoints
- Added test coverage:
  - Calendar API endpoint helper assertions in `apps/web/lib/api.test.ts`
  - Calendar account list rendering behavior test
  - Calendar event ingestion form behavior test

## Calendar Surface Backing Mode
- `calendar-account-list`: live API when configured; fixture-backed fallback when live config is absent or live list read fails; explicit unavailable state when source is unavailable and no accounts are present.
- `calendar-account-detail`: live API detail when configured and list is live; fixture fallback for selected account detail failure; explicit unavailable state when no fallback exists.
- `calendar-account-connect-form`: live-only write action (`POST /v0/calendar-accounts`); explicit unavailable/disabled behavior without live API config.
- `calendar-event-ingest-form`: live-only write action (`POST /v0/calendar-accounts/{id}/events/{provider_event_id}/ingest`) gated on live account detail + live task workspace list + live API config.
- `calendar-ingestion-summary`: live result display after successful ingestion; explicit idle and unavailable states otherwise.
- `/calendar` page mode chip: `Live API`, `Fixture-backed`, or `Mixed fallback` via `combinePageModes(...)`.

## Incomplete Work
- None for Sprint 6V in-scope deliverables.

## Files Changed
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/calendar/page.tsx`
- `apps/web/app/calendar/loading.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/app-shell.tsx`
- `apps/web/components/calendar-account-list.tsx`
- `apps/web/components/calendar-account-detail.tsx`
- `apps/web/components/calendar-account-connect-form.tsx`
- `apps/web/components/calendar-event-ingest-form.tsx`
- `apps/web/components/calendar-ingestion-summary.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/fixtures.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/components/calendar-account-list.test.tsx`
- `apps/web/components/calendar-event-ingest-form.test.tsx`
- `BUILD_REPORT.md`

## Tests Run
### Exact Commands
- `npm run lint` (run in `apps/web`)
- `npm test` (run in `apps/web`)
- `npm run build` (run in `apps/web`)

### Results
- `npm run lint`: PASS
- `npm test`: PASS (`29` files, `89` tests)
- `npm run build`: PASS (Next.js production build succeeded; `/calendar` route generated)

## Desktop and Mobile Visual Verification Notes
- Desktop verification (code-level): `/calendar` uses two-column `calendar-layout` (account list + selected detail) and two-column `calendar-action-grid` (connect + ingest stack), matching existing bounded workspace patterns.
- Mobile/tablet verification (code-level): `calendar-layout` and `calendar-action-grid` collapse to one column under `@media (max-width: 1120px)`; form two-up fields collapse to single column under `@media (max-width: 740px)`.

## Blockers / Issues
- No implementation blockers.
- No backend changes were required.

## Intentionally Deferred Scope
- Calendar event list/search UI.
- Recurrence expansion, sync, or backfill controls.
- Calendar write actions.
- Artifact editing from Calendar workspace.
- Gmail/auth/runner/backend scope expansion.

## Recommended Next Step
Run sprint review against `/calendar` UI behavior and scope boundaries, then open/merge the sprint PR per Control Tower policy if reviewer outcome is `PASS`.
