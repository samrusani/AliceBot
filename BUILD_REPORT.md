# BUILD_REPORT.md

## Sprint Objective
Phase 3 Sprint 5: Profile-Scoped Memory and Context Isolation.

Implement durable profile attribution on memory rows and enforce profile-scoped memory behavior across compile/response and admission paths, while preserving deterministic `assistant_default` fallback when attribution is omitted.

## Completed Work
- Carried forward required Sprint 4 registry baseline not yet present on `main`:
- migration `20260324_0033_agent_profile_registry`
- DB-backed profile registry runtime wiring in `phase3_profiles.py`
- continuity integration coverage updates that match DB-backed registry behavior
- Added migration `20260324_0034_memory_agent_profile_scope`:
- Added `memories.agent_profile_id text NOT NULL DEFAULT 'assistant_default'`.
- Added FK `memories_agent_profile_id_fkey` -> `agent_profiles(id)`.
- Replaced global memory-key uniqueness with profile-scoped uniqueness:
- dropped `memories_user_id_memory_key_key`
- added `memories_user_profile_memory_key_key` on `(user_id, agent_profile_id, memory_key)`
- Added deterministic retrieval index `memories_user_profile_updated_created_id_idx` on `(user_id, agent_profile_id, updated_at, created_at, id)`.
- Hardened downgrade safety:
- before restoring `UNIQUE (user_id, memory_key)`, downgrade deterministically rewrites only duplicate cross-profile keys (ranked suffix strategy) so rollback does not fail on post-upgrade cross-profile duplicates.
- Updated store wiring:
- `create_memory(..., agent_profile_id='assistant_default')`
- `get_memory_by_key_and_profile(memory_key, agent_profile_id)`
- `list_context_memories_for_profile(agent_profile_id=...)`
- `retrieve_semantic_memory_matches_for_profile(..., agent_profile_id=...)`
- Updated memory admission write path (`memory.py`):
- derives profile domain from `source_event_ids` -> source event threads -> thread `agent_profile_id`
- validates optional explicit `agent_profile_id` (when provided) and enforces consistency with derived source profile
- rejects mixed-profile `source_event_ids` deterministically
- scopes upsert lookup by profile (`memory_key + agent_profile_id`)
- persists new rows with resolved profile attribution
- includes resolved profile in revision candidate payload
- Updated API contract/request plumbing:
- `MemoryCandidateInput` supports optional `agent_profile_id`
- `/v0/memories/admit` request supports optional `agent_profile_id` and passes through
- Kept compile/response profile-scoped read behavior in place and verified:
- compile memory retrieval remains bounded to active thread profile
- semantic retrieval in compile remains bounded to active thread profile
- Added/updated tests:
- `tests/unit/test_20260324_0034_memory_agent_profile_scope.py` (migration invariants including profile-scoped uniqueness)
- `tests/unit/test_memory.py` (admission profile-scoped upsert + mixed-profile rejection)
- `tests/unit/test_memory_store.py` (store SQL/params expectations after profile column exposure)
- `tests/integration/test_memory_review_api.py`:
- same `memory_key` admitted from assistant/coach threads persists separately by profile
- mixed-profile source event set is rejected
- explicit `agent_profile_id` mismatch is rejected
- unknown `agent_profile_id` is rejected
- Existing compile/response isolation tests continue passing

## Incomplete Work
- None within sprint objective.

## Files Changed
- `apps/api/alembic/versions/20260324_0033_agent_profile_registry.py`
- `apps/api/alembic/versions/20260324_0034_memory_agent_profile_scope.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/compiler.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/phase3_profiles.py`
- `tests/unit/test_20260324_0033_agent_profile_registry.py`
- `tests/unit/test_20260324_0034_memory_agent_profile_scope.py`
- `tests/unit/test_memory.py`
- `tests/unit/test_memory_store.py`
- `tests/integration/test_context_compile.py`
- `tests/integration/test_continuity_api.py`
- `tests/integration/test_memory_review_api.py`
- `tests/integration/test_responses_api.py`
- `.ai/active/SPRINT_PACKET.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## Scope Hygiene
- Sprint branch includes Sprint 5 memory-scope work plus the minimal Sprint 4 registry baseline required for migration/runtime coherence on a `main` base that does not yet contain Sprint 4.
- No additional scope expansion entered beyond that prerequisite baseline and Sprint 5 targets.

## Tests Run
1. `./.venv/bin/python -m pytest tests/unit/test_20260324_0033_agent_profile_registry.py -q`
- PASS (`3 passed`)

2. `./.venv/bin/python -m pytest tests/unit/test_20260324_0034_memory_agent_profile_scope.py -q`
- PASS (`4 passed`)

3. `./.venv/bin/python -m pytest tests/unit/test_memory.py -q`
- PASS (`23 passed`)

4. `./.venv/bin/python -m pytest tests/unit/test_memory_store.py tests/unit/test_20260324_0034_memory_agent_profile_scope.py -q`
- PASS (`10 passed`)

5. `./.venv/bin/python -m pytest tests/integration/test_continuity_api.py -q`
- PASS (`7 passed`)

6. `./.venv/bin/python -m pytest tests/integration/test_context_compile.py tests/integration/test_responses_api.py tests/integration/test_memory_review_api.py -q`
- PASS (`30 passed`)

7. `python3 scripts/run_phase2_validation_matrix.py`
- PASS
- `control_doc_truth: PASS`
- `gate_contract_tests: PASS`
- `readiness_gates: PASS`
- `backend_integration_matrix: PASS`
- `web_validation_matrix: PASS`

## Blockers/Issues
- Sandbox networking blocked localhost Postgres access for DB-backed tests.
- Resolved by running required DB-backed commands with elevated permissions.

## Recommended Next Step
1. Control Tower final review and merge for Phase 3 Sprint 5 with emphasis on migration rollout sequencing and profile-domain admission semantics.
