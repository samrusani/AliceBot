# BUILD_REPORT.md

## Sprint Objective
Implement Phase 2 Sprint 2 typed memory backbone end-to-end (schema, store, contracts/API, compiler serialization, and `/memories` UI) without expanding into open-loop workflows, resumption generation, worker orchestration, or Phase 3 runtime.

## Completed Work
- Added typed memory metadata fields across persistence, API serialization, and compiler output:
  - `memory_type`
  - `confidence`
  - `salience`
  - `confirmation_status`
  - `valid_from`
  - `valid_to`
  - `last_confirmed_at`
- Added deterministic validation for `memory_type` in admission flow (`400` with explicit allowed values).
- Preserved append-only revision guarantees; metadata changes are now threaded through admission/update paths and remain auditable in candidate payloads when provided.
- Linked migration lineage to the current Alembic head (`down_revision = 20260319_0030`) so upgrade runs remain single-head and deterministic.
- Extended memory store SQL read/write paths and typed row contracts to include new metadata fields.
- Extended `AdmitMemoryRequest`/`MemoryCandidateInput` handling for optional typed metadata plus temporal-range validation.
- Extended compiler memory serialization to include typed metadata in context-pack memories when present.
- Added `/memories` web route with:
  - list/detail split review surface
  - typed metadata visibility
  - safe fallbacks for missing metadata
- Added/updated sprint-scoped tests for migration, store/API behavior, compiler outputs, and web API/page seams.

## Incomplete Work
- None within sprint scope.

## Migration IDs And API Surface Deltas
- Migration added:
  - `20260323_0030_typed_memory_backbone`
- Schema delta (`memories`):
  - Added columns: `memory_type`, `confidence`, `salience`, `confirmation_status`, `valid_from`, `valid_to`, `last_confirmed_at`
  - Added constraints: memory type domain, confirmation status domain, confidence/salience range checks, temporal range check
  - Added index: `memories_user_type_updated_idx`
- API deltas:
  - `POST /v0/memories/admit`: accepts optional typed metadata fields and rejects invalid `memory_type` deterministically.
  - `GET /v0/memories`, `GET /v0/memories/{memory_id}`, `GET /v0/memories/review-queue`: now return typed metadata fields when available.
  - Context compiler memory serialization includes typed metadata fields when present.

## Files Changed
- `apps/api/alembic/versions/20260323_0030_typed_memory_backbone.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/compiler.py`
- `apps/web/lib/api.ts`
- `apps/web/app/memories/page.tsx`
- `apps/web/app/memories/page.test.tsx`
- `tests/unit/test_20260323_0030_typed_memory_backbone.py`
- `tests/unit/test_memory_store.py`
- `tests/unit/test_entity_store.py`
- `tests/unit/test_memory.py`
- `tests/integration/test_memory_admission.py`
- `tests/integration/test_memory_review_api.py`
- `tests/integration/test_context_compile.py`
- `tests/integration/test_migrations.py`
- `.ai/active/SPRINT_PACKET.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Tests Run
1. `PYTHONPATH=$PWD .venv/bin/pytest tests/unit/test_20260323_0030_typed_memory_backbone.py tests/unit/test_memory_store.py tests/unit/test_entity_store.py tests/unit/test_memory.py tests/unit/test_compiler.py tests/unit/test_main.py`
- Outcome: `73 passed`

2. `PYTHONPATH=$PWD .venv/bin/pytest tests/unit/test_explicit_preferences.py`
- Outcome: `8 passed`

3. `cd apps/web && pnpm test -- lib/api.test.ts app/memories/page.test.tsx`
- Outcome: `23 passed`

4. `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_memory_admission.py`
- Outcome (DB-enabled verification): `5 passed`

5. `PYTHONPATH=$PWD .venv/bin/pytest tests/integration/test_memory_review_api.py tests/integration/test_context_compile.py tests/integration/test_migrations.py`
- Outcome (DB-enabled verification): `25 passed`

## Blockers/Issues
- No blocking issues remain for sprint-scope acceptance.

## Explicit Deferred Scope
- Open loops/workflows
- Resumption brief generation
- Worker activation/orchestration
- Phase 3 runtime/profile implementation

## Recommended Next Step
Proceed with sprint PR review and merge using this sprint-scoped diff and the verified test evidence.
