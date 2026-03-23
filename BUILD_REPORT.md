# BUILD_REPORT.md

## Sprint Objective
Implement Phase 2 Sprint 3 open-loop backbone end-to-end (schema, store, contracts/API, compiler serialization, and `/memories` review adoption) without adding automation, worker orchestration, resumption synthesis, or Phase 3 runtime behavior.

## Completed Work
- Shipped migration-backed `open_loops` domain with deterministic lifecycle fields:
  - `id`
  - `user_id`
  - `memory_id`
  - `title`
  - `status`
  - `opened_at`
  - `due_at`
  - `resolved_at`
  - `resolution_note`
  - `created_at`
  - `updated_at`
- Added open-loop status validation for `open`, `resolved`, and `dismissed`.
- Added store methods for open-loop create/list/detail/count/update-status with strict `user_id` scoping.
- Added API surface:
  - `GET /v0/open-loops`
  - `GET /v0/open-loops/{open_loop_id}`
  - `POST /v0/open-loops`
  - `POST /v0/open-loops/{open_loop_id}/status`
- Extended memory admission to accept optional `open_loop` payload and create an open loop during admission without regressing existing admission paths.
- Extended compiled context payload to include bounded, deterministic open-loop slice and open-loop summary when open loops exist.
- Updated `/memories` to show open-loop summary/list and selected detail with live + fixture-safe fallback behavior.
- Added/updated sprint-scoped migration, unit, integration, and web tests for the touched seams.
- Added explicit test coverage for:
  - successful `open -> dismissed` transition audit fields
  - cross-user `404` denial on open-loop detail/status mutation
- Updated `ARCHITECTURE.md` to document the shipped open-loop domain/API/compiler and `/memories` adoption.
- Fixed route model typing bug in open-loop status filter (`OpenLoopStatusFilter`) so FastAPI route registration remains valid.

## Incomplete Work
- None within sprint scope.

## Migration IDs And API Surface Deltas
- Migration added:
  - `20260323_0031_open_loop_backbone`
- Schema delta:
  - New `open_loops` table and indexes:
    - `open_loops_user_status_opened_idx`
    - `open_loops_user_memory_idx`
  - Enforced status domain + lifecycle consistency checks.
  - RLS enabled/forced with owner policy.
  - Granted `SELECT, INSERT, UPDATE` on `open_loops` to `alicebot_app`.
- API deltas:
  - New open-loop list/detail/create/status-update endpoints listed above.
  - `POST /v0/memories/admit` now accepts optional `open_loop` payload and may return created open-loop details.
  - `POST /v0/context/compile` context pack may include `open_loops` and `open_loop_summary` when candidate open loops exist.

## Files Changed
- `apps/api/alembic/versions/20260323_0031_open_loop_backbone.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/compiler.py`
- `ARCHITECTURE.md`
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/app/memories/page.tsx`
- `apps/web/app/memories/page.test.tsx`
- `tests/unit/test_20260323_0031_open_loop_backbone.py`
- `tests/unit/test_memory_store.py`
- `tests/unit/test_memory.py`
- `tests/unit/test_compiler.py`
- `tests/unit/test_main.py`
- `tests/integration/test_open_loops_api.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `PYTHONPATH=$PWD .venv/bin/pytest tests/unit/test_20260323_0031_open_loop_backbone.py tests/unit/test_memory_store.py tests/unit/test_memory.py tests/unit/test_compiler.py tests/unit/test_main.py`
- Outcome: `79 passed`

2. `cd apps/web && pnpm test -- lib/api.test.ts app/memories/page.test.tsx`
- Outcome: `24 passed`

3. `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_open_loops_api.py tests/integration/test_migrations.py`
- Outcome: `11 passed`
- Note: executed with escalated permissions to allow local Postgres connectivity from this environment.

## Blockers/Issues
- No unresolved blockers.
- Environment-specific constraint encountered: DB-backed integration tests required running outside sandbox network restrictions.

## Explicit Deferred Scope
- Resumption brief synthesis
- Background workers/scheduler automation
- Autonomous follow-up execution/reminder orchestration
- Phase 3 multi-agent runtime/profile routing

## Recommended Next Step
Proceed to sprint review with this open-loop backbone diff and test evidence, then merge once Control Tower approves scope and acceptance criteria.
