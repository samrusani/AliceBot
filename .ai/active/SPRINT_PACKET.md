# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 7: Profile-Scoped Model Routing

## Sprint Type

feature

## Sprint Reason

Sprint 6 established profile-scoped policy evaluation and routing. The next non-redundant gap is runtime model selection: response generation still uses one global model configuration from environment settings instead of active profile-specific routing.

## Sprint Intent

Route `/v0/responses` model selection by active thread profile using deterministic profile runtime configuration, while preserving safe fallback to current global settings.

## Git Instructions

- Branch Name: `codex/phase3-sprint7-profile-model-routing`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It is the next non-redundant seam after identity, memory isolation, and policy isolation.
- It closes the remaining shared-runtime gap where all profiles currently invoke the same model config.
- It enables true separate-agent runtime posture without introducing orchestration breadth.

## Redundancy Guard

- Already shipped in Sprint 1: thread-level profile identity + metadata propagation.
- Already shipped in Sprint 2: web profile selection/visibility.
- Already shipped in Sprint 3: profile-aware response prompting.
- Already shipped in Sprint 4: durable profile registry + thread FK.
- Already shipped in Sprint 5: profile-scoped memory/context isolation.
- Already shipped in Sprint 6: profile-scoped policy evaluation/routing.
- Missing and required now: profile-scoped model/provider selection at response invocation.

## Design Truth

- Profile records can carry runtime model config (`model_provider`, `model_name`).
- Response generation resolves runtime model config from active thread profile.
- Fallback remains deterministic:
  - if profile runtime config is absent, use existing global settings.
- Keep provider surface bounded; no new external connector/provider wiring in this sprint.

## Exact Surfaces In Scope

- profile runtime config schema + registry read wiring
- response generation model selection by active profile
- additive API/profile contracts exposing runtime config where needed
- unit/integration tests for routing + fallback determinism

## Exact Files In Scope

- [store.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/store.py)
- [main.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/main.py)
- [contracts.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/contracts.py)
- [phase3_profiles.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/phase3_profiles.py)
- [response_generation.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/response_generation.py)
- [20260325_0036_agent_profile_model_runtime.py](/Users/samirusani/Desktop/Codex/AliceBot/apps/api/alembic/versions/20260325_0036_agent_profile_model_runtime.py)
- [test_20260325_0036_agent_profile_model_runtime.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_20260325_0036_agent_profile_model_runtime.py)
- [test_response_generation.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_response_generation.py)
- [test_continuity_api.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_continuity_api.py)
- [test_responses_api.py](/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_responses_api.py)
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md)
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md)

## In Scope

- Add runtime model columns to `agent_profiles` (nullable for backward compatibility):
  - `model_provider`
  - `model_name`
- Seed deterministic runtime config for shipped profiles:
  - `assistant_default`
  - `coach_default`
- Update profile registry read contracts to expose runtime config fields.
- Update `/v0/responses` path to:
  - resolve active thread profile
  - select provider/model from profile runtime config when present
  - fallback to `Settings.model_provider` / `Settings.model_name` when absent
- Preserve existing error behavior, event shape, and trace contracts.
- Add migration tests for schema + seed/runtime invariants.
- Add unit tests for runtime selection/fallback logic.
- Add integration tests proving:
  - profile-specific model selection is used in response invocation
  - fallback to global settings works deterministically when profile runtime is unset
  - profile metadata and backward-compatible response envelope remain stable

## Out of Scope

- profile CRUD endpoints
- introducing new provider integrations or secret handling changes
- policy/tooling redesign
- web UI changes
- connector/auth/orchestration expansion

## Required Deliverables

- profile runtime model migration and registry wiring
- response-generation profile model routing with deterministic fallback
- passing unit/integration evidence for profile-scoped model selection
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- Agent profiles persist deterministic runtime model config fields.
- `/v0/responses` uses profile runtime model config for the active thread profile.
- If profile runtime model config is absent, fallback to global settings remains deterministic.
- Existing `/v0/responses` response envelope remains backward-compatible.
- `./.venv/bin/python -m pytest tests/unit/test_20260325_0036_agent_profile_model_runtime.py -q` passes.
- `./.venv/bin/python -m pytest tests/unit/test_response_generation.py -q` passes.
- `./.venv/bin/python -m pytest tests/integration/test_continuity_api.py tests/integration/test_responses_api.py -q` passes.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No new-provider/orchestration scope expansion enters this sprint.

## Implementation Constraints

- do not introduce new dependencies
- preserve existing response/trace payload contracts (additive fields only where necessary)
- keep migration reversible and forward-safe
- keep profile list ordering deterministic (`id_asc`)

## Control Tower Task Cards

### Task 1: Profile Runtime Migration + Store Wiring
Owner: tooling operative  
Write scope:
- `apps/api/alembic/versions/20260325_0036_agent_profile_model_runtime.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/phase3_profiles.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/response_generation.py`

### Task 2: Verification
Owner: tooling operative  
Write scope:
- `tests/unit/test_20260325_0036_agent_profile_model_runtime.py`
- `tests/unit/test_response_generation.py`
- `tests/integration/test_continuity_api.py`
- `tests/integration/test_responses_api.py`

### Task 3: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays profile-model-routing scoped
- verify no new-provider/orchestration expansion
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact profile-runtime migration and response-model-routing deltas
- exact verification command outcomes
- explicit deferred scope (new providers, orchestration, profile CRUD)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to profile model routing
- profile runtime model selection and fallback behavior are deterministic and correct
- API behavior remains backward-compatible
- no hidden scope expansion

## Exit Condition

This sprint is complete when response model selection is profile-scoped and deterministic for the active thread profile, with migration/test evidence and all validation gates green.
