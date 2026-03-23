# SPRINT_PACKET.md

## Sprint Title

Phase 2 Sprint 7: Chat Capture Controls

## Sprint Type

feature

## Sprint Reason

Phase 2 Sprint 6 unified explicit signal capture is merged. The endpoint exists but is not yet available in an operator workflow. The next seam is bounded `/chat` adoption so capture can be triggered deliberately from visible thread events.

## Sprint Intent

Implement bounded `/chat` controls to manually trigger the shipped unified explicit-signal capture endpoint for selected `message.user` events, and render deterministic capture results in the operator rail without introducing automatic capture behavior.

## Git Instructions

- Branch Name: `codex/phase2-sprint7-chat-capture-controls`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Unified capture API is shipped and stable.
- Operators still need manual API invocation outside the product surface.
- This is the narrowest product-facing seam before any optional capture automation.

## Design Truth

- Reuse shipped `POST /v0/memories/capture-explicit-signals`; do not duplicate backend logic.
- Keep capture manually initiated from explicit user action in UI.
- Preserve clear source visibility (`source_event_id`) and deterministic result rendering.

## Exact Surfaces In Scope

- `/chat` operator controls for explicit-signal capture
- deterministic capture result rendering in rail context
- web API client integration (existing endpoint)
- sprint-scoped frontend and targeted API-client tests

## Exact Files In Scope

- [api.ts](apps/web/lib/api.ts)
- [api.test.ts](apps/web/lib/api.test.ts)
- [page.tsx](apps/web/app/chat/page.tsx)
- [thread-event-list.tsx](apps/web/components/thread-event-list.tsx)
- [thread-event-list.test.tsx](apps/web/components/thread-event-list.test.tsx)
- [page.test.tsx](apps/web/app/chat/page.test.tsx)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)
- relevant tests under:
  - `apps/web/**/*.test.tsx`

## In Scope

- Add a bounded UI control in `/chat` rail that allows operator-triggered capture for selected `message.user` events only.
- Use shipped API client (`captureExplicitSignals(...)`) against `POST /v0/memories/capture-explicit-signals`.
- Render deterministic result summary in UI:
  - candidate/admission counts
  - open-loop created/noop counts
  - source event confirmation
- Keep explicit live/fixture/unavailable handling:
  - live mode: controls enabled when API config + eligible event exists
  - fixture mode: clear non-destructive fixture messaging
  - unavailable mode: deterministic disabled state + reason
- Ensure no automatic capture trigger on page load, mode switch, or thread selection.
- Add/update frontend tests for:
  - eligible event selection behavior
  - request payload correctness (`user_id`, `source_event_id`)
  - success/error rendering and disabled states

## Out of Scope

- autonomous follow-up execution or reminders
- background workers or scheduler integration
- connector expansion
- multi-agent runtime/profile routing (Phase 3)
- backend extraction/orchestration contract changes
- broad UI redesign outside scoped `/chat` rail controls

## Required Deliverables

- `/chat` rail control for manual explicit-signal capture
- deterministic capture outcome rendering in UI
- updated API-client wiring/tests for UI behavior
- updated sprint reports for this sprint only

## Acceptance Criteria

- capture can be triggered from `/chat` for an eligible `message.user` event in live mode
- emitted request payload is deterministic and correct (`user_id`, `source_event_id`)
- success UI shows coherent aggregate results from endpoint response
- error UI is deterministic and non-destructive
- fixture/unavailable states are explicit and safe
- no automatic capture side effects occur
- touched frontend + API-client tests pass
- no out-of-scope automation, worker, or Phase 3 routing work enters sprint

## Implementation Constraints

- preserve manual user initiation requirement
- preserve deterministic and transparent source-event mapping in UI
- avoid introducing stateful background polling or hidden retries
- co-deliver tests with each seam change

## Control Tower Task Cards

### Task 1: Chat UI Adoption
Owner: frontend operative  
Write scope:
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/chat/page.tsx`
- `apps/web/components/thread-event-list.tsx`
- related chat component tests

### Task 2: Integration Review
Owner: control tower  
Responsibilities:
- verify chat-control/API-client coherence
- verify strict sprint scope
- verify acceptance + evidence completeness

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact `/chat` control behavior and trigger rules
- capture result rendering behavior for live/fixture/unavailable states
- exact commands/tests run with outcomes
- explicit deferred scope (automation/workers/Phase 3 runtime orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint remained chat-capture-controls scoped
- chat-control/API-client consistency
- sufficient tests for all touched seams
- no hidden scope expansion

## Exit Condition

This sprint is complete when `/chat` exposes safe manual controls for unified explicit-signal capture with deterministic result rendering and test-backed behavior, without backend contract drift or automation/worker/Phase 3 scope expansion.
