# BUILD_REPORT.md

## Sprint Objective
Implement Sprint 7C memory-review throughput updates on `/memories`: add deterministic queue-mode label-and-advance flow and add progress visibility for labels remaining to minimum adjudicated sample.

## Completed Work
- Added memory-quality progress metric in utility layer:
  - `remaining_to_minimum_sample = max(0, minimum_sample - adjudicated_sample)`
  - surfaced as `remainingToMinimumSample` in `deriveMemoryQualityGate(...)` output.
- Updated memory-quality gate UI to render progress deterministically:
  - new key metric row: `Remaining to minimum sample`
  - new copy line:
    - unavailable: `Progress to minimum sample is unavailable.`
    - met: `Progress: minimum adjudicated sample is met.`
    - unmet: `Progress: N labels remaining to reach the minimum sample.`
- Added deterministic queue advance wiring in `/memories` route:
  - computes next queue target from current visible queue order only.
  - passes `activeFilter` and `nextQueueMemoryId` into `memory-label-form`.
- Extended `memory-label-form` with explicit queue action:
  - existing action preserved: `Submit review label`
  - queue action added (only when queue mode + next exists): `Submit and next in queue`
  - single-submit behavior unchanged outside queue mode.
  - queue submit-and-next posts label first, then navigates to:
    - `/memories?filter=queue&memory={nextQueueMemoryId}`
- Updated runbook for queue adjudication workflow and stop conditions.
- Added deterministic tests for:
  - remaining-to-sample metric behavior
  - queue submit-and-next button visibility rules
  - queue submit-and-next navigation behavior
  - disabled states in non-live mode with clear messaging

## Incomplete Work
- None within Sprint 7C scope.

## Files Changed
- `apps/web/app/memories/page.tsx`
- `apps/web/app/memories/page.test.tsx`
- `apps/web/components/memory-label-form.tsx`
- `apps/web/components/memory-label-form.test.tsx`
- `apps/web/components/memory-quality-gate.tsx`
- `apps/web/components/memory-quality-gate.test.tsx`
- `apps/web/components/memory-summary.test.tsx`
- `apps/web/lib/memory-quality.ts`
- `apps/web/lib/memory-quality.test.ts`
- `docs/runbooks/memory-quality-gate.md`
- `BUILD_REPORT.md`

## Queue-Advance Rules (Shipped)
- Queue-advance action is shown only when:
  - filter is `queue`
  - selected memory has a next item in the current visible queue ordering.
- Deterministic next target:
  - based on current `visibleMemories` order in route state
  - `nextQueueMemoryId = visibleMemories[selectedIndex + 1]?.id ?? null`
- Submission behavior:
  - always explicit, user-triggered POST
  - no background labeling
  - no auto-labeling
- Non-queue mode:
  - preserves existing single-submit behavior (`router.refresh()` only).

## Sample-Progress Formula (Shipped)
- `adjudicated_sample = correct + incorrect`
- `remaining_to_minimum_sample = max(0, 10 - adjudicated_sample)`

## Queue-Advance Surface Source Mode
- Mixed by design, depending on data source state:
  - Live: action enabled when selected memory detail source is live and API config is present.
  - Fixture/Unavailable: controls remain visible but submission actions are disabled with explicit explanation.

## Endpoints Consumed (No New Contracts)
- `GET /v0/memories/review-queue`
- `POST /v0/memories/{memory_id}/labels`
- `GET /v0/memories/evaluation-summary`

## Tests Run
Commands executed in `apps/web`:
- `npm run lint`
- `npm test`
- `npm run build`

Results:
- `npm run lint`: PASS
- `npm test`: PASS (`35` files, `115` tests)
- `npm run build`: PASS (Next.js production build completed successfully)

## Desktop/Mobile Verification Notes
- Desktop: verified behavior via unit/integration tests for queue advance visibility, submit-and-next navigation, and progress copy.
- Mobile: no dedicated viewport automation added this sprint; responsive behavior relies on existing shared button/layout rules already present in `globals.css` (unchanged in this sprint).

## Blockers/Issues
- No implementation blockers encountered.

## Deferred Scope (Intentional)
- No backend endpoint changes.
- No memory extraction/retrieval/reranking changes.
- No auth/runner/orchestration changes.
- No unrelated route redesign.

## Recommended Next Step
Run Reviewer validation against Sprint 7C acceptance criteria, focusing on deterministic queue progression and live/fixture/unavailable operator messaging on `/memories`.
