# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 5: Profile-Scoped Memory and Context Isolation

## Sprint Type

feature

## Sprint Reason

Sprint 4 stabilizes durable profile identity in the registry and thread FK binding. The next non-redundant gap is isolation: context compilation still reads user memories globally, so different agent profiles can share memory context unintentionally. Current `main` does not yet include that Sprint 4 registry baseline, so this sprint carries the minimal prerequisite registry artifacts forward to keep the migration/runtime chain coherent.

## Sprint Intent

Bind memory selection to active thread profile by adding profile attribution on memory records and enforcing profile-scoped context retrieval, while preserving backward-compatible defaults.

## Git Instructions

- Branch Name: `codex/phase3-sprint5-profile-memory-context-isolation`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the next non-redundant seam after profile identity + registry.
- It closes cross-profile memory bleed risk in `POST /v0/context/compile` and `POST /v0/responses`.
- It establishes a durable boundary needed before profile-specific policy/provider routing.

## Redundancy Guard

- Already shipped in Sprint 1: thread-level profile identity + metadata propagation.
- Already shipped in Sprint 2: web profile selection/visibility.
- Already shipped in Sprint 3: profile-aware response prompting.
- Required Sprint 4 baseline not yet present on `main` and carried here as prerequisite only: durable profile registry migration/runtime wiring.
- Missing and required now: profile-scoped memory attribution and profile-bound context retrieval.

## Design Truth

- Memory rows carry explicit `agent_profile_id` bound to the profile registry.
- Memory retrieval for compile/response uses the selected thread profile boundary.
- Existing behavior defaults safely to `assistant_default` where profile attribution is omitted.
- API envelopes remain stable; profile fields may be additive where necessary.

## Exact Surfaces In Scope

- memory schema/profile attribution migration
- store-layer memory read/write updates with profile filtering
- compile/response memory retrieval path updated to active thread profile scope
- prerequisite profile-registry baseline carry-forward required by migration/runtime chain
- integration and unit tests for isolation and backward-compatible defaults

## Exact Files In Scope

- [store.py](apps/api/src/alicebot_api/store.py)
- [compiler.py](apps/api/src/alicebot_api/compiler.py)
- [main.py](apps/api/src/alicebot_api/main.py)
- [contracts.py](apps/api/src/alicebot_api/contracts.py)
- [memory.py](apps/api/src/alicebot_api/memory.py)
- [phase3_profiles.py](apps/api/src/alicebot_api/phase3_profiles.py)
- [20260324_0033_agent_profile_registry.py](apps/api/alembic/versions/20260324_0033_agent_profile_registry.py)
- [20260324_0034_memory_agent_profile_scope.py](apps/api/alembic/versions/20260324_0034_memory_agent_profile_scope.py)
- [test_20260324_0033_agent_profile_registry.py](tests/unit/test_20260324_0033_agent_profile_registry.py)
- [test_20260324_0034_memory_agent_profile_scope.py](tests/unit/test_20260324_0034_memory_agent_profile_scope.py)
- [test_memory.py](tests/unit/test_memory.py)
- [test_memory_store.py](tests/unit/test_memory_store.py)
- [test_context_compile.py](tests/integration/test_context_compile.py)
- [test_memory_review_api.py](tests/integration/test_memory_review_api.py)
- [test_continuity_api.py](tests/integration/test_continuity_api.py)
- [test_responses_api.py](tests/integration/test_responses_api.py)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Add `agent_profile_id` to `memories` with:
  - non-null default `assistant_default`
  - FK to `agent_profiles(id)`
  - deterministic index for scoped retrieval (`user_id`, `agent_profile_id`, `updated_at`, `created_at`, `id`)
- Backfill existing memory rows to `assistant_default` via migration default semantics.
- Update memory create/upsert flows so new/updated memory rows preserve explicit profile attribution.
- Update context compilation path to fetch memories scoped to active thread profile.
- Keep existing response/context metadata profile propagation behavior unchanged.
- Carry forward required Sprint 4 registry foundation (`0033` migration + profile-registry runtime wiring/tests) without adding CRUD/provider/orchestration scope.
- Add unit migration tests for upgrade/rollback and profile FK/default invariants.
- Add integration coverage proving:
  - compile for `assistant_default` and `coach_default` threads returns profile-scoped memory slices
  - response generation inherits scoped compile behavior
  - existing default path remains deterministic when profile is omitted

## Out of Scope

- profile CRUD endpoints
- per-profile provider/model routing
- policy/tooling profile scoping
- web UI changes
- connector/auth/orchestration expansion

## Required Deliverables

- memory profile-scope migration and store wiring
- compile/response memory retrieval isolation by active profile
- passing unit/integration evidence for profile-scoped memory behavior
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- Memory rows are profile-attributed and FK-bound to registry profiles.
- Compile for a thread includes only memories from that thread’s active profile domain.
- `/v0/responses` remains backward-compatible while using profile-scoped compile behavior.
- Default behavior remains deterministic (`assistant_default`) when profile attribution is omitted.
- `./.venv/bin/python -m pytest tests/unit/test_20260324_0034_memory_agent_profile_scope.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_context_compile.py tests/integration/test_responses_api.py tests/integration/test_memory_review_api.py -q` passes.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No provider/policy/orchestration scope expansion enters this sprint.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing response and compile payload contracts
- keep migration reversible and forward-safe
- keep scoped retrieval ordering deterministic with existing memory ordering rules

## Control Tower Task Cards

### Task 1: Memory Scope Migration + Store Wiring
Owner: tooling operative  
Write scope:
- `apps/api/alembic/versions/20260324_0033_agent_profile_registry.py`
- `apps/api/alembic/versions/20260324_0034_memory_agent_profile_scope.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/compiler.py`
- `apps/api/src/alicebot_api/memory.py`
- `apps/api/src/alicebot_api/phase3_profiles.py`

### Task 2: Verification
Owner: tooling operative  
Write scope:
- `tests/unit/test_20260324_0033_agent_profile_registry.py`
- `tests/unit/test_20260324_0034_memory_agent_profile_scope.py`
- `tests/unit/test_memory.py`
- `tests/unit/test_memory_store.py`
- `tests/integration/test_context_compile.py`
- `tests/integration/test_continuity_api.py`
- `tests/integration/test_memory_review_api.py`
- `tests/integration/test_responses_api.py`
- `apps/api/src/alicebot_api/main.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays memory-scope isolation scoped
- verify no provider/policy/orchestration expansion
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact memory-profile-scope migration and compile isolation deltas
- exact verification command outcomes
- explicit deferred scope (policy/provider/orchestration/profile CRUD)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to memory/context profile isolation
- memory profile attribution and scoped compile behavior are correct and deterministic
- API behavior remains backward-compatible
- no hidden scope expansion

## Exit Condition

This sprint is complete when context memory selection is profile-scoped and deterministic for the active thread profile, with migration/test evidence and all validation gates green.
