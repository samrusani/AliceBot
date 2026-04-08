# REVIEW_REPORT

## verdict
PASS

## criteria met
- All `P10-S1` in-scope hosted APIs are implemented and exercised:
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
- Hosted challenge-token security posture is improved: magic-link and device-link tokens are now hashed at rest (`challenge_token_hash`) in migration and runtime lookup logic.
- New/returning user paths, workspace bootstrap, deterministic device linking/revocation, and hosted preferences persistence are validated via integration tests.
- Telegram remains explicitly out of scope in API/UI (`telegram_state: not_available_in_p10_s1` and matching web copy).
- Control docs and planning surfaces are aligned to an active `P10-S1` execution sprint rather than the prior idle post-Phase-9 placeholder:
  - `.ai/active/SPRINT_PACKET.md`
  - `.ai/handoff/CURRENT_STATE.md`
  - `README.md`
  - `ROADMAP.md`
  - `RULES.md`
- Required verification commands passed in this re-review:
  - `python3 scripts/check_control_doc_truth.py` -> PASS
  - `./.venv/bin/python -m pytest tests/unit tests/integration -q` -> `990 passed`
  - `pnpm --dir apps/web test` -> `59 passed` test files, `194 passed` tests

## criteria missed
- None identified for `P10-S1` acceptance criteria.

## quality issues
- No blocking quality issues found after fixes.

## regression risks
- Low.
- Main residual risk is ordinary follow-on scope pressure: future Telegram and scheduler sprints must reuse these hosted identity/workspace seams instead of bypassing them.

## docs issues
- No blocking docs issues for sprint acceptance.
- Optional follow-up: add concise API reference docs for the new hosted `v1` endpoints if not already planned.

## should anything be added to RULES.md?
- Optional hardening rule worth keeping: one-time auth challenge secrets must be stored hashed at rest.

## should anything update ARCHITECTURE.md?
- Optional: add a brief hosted auth token lifecycle note (issue, hash-at-rest, verify by hash, TTL/revocation).

## recommended next action
1. Ready for Control Tower merge approval under policy.
2. After merge, open `P10-S2` only on top of these hosted identity/workspace/device foundations without widening scope early.
