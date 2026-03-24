# SPRINT_PACKET.md

## Sprint Title

Phase 3 Sprint 2: Web Agent Profile Adoption

## Sprint Type

feature

## Sprint Reason

Phase 3 Sprint 1 shipped and merged the backend profile backbone (`agent_profile_id` persistence, `/v0/agent-profiles`, profile metadata propagation). The operator shell still does not consume this surface, which creates a planning and usability gap for multi-agent deployment.

## Sprint Intent

Adopt shipped profile identity in the web shell so profile choice and visibility are explicit during thread creation and thread review, while keeping backend scope unchanged.

## Git Instructions

- Branch Name: `codex/phase3-sprint2-web-agent-profile-adoption`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- It directly consumes the backend capability that just shipped in Phase 3 Sprint 1.
- It is non-redundant: current web code does not call `GET /v0/agent-profiles` and does not use `agent_profile_id` on thread create/list/detail.
- It closes a concrete operator-facing gap before any model routing or orchestration expansion.

## Redundancy Guard

- Already shipped in Sprint 1 (do not re-implement): profile registry, migration, thread persistence, API validation, compile/response metadata propagation.
- Missing and required now: web client typing, profile fetch/read path, profile selection at thread create, and visible thread profile identity in chat surfaces.

## Design Truth

- Reuse shipped API seams as-is; no backend contract changes.
- Preserve current fixture/live fallback behavior across `/chat`.
- Keep deterministic default profile behavior explicit (`assistant_default`) when profile selection is unavailable.
- Keep UX bounded and calm: one selector on create, lightweight profile visibility in thread review surfaces.

## Exact Surfaces In Scope

- web API client contract adoption for `agent_profile_id` and `/v0/agent-profiles`
- chat-page live/fixture profile loading and fallback behavior
- thread create UI profile selection
- thread list/summary profile visibility
- targeted tests for all above seams

## Exact Files In Scope

- [api.ts](apps/web/lib/api.ts)
- [api.test.ts](apps/web/lib/api.test.ts)
- [fixtures.ts](apps/web/lib/fixtures.ts)
- [page.tsx](apps/web/app/chat/page.tsx)
- [page.test.tsx](apps/web/app/chat/page.test.tsx)
- [thread-create.tsx](apps/web/components/thread-create.tsx)
- [thread-create.test.tsx](apps/web/components/thread-create.test.tsx)
- [thread-list.tsx](apps/web/components/thread-list.tsx)
- [thread-list.test.tsx](apps/web/components/thread-list.test.tsx)
- [thread-summary.tsx](apps/web/components/thread-summary.tsx)
- [thread-summary.test.tsx](apps/web/components/thread-summary.test.tsx)
- [BUILD_REPORT.md](BUILD_REPORT.md)
- [REVIEW_REPORT.md](REVIEW_REPORT.md)
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md)

## In Scope

- Extend `ThreadItem` and `ThreadCreatePayload` in web API client with `agent_profile_id`.
- Add deterministic web API client types/helpers for profile registry:
  - `AgentProfileItem`
  - `AgentProfileListSummary`
  - `listAgentProfiles(apiBaseUrl)`
- Update `/chat` loading path to fetch profile registry in live mode and preserve fixture behavior when unavailable.
- Update thread create flow to allow profile selection and submit selected `agent_profile_id`.
- Show selected thread profile identity in thread review surfaces (`ThreadList` and `ThreadSummary`) without noisy UI expansion.
- Add/update tests covering:
  - request payloads include selected profile id
  - list/detail typing includes profile id
  - live profile fetch success/fallback behavior
  - profile identity rendering in list/summary

## Out of Scope

- backend schema/migration changes
- backend API contract changes for profile registry or thread create
- per-profile model-provider routing/switching
- profile CRUD endpoints
- external LLM provider integration
- auth model changes
- runner/worker orchestration changes

## Required Deliverables

- web API client + chat UI consume shipped profile seams end-to-end
- deterministic fallback behavior if profile registry is unavailable
- updated web tests for the profile adoption seam
- sprint build/review reports scoped to this sprint only

## Acceptance Criteria

- Thread create in live mode submits `agent_profile_id` along with `user_id` and `title`.
- Web thread data types and reads retain `agent_profile_id` from API responses.
- `/chat` reads `GET /v0/agent-profiles` in live mode and remains usable if that read fails.
- Thread list and selected-thread summary visibly show active profile identity.
- Fixture mode remains stable and deterministic with no regression to existing fallback paths.
- `npm --prefix apps/web run test:mvp:validation-matrix` passes.
- `python3 scripts/run_phase2_validation_matrix.py` remains PASS.
- No backend/API/migration scope enters this sprint.

## Implementation Constraints

- do not introduce new dependencies
- do not modify `apps/api` or migration files
- keep profile default deterministic (`assistant_default`) when selection data is unavailable
- preserve existing copy tone and visual containment in chat rail components

## Control Tower Task Cards

### Task 1: API Client + Fixture Contract Adoption
Owner: tooling operative  
Write scope:
- `apps/web/lib/api.ts`
- `apps/web/lib/api.test.ts`
- `apps/web/lib/fixtures.ts`

### Task 2: Chat Data Loading + Fallback
Owner: tooling operative  
Write scope:
- `apps/web/app/chat/page.tsx`
- `apps/web/app/chat/page.test.tsx`

### Task 3: Thread UI Adoption
Owner: tooling operative  
Write scope:
- `apps/web/components/thread-create.tsx`
- `apps/web/components/thread-create.test.tsx`
- `apps/web/components/thread-list.tsx`
- `apps/web/components/thread-list.test.tsx`
- `apps/web/components/thread-summary.tsx`
- `apps/web/components/thread-summary.test.tsx`

### Task 4: Integration Review
Owner: control tower  
Responsibilities:
- verify sprint stays web-adoption scoped
- verify no backend rework or profile-registry duplication
- verify validation matrix remains green

## Build Report Requirements

`BUILD_REPORT.md` must include:
- exact web contract/UI deltas for profile adoption
- exact verification command outcomes
- explicit deferred scope (routing, provider switching, orchestration)

## Review Focus

`REVIEW_REPORT.md` should verify:
- sprint stayed bounded to web profile adoption
- profile selection and visibility are correct and deterministic
- fallback behavior is explicit and non-breaking
- no hidden scope expansion

## Exit Condition

This sprint is complete when the shipped Phase 3 profile backbone is fully adopted in the web chat operator surface (selection + visibility + tests) with deterministic fallback behavior and all required validation gates green.
