# BUILD_REPORT.md

## Sprint Objective
Adopt Phase 3 Sprint 1 profile seams in the web operator shell by wiring `agent_profile_id` and `/v0/agent-profiles` into chat loading, thread creation, and thread review visibility while keeping backend scope unchanged.

## Completed Work
- Web API contract adoption (`apps/web/lib/api.ts`):
  - Extended `ThreadItem` with `agent_profile_id`.
  - Extended `ThreadCreatePayload` with `agent_profile_id`.
  - Added `DEFAULT_AGENT_PROFILE_ID` constant (`assistant_default`).
  - Added profile registry types:
    - `AgentProfileItem`
    - `AgentProfileListSummary`
  - Added `listAgentProfiles(apiBaseUrl)` for `GET /v0/agent-profiles`.
- API/contract tests (`apps/web/lib/api.test.ts`):
  - Verified thread create payload now includes `agent_profile_id`.
  - Verified list/detail reads retain `agent_profile_id`.
  - Verified profile registry read path hits `/v0/agent-profiles` and returns deterministic ids.
- Fixture contract adoption (`apps/web/lib/fixtures.ts`):
  - Added `agent_profile_id` to thread fixtures.
  - Added deterministic profile fixtures (`assistant_default`, `coach_default`).
  - Ensured fixture thread creation defaults to `assistant_default`.
- Chat loading + fallback (`apps/web/app/chat/page.tsx`):
  - Added live profile registry load via `listAgentProfiles`.
  - Added deterministic fallback to fixture profile registry when live read fails.
  - Normalized thread profile ids to explicit default (`assistant_default`) when missing.
  - Passed profile registry into thread create/list/summary surfaces.
- Chat page tests (`apps/web/app/chat/page.test.tsx`):
  - Added profile registry mock coverage.
  - Added explicit test for live profile read failure fallback while `/chat` remains usable.
- Thread create UI adoption (`apps/web/components/thread-create.tsx`):
  - Added profile selector to thread creation form.
  - Submitted selected `agent_profile_id` with `user_id` and `title`.
  - Preserved deterministic `assistant_default` fallback when profile list is unavailable.
- Thread create tests (`apps/web/components/thread-create.test.tsx`):
  - Verified selected profile id is sent in create payload.
  - Verified deterministic default payload uses `assistant_default` without profile data.
- Thread list visibility (`apps/web/components/thread-list.tsx`):
  - Added visible profile badge per thread row.
- Thread list tests (`apps/web/components/thread-list.test.tsx`):
  - Verified profile identity rendering in thread rows.
- Thread summary visibility (`apps/web/components/thread-summary.tsx`):
  - Added visible selected-thread profile identity (badge + summary field).
- Thread summary tests (`apps/web/components/thread-summary.test.tsx`):
  - Verified profile identity rendering in selected-thread summary.

## Incomplete Work
- None within sprint scope.

## Files Changed
- `.ai/active/SPRINT_PACKET.md` (pre-existing sprint packet update in workspace; not modified for implementation logic)
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/lib/fixtures.ts`
- `apps/web/app/chat/page.tsx`
- `apps/web/app/chat/page.test.tsx`
- `apps/web/components/thread-create.tsx`
- `apps/web/components/thread-create.test.tsx`
- `apps/web/components/thread-list.tsx`
- `apps/web/components/thread-list.test.tsx`
- `apps/web/components/thread-summary.tsx`
- `apps/web/components/thread-summary.test.tsx`
- `BUILD_REPORT.md`

## Tests Run
1. `npm --prefix apps/web run test -- lib/api.test.ts app/chat/page.test.tsx components/thread-create.test.tsx components/thread-list.test.tsx components/thread-summary.test.tsx`
- Outcome: PASS (`5` files, `36` tests).

2. `npm --prefix apps/web run test:mvp:validation-matrix`
- Outcome: PASS (`13` files, `65` tests).

3. `python3 scripts/run_phase2_validation_matrix.py`
- Initial sandbox run: blocked on local Postgres access (`localhost:5432 Operation not permitted`).
- Elevated rerun outcome: PASS.
- Gate summary:
  - `control_doc_truth: PASS`
  - `gate_contract_tests: PASS`
  - `readiness_gates: PASS`
  - `backend_integration_matrix: PASS`
  - `web_validation_matrix: PASS`

## Blockers/Issues
- Sandbox permissions blocked DB-backed validation matrix execution on first run.
- Resolved by rerunning with elevated local access; no code blocker remained.

## Explicit Deferred Scope
- Per-profile model routing or provider switching.
- Worker/runner orchestration changes.
- Backend profile CRUD expansion.

## Recommended Next Step
1. Hand off to Control Tower review focused on: profile selection correctness, thread profile visibility, and fallback determinism under live profile registry failure.
