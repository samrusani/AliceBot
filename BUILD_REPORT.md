# BUILD_REPORT.md

## Sprint Objective
Implement Phase 2 Sprint 4 deterministic resumption briefs (typed contracts, user-scoped API, compiler-backed deterministic assembly, and `/chat` selected-thread display adoption) without adding automation, worker orchestration, or Phase 3 runtime/profile routing.

## Completed Work
- Shipped typed resumption-brief contracts and bounds in `apps/api/src/alicebot_api/contracts.py`.
- Shipped `GET /v0/threads/{thread_id}/resumption-brief` in `apps/api/src/alicebot_api/main.py`.
- Added bounded query inputs:
  - `user_id` (required)
  - `max_events` (default `8`, max `50`)
  - `max_open_loops` (default `5`, max `20`)
  - `max_memories` (default `5`, max `20`)
- Added compiler-backed deterministic brief assembly in `apps/api/src/alicebot_api/compiler.py` via `compile_resumption_brief(...)`.
- Brief assembly is sourced from existing durable seams only:
  - selected thread metadata
  - latest conversation events (`message.user`, `message.assistant`)
  - active open loops (`status="open"`)
  - active memory highlights
  - latest task + latest task-step posture for the selected thread when present
- Added `/chat` adoption:
  - `apps/web/lib/api.ts`: typed client + `getThreadResumptionBrief(...)`
  - `apps/web/app/chat/page.tsx`: live/fixture/unavailable brief loading
  - `apps/web/components/thread-summary.tsx`: brief section rendering in selected-thread panel
- Added/updated sprint-scoped backend/frontend tests for contracts/API/assembly/UI seams.

## Exact Resumption-Brief Fields Shipped
- Top-level `brief` payload:
  - `assembly_version`
  - `thread`
  - `conversation`
    - `items`
    - `summary`: `limit`, `returned_count`, `total_count`, `order`, `kinds`
  - `open_loops`
    - `items`
    - `summary`: `limit`, `returned_count`, `total_count`, `order`
  - `memory_highlights`
    - `items`
    - `summary`: `limit`, `returned_count`, `total_count`, `order`
  - `workflow` (`null` when absent)
    - `task`
    - `latest_task_step`
    - `summary`: `present`, `task_order`, `task_step_order`
  - `sources`

## API Surface Deltas And Deterministic Ordering Rules
- New endpoint:
  - `GET /v0/threads/{thread_id}/resumption-brief`
- Deterministic not-found behavior:
  - missing thread and cross-user thread both return `404` with thread-specific detail.
- Deterministic ordering and bounded windows:
  - conversation candidates ordered by `sequence_no_asc`, then bounded to latest window (`max_events`).
  - open loops ordered by `opened_at_desc`, `created_at_desc`, `id_desc`, then bounded by `max_open_loops`.
  - memory highlights ordered by `updated_at_asc`, `created_at_asc`, `id_asc`, then bounded to latest window (`max_memories`).
  - workflow posture uses latest task by `created_at_asc`, `id_asc` and latest task-step by `sequence_no_asc`, `created_at_asc`, `id_asc`.

## Incomplete Work
- None within sprint scope.

## Files Changed
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/compiler.py`
- `apps/web/lib/api.ts`
- `apps/web/app/chat/page.tsx`
- `apps/web/components/thread-summary.tsx`
- `tests/unit/test_compiler.py`
- `tests/unit/test_main.py`
- `tests/integration/test_continuity_api.py`
- `apps/web/lib/api.test.ts`
- `apps/web/components/thread-summary.test.tsx`
- `apps/web/app/chat/page.test.tsx`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `PYTHONPATH=$PWD .venv/bin/pytest tests/unit/test_compiler.py tests/unit/test_main.py`
- Outcome: `53 passed`

2. `cd apps/web && pnpm test -- app/chat/page.test.tsx components/thread-summary.test.tsx lib/api.test.ts`
- Outcome: `28 passed`

3. `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_continuity_api.py`
- Outcome: `3 passed`
- Note: executed with escalated permissions to allow local Postgres access from this environment.

## Blockers/Issues
- No unresolved blockers.
- Environment constraint: DB-backed integration tests require execution outside default sandbox network restrictions.

## Explicit Deferred Scope
- autonomous follow-up behavior/reminders
- background worker or scheduler integration
- automation orchestration
- Phase 3 multi-agent runtime/profile routing
- database migrations/new tables outside sprint scope

## Recommended Next Step
Proceed to Control Tower integration review for Sprint 4, focusing on deterministic brief payload coherence across contracts/API/compiler/UI and merge after reviewer `PASS` + explicit merge approval.
