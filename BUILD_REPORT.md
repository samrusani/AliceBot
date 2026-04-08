# BUILD_REPORT

## sprint objective
Implement **Phase 10 Sprint 1 (P10-S1): Identity + Workspace Bootstrap** with hosted magic-link auth, hosted workspace bootstrap, deterministic device linking/management, hosted preferences persistence, and beta cohort/feature-flag foundations without expanding into Telegram delivery/linking scope.

## completed work
- Updated the active control/docs layer to reflect an active `P10-S1` execution sprint instead of the post-Phase-9 idle placeholder:
  - `.ai/active/SPRINT_PACKET.md`
  - `.ai/handoff/CURRENT_STATE.md`
  - `README.md`
  - `ROADMAP.md`
  - `RULES.md`
  - `ARCHITECTURE.md`
  - `PRODUCT_BRIEF.md`
  - `ARCHIVE_RECOMMENDATIONS.md`
  - `RECOMMENDED_ADRS.md`
- Added hosted control-plane migration for all sprint data additions:
  - `user_accounts`, `auth_sessions`, `magic_link_challenges`, `devices`, `device_link_challenges`, `workspaces`, `workspace_members`, `user_preferences`, `beta_cohorts`, `feature_flags`.
- Implemented new hosted modules under API source:
  - `hosted_auth.py` (magic-link lifecycle, session issuance/validation/logout, feature-flag resolution)
  - `hosted_workspace.py` (workspace creation/current selection/bootstrap status/complete)
  - `hosted_devices.py` (device-link challenge start/confirm, list, revoke + session revocation)
  - `hosted_preferences.py` (timezone validation + preference get/patch persistence)
- Added full `v1` API surface in `main.py`:
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
- Added config knobs for hosted TTL controls:
  - `MAGIC_LINK_TTL_SECONDS`, `AUTH_SESSION_TTL_SECONDS`, `DEVICE_LINK_TTL_SECONDS`.
- Added hosted contract types in `contracts.py` for account/session/workspace/device/preferences records and statuses.
- Added hosted onboarding/settings web slice:
  - new routes `/onboarding` and `/settings`
  - supporting components for onboarding and settings posture
  - navigation + overview route-card updates
  - explicit messaging that Telegram linkage is not available in `P10-S1`.
- Added verification coverage:
  - integration coverage for all new `v1` flows, including invalid token, expired token, duplicate bootstrap, and revoked-device session path
  - unit coverage for hosted helper logic and migration wiring
  - web tests for onboarding/settings pages.

## incomplete work
- None within `P10-S1` acceptance scope.

## files changed
Sprint-owned files changed:
- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `ARCHIVE_RECOMMENDATIONS.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `RECOMMENDED_ADRS.md`
- `ROADMAP.md`
- `RULES.md`
- `scripts/check_control_doc_truth.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `apps/api/alembic/versions/20260408_0043_phase10_identity_workspace_bootstrap.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/hosted_auth.py`
- `apps/api/src/alicebot_api/hosted_workspace.py`
- `apps/api/src/alicebot_api/hosted_devices.py`
- `apps/api/src/alicebot_api/hosted_preferences.py`
- `tests/integration/test_phase10_identity_workspace_bootstrap_api.py`
- `tests/unit/test_20260408_0043_phase10_identity_workspace_bootstrap.py`
- `tests/unit/test_phase10_hosted_modules.py`
- `apps/web/app/onboarding/page.tsx`
- `apps/web/app/onboarding/page.test.tsx`
- `apps/web/app/settings/page.tsx`
- `apps/web/app/settings/page.test.tsx`
- `apps/web/components/hosted-onboarding-panel.tsx`
- `apps/web/components/hosted-settings-panel.tsx`
- `apps/web/components/app-shell.tsx`
- `apps/web/app/page.tsx`

## tests run
Required verification commands and results:
- `python3 scripts/check_control_doc_truth.py`
  - `Control-doc truth check: PASS`
  - Verified: `README.md`, `ROADMAP.md`, `.ai/active/SPRINT_PACKET.md`, `RULES.md`, `.ai/handoff/CURRENT_STATE.md`, `docs/archive/planning/2026-04-08-context-compaction/README.md`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - `990 passed in 108.75s (0:01:48)`
- `pnpm --dir apps/web test`
  - `Test Files 59 passed (59)`
  - `Tests 194 passed (194)`

Additional focused checks run during implementation:
- `./.venv/bin/python -m pytest tests/unit/test_phase10_hosted_modules.py tests/unit/test_20260408_0043_phase10_identity_workspace_bootstrap.py tests/integration/test_phase10_identity_workspace_bootstrap_api.py -q`
  - `9 passed in 1.37s`

## blockers/issues
- No implementation blockers.
- One transient web test assertion ambiguity (duplicate text match) was resolved by tightening the selector to role-based heading assertions.

## recommended next step
Seek explicit Control Tower merge approval for `P10-S1`, using this branch head and the verification evidence above.
