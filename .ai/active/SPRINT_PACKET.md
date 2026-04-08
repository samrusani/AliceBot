# Sprint Packet

## Sprint Title

Phase 10 Sprint 1 (P10-S1): Identity + Workspace Bootstrap

## Sprint Type

feature

## Sprint Reason

Phase 9 proved Alice can be installed, interoperate, remember, and resume deterministically. Phase 10 must make Alice usable without local-only developer setup. `P10-S1` establishes the hosted identity and workspace foundations required before Telegram, chat-native continuity, and scheduled briefs can ship.

## Sprint Intent

- hosted account and session model
- magic-link authentication only for the first hosted entry path
- workspace creation and bootstrap flow
- deterministic device linking and device management
- preferences and hosted settings foundation for timezone and future brief policy inputs
- beta cohort and feature-flag support

## Git Instructions

- Branch Name: `codex/phase10-sprint-1-identity-workspace-bootstrap`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR
- Merge Policy: squash merge only after review `PASS` and explicit approval

## Redundancy Guard

- Already shipped baseline:
  - Alice Core local-first runtime
  - deterministic CLI continuity contract
  - deterministic MCP transport
  - OpenClaw, Markdown, and ChatGPT importers
  - continuity engine, approvals, and eval harness
- Required now:
  - hosted identity, sessions, and device trust model
  - workspace bootstrap and preferences model
  - onboarding/settings foundations that later sprints can attach Telegram to
- Explicitly out of `P10-S1`:
  - passkeys or alternate auth methods beyond magic-link
  - Telegram transport
  - Telegram link/unlink UX
  - chat-native continuity flows
  - daily brief delivery
  - scheduler execution
  - backup or sync payload movement
  - admin/support dashboards
  - launch hardening

## Exact APIs In Scope

- `POST /v1/auth/magic-link/start`
- `POST /v1/auth/magic-link/verify`
- `POST /v1/auth/logout`
- `GET /v1/auth/session`
- `POST /v1/workspaces`
- `GET /v1/workspaces/current`
- `POST /v1/workspaces/bootstrap`
- `GET /v1/workspaces/bootstrap/status`
- `POST /v1/devices/link/start`
- `POST /v1/devices/link/confirm`
- `GET /v1/devices`
- `DELETE /v1/devices/{device_id}`
- `GET /v1/preferences`
- `PATCH /v1/preferences`

## Exact Data Additions In Scope

- `user_accounts`
- `auth_sessions`
- `magic_link_challenges`
- `devices`
- `device_link_challenges`
- `workspaces`
- `workspace_members`
- `user_preferences`
- `beta_cohorts`
- `feature_flags`

## Exact Files And Modules In Scope

- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- new hosted auth / workspace bootstrap / device / preferences modules under `apps/api/src/alicebot_api/`
- API migrations under `apps/api/alembic/versions/`
- hosted onboarding/settings pages and supporting UI under `apps/web/app/` and `apps/web/components/`
- sprint-owned unit, integration, and web tests under `tests/` and `apps/web/app/**/*.test.tsx`
- sprint-owned documentation updates required to keep active control truth aligned

## Implementation Workstreams

### API And Persistence

- add hosted account, session, workspace, device, and preference contracts
- add magic-link challenge lifecycle and authenticated session resolution
- add workspace bootstrap state and feature-flag visibility needed by hosted onboarding
- keep hosted identity/workspace records mapped cleanly onto the shipped Alice Core user/workspace semantics

### Hosted UX

- add the minimal hosted web flow needed to sign in, create or bootstrap a workspace, manage linked devices, and update preferences
- keep the surface narrow and utilitarian; this sprint is foundation, not launch polish
- show hosted bootstrap readiness only; do not imply Telegram is available yet

### Verification

- add unit coverage for auth, session, device, workspace bootstrap, and preference logic
- add integration coverage for all `P10-S1` endpoints, including invalid token, expired token, duplicate bootstrap, and revoked-device paths
- add web tests for the hosted onboarding/settings slice
- keep control-doc truth checks passing after packet and current-state updates

## Required Deliverables

- hosted account model
- magic-link auth
- device linking
- workspace bootstrap flow
- hosted settings page for timezone, brief-preference inputs, quiet-hours inputs, and device visibility
- beta cohort and feature-flag support

## Acceptance Criteria

- a new user can create a workspace without touching a repo
- a returning user can log in securely
- device linking works deterministically
- preferences persist and are exposed in hosted bootstrap/settings responses for later brief scheduling
- Phase 9 shipped scope is baseline truth, not sprint work
- hosted identity does not diverge from local workspace semantics
- no `P10-S1` screen or API claims that Telegram is already linked or available

## Required Verification Commands

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
- `pnpm --dir apps/web test`

## Review Evidence Requirements

- `BUILD_REPORT.md` must list the exact sprint-owned files changed and the exact command results above
- `REVIEW_REPORT.md` must grade against `P10-S1` specifically, not generic Phase 10 planning
- if local archive paths remain dirty, they must be called out explicitly as excluded from sprint merge scope

## Implementation Constraints

- do not fork continuity semantics between hosted surfaces and Alice Core
- keep OSS versus product boundaries explicit in docs and API naming
- preserve existing approval, provenance, and correction discipline
- do not widen Phase 10 scope to Telegram or notifications inside this sprint
- do not ship a scheduler in `P10-S1`; preference storage is enough
- do not represent Telegram channel state before `P10-S2`
- prefer additive hosted-control-plane seams over invasive rewrites of shipped Phase 9 paths

## Exit Condition

`P10-S1` is complete when a user can authenticate by magic link, create or bootstrap a workspace, link and revoke devices, persist hosted preferences, and land in a hosted bootstrap state that is explicitly ready for later Telegram linkage without reopening shipped Phase 9 scope.
