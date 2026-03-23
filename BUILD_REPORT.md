# BUILD_REPORT.md

## Sprint Objective
Implement Phase 2 Sprint 7 `/chat` manual capture controls so operators can trigger the shipped unified explicit-signal capture endpoint (`POST /v0/memories/capture-explicit-signals`) for selected `message.user` events, with deterministic rail rendering and no automatic capture behavior.

## `/chat` Control Behavior And Trigger Rules
- Added a new rail section in `ThreadEventList` titled `Manual capture control`.
- Eligible source events are strictly bounded to `message.user` events only.
- Eligible events are selectable through an explicit dropdown control.
- Capture runs only on explicit button click (`Capture explicit signals`).
- No automatic capture is triggered on:
  - page load
  - mode toggle
  - thread selection/event-list changes
- Live capture button enablement is deterministic:
  - requires `source === "live"`
  - requires API config (`apiBaseUrl`, `userId`)
  - requires at least one eligible `message.user` event

## Capture Result Rendering (Live/Fixture/Unavailable)
- Live mode:
  - Capture executes via `captureExplicitSignals(apiBaseUrl, { user_id, source_event_id })`.
  - Success renders deterministic summary chips:
    - `Candidates {count}`
    - `Admissions {count}`
    - `Open loops created {count}`
    - `Open loops noop {count}`
  - Source event confirmation renders as:
    - `{source_event_id} ({source_event_kind})`
  - Error renders deterministic non-destructive status text:
    - `Capture failed: {error message}`
- Fixture mode:
  - Capture control is disabled.
  - Explicit fixture message is shown:
    - `Fixture mode is non-destructive. Configure live API settings to enable capture.`
- Unavailable mode:
  - Capture control is disabled.
  - Explicit unavailable reason is shown using continuity failure reason when present.

## Completed Work
- Updated `apps/web/components/thread-event-list.tsx`:
  - converted to client component
  - added manual explicit-signal capture form
  - added eligible-event selection constrained to `message.user`
  - added deterministic live/fixture/unavailable gating and status messaging
  - added deterministic success summary rendering for required aggregate fields
- Updated `apps/web/app/chat/page.tsx`:
  - passed live API context (`apiBaseUrl`, `userId`) into `ThreadEventList`
- Updated `apps/web/components/thread-event-list.test.tsx`:
  - eligible event selection behavior
  - no auto-capture on render
  - request payload correctness (`user_id`, `source_event_id`)
  - deterministic success rendering
  - deterministic error rendering
  - explicit fixture/unavailable disabled-state behavior
- Updated `apps/web/lib/api.test.ts`:
  - added explicit `captureExplicitSignals` backend-error envelope `ApiError` assertion
  - retained explicit request wiring assertions for endpoint/payload contract

## Incomplete Work
- None within sprint scope.

## Files Changed
- `apps/web/app/chat/page.tsx`
- `apps/web/components/thread-event-list.tsx`
- `apps/web/components/thread-event-list.test.tsx`
- `apps/web/lib/api.test.ts`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `ARCHITECTURE.md`

## Tests Run
1. `cd apps/web && pnpm test -- lib/api.test.ts components/thread-event-list.test.tsx app/chat/page.test.tsx`
- Outcome: `3 passed` test files, `31 passed` tests, `0 failed` (initial Sprint 7 implementation run).

2. `cd apps/web && pnpm lint -- app/chat/page.tsx components/thread-event-list.tsx components/thread-event-list.test.tsx lib/api.test.ts`
- Outcome: `eslint` completed with `0` warnings / `0` errors (initial Sprint 7 implementation run).

3. `cd apps/web && pnpm test -- lib/api.test.ts components/thread-event-list.test.tsx app/chat/page.test.tsx`
- Outcome: `3 passed` test files, `35 passed` tests, `0 failed` (review-fix run adding continuity-regression + live negative-state coverage).

4. `cd apps/web && pnpm lint -- app/chat/page.tsx components/thread-event-list.tsx components/thread-event-list.test.tsx lib/api.test.ts`
- Outcome: `eslint` completed with `0` warnings / `0` errors (review-fix run).

## Blockers/Issues
- No functional blockers.

## Explicit Deferred Scope
- autonomous follow-up execution or reminders
- background workers or scheduler integration
- connector expansion
- backend extraction/orchestration contract changes
- multi-agent runtime/profile routing (Phase 3)

## Recommended Next Step
Proceed to Control Tower integration review focused on `/chat` control/API-client coherence and sprint-scope validation, then open the sprint PR.
