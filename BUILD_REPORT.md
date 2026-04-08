# BUILD_REPORT

## sprint objective
Implement `P10-S5` (Beta Hardening + Launch Readiness) from `.ai/active/SPRINT_PACKET.md`: hosted beta onboarding hardening, hosted admin/support visibility, hosted chat/scheduler telemetry and observability, rollout/rate-limit/abuse controls, and launch-facing hosted-vs-OSS clarity without reopening `P10-S1` through `P10-S4` feature seams.

## completed work
- Updated the active control/docs layer to reflect an active `P10-S5` execution sprint:
  - `.ai/active/SPRINT_PACKET.md`
  - `.ai/handoff/CURRENT_STATE.md`
  - `README.md`
- Added `20260409_0047` migration for:
  - `chat_telemetry` table.
  - additive support/rollout/rate-limit/incident evidence fields on `workspaces`, `channel_delivery_receipts`, and `daily_brief_jobs`.
  - hosted rollout/admin/rate-limit feature-flag seeds.
- Added hosted helper modules:
  - `hosted_rollout.py` (flag resolution/list/patch helpers).
  - `hosted_rate_limits.py` (deterministic hosted flow limit + abuse decisions).
  - `hosted_telemetry.py` (telemetry write/list/aggregate helpers).
  - `hosted_admin.py` (overview/workspace/delivery/incident/rate-limit admin queries).
- Extended API/config/contracts/store wiring for P10-S5 data and control-plane fields.
- Implemented exact in-scope admin APIs in `main.py`:
  - `GET /v1/admin/hosted/overview`
  - `GET /v1/admin/hosted/workspaces`
  - `GET /v1/admin/hosted/delivery-receipts`
  - `GET /v1/admin/hosted/incidents`
  - `GET /v1/admin/hosted/rollout-flags`
  - `PATCH /v1/admin/hosted/rollout-flags`
  - `GET /v1/admin/hosted/analytics`
  - `GET /v1/admin/hosted/rate-limits`
- Added rollout/rate-limit/abuse gating + telemetry recording on hosted chat/scheduler paths:
  - `/v1/channels/telegram/daily-brief/deliver`
  - `/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver`
  - `/v1/channels/telegram/messages/{message_id}/handle`
- Added onboarding failure-state hardening:
  - bootstrap conflict/not-found failures now persist workspace support/onboarding incident evidence.
- Added sprint-owned web surfaces/tests:
  - hosted admin page/panel + tests.
  - onboarding failure visibility copy + onboarding page test coverage.
  - shell/home hosted-admin navigation and launch-clarity updates.
- Added sprint-owned test coverage:
  - migration unit tests.
  - helper unit tests for rollout/rate-limit/telemetry aggregation behavior.
  - integration coverage for admin endpoints, rollout blocking, rate-limit/abuse blocking, and onboarding failure visibility.
- Fixed implementation issues discovered by tests:
  - escaped `%` in psycopg SQL `LIKE` clauses (`hosted_%%`).
  - resolved JSONB parameter typing in onboarding-failure persistence (`%s::text`).
  - adjusted hosted admin rollout patch behavior in web UI to include loaded cohort scope when toggling flags.
- Applied reviewer-driven hardening fixes:
  - restricted hosted admin endpoints to explicit operator authorization (`hosted_admin_read` + `hosted_admin_operator`).
  - added operator cohort (`p10-ops`) feature-flag seeding for deterministic admin access control.
  - prevented bootstrap not-found paths from mutating workspace support/incident evidence unless workspace membership was resolved.
  - constrained hosted rollout patching to hosted-prefixed flags and caller cohort scope.
  - added integration coverage for non-operator admin denial, hosted-only rollout patch validation, and cross-tenant onboarding-evidence safety.

## incomplete work
- None identified against the sprint packet acceptance criteria.

## files changed
- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `apps/api/alembic/versions/20260409_0047_phase10_beta_hardening_launch.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/hosted_admin.py`
- `apps/api/src/alicebot_api/hosted_rate_limits.py`
- `apps/api/src/alicebot_api/hosted_rollout.py`
- `apps/api/src/alicebot_api/hosted_telemetry.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/telegram_channels.py`
- `apps/api/src/alicebot_api/telegram_notifications.py`
- `apps/web/app/admin/page.test.tsx`
- `apps/web/app/admin/page.tsx`
- `apps/web/app/onboarding/page.test.tsx`
- `apps/web/app/page.tsx`
- `apps/web/components/app-shell.tsx`
- `apps/web/components/hosted-admin-panel.test.tsx`
- `apps/web/components/hosted-admin-panel.tsx`
- `apps/web/components/hosted-onboarding-panel.tsx`
- `tests/integration/test_phase10_beta_hardening_launch_api.py`
- `tests/unit/test_20260409_0047_phase10_beta_hardening_launch.py`
- `tests/unit/test_config.py`
- `tests/unit/test_phase10_beta_hardening_helpers.py`

## tests run
1. `python3 scripts/check_control_doc_truth.py`
- Result: PASS
- Output summary: verified `README.md`, `ROADMAP.md`, `.ai/active/SPRINT_PACKET.md`, `RULES.md`, `.ai/handoff/CURRENT_STATE.md`, and `docs/archive/planning/2026-04-08-context-compaction/README.md`.

2. `./.venv/bin/python -m pytest tests/unit tests/integration -q`
- Result: PASS
- Output summary: `1045 passed in 134.02s (0:02:14)`.

3. `pnpm --dir apps/web test`
- Result: PASS
- Output summary: `Test Files 62 passed (62)`, `Tests 199 passed (199)`.

(Additional focused preflight runs were executed during development and passed after fixes.)

## blockers/issues
- No remaining blockers.
- Resolved during implementation:
  - psycopg placeholder parsing conflict with SQL `LIKE 'hosted_%'`.
  - PostgreSQL parameter type ambiguity in onboarding failure JSONB update statement.

## recommended next step
Seek explicit Control Tower merge approval for `P10-S5`, using this branch head and the verification evidence above.
