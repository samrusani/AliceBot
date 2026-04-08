# BUILD_REPORT

## sprint objective
Implement **Phase 10 Sprint 2 (P10-S2): Telegram Transport + Message Normalization** exactly within sprint scope: Telegram link/unlink lifecycle, webhook ingress normalization/idempotency, deterministic workspace/thread routing, outbound dispatch, and delivery receipts.

## completed work
- Updated the active control/docs layer to reflect an active `P10-S2` execution sprint:
  - `.ai/active/SPRINT_PACKET.md`
  - `.ai/handoff/CURRENT_STATE.md`
  - `README.md`
- Added Telegram transport persistence migration with all in-scope tables:
  - `channel_identities`
  - `channel_link_challenges`
  - `channel_messages`
  - `channel_threads`
  - `channel_delivery_receipts`
  - `chat_intents`
- Added new API transport module:
  - `apps/api/src/alicebot_api/telegram_channels.py`
  - Includes link challenge lifecycle, webhook normalization, idempotent inbound ingestion, routing/thread resolution, unlink/relink behavior, outbound dispatch, and receipt serialization.
- Added all in-scope `P10-S2` endpoints in `main.py`:
  - `POST /v1/channels/telegram/link/start`
  - `POST /v1/channels/telegram/link/confirm`
  - `POST /v1/channels/telegram/unlink`
  - `GET /v1/channels/telegram/status`
  - `POST /v1/channels/telegram/webhook`
  - `GET /v1/channels/telegram/messages`
  - `GET /v1/channels/telegram/threads`
  - `POST /v1/channels/telegram/messages/{message_id}/dispatch`
  - `GET /v1/channels/telegram/delivery-receipts`
- Added Telegram runtime config in `config.py`:
  - `TELEGRAM_LINK_TTL_SECONDS`
  - `TELEGRAM_BOT_USERNAME`
  - `TELEGRAM_WEBHOOK_SECRET`
  - `TELEGRAM_BOT_TOKEN`
- Added sprint-scoped contract/store additions for channel identity/challenge/message/thread/intent/receipt records.
- Updated hosted settings UI copy for `P10-S2` Telegram transport/status scope and preserved explicit non-claim boundary for chat-native continuity behavior.
- Added sprint tests:
  - Unit: Telegram normalization/idempotency helpers.
  - Unit: new migration wiring coverage.
  - Integration: full `P10-S2` endpoint flow including duplicate webhook delivery, invalid link token, unlink/relink, unknown-chat routing, dispatch, and receipt listing.
  - Web: Telegram link/status UX copy coverage.
- Applied minimal control-doc marker updates required for `scripts/check_control_doc_truth.py` to pass with active `P10-S2` packet context.

## incomplete work
- None identified within `P10-S2` sprint packet scope.

## files changed
- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `README.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`
- `apps/api/alembic/versions/20260408_0044_phase10_telegram_transport.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/hosted_workspace.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/telegram_channels.py`
- `tests/integration/test_phase10_identity_workspace_bootstrap_api.py`
- `tests/integration/test_phase10_telegram_transport_api.py`
- `tests/unit/test_20260408_0044_phase10_telegram_transport.py`
- `tests/unit/test_config.py`
- `tests/unit/test_telegram_channels.py`
- `apps/web/app/settings/page.tsx`
- `apps/web/app/settings/page.test.tsx`
- `apps/web/components/hosted-settings-panel.tsx`
- `apps/web/components/hosted-settings-panel.test.tsx`

## tests run
Required verification commands and exact results:
- `python3 scripts/check_control_doc_truth.py`
  - `Control-doc truth check: PASS`
  - verified: `README.md`, `ROADMAP.md`, `.ai/active/SPRINT_PACKET.md`, `RULES.md`, `.ai/handoff/CURRENT_STATE.md`, `docs/archive/planning/2026-04-08-context-compaction/README.md`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - `1003 passed in 122.94s (0:02:02)`
- `pnpm --dir apps/web test`
  - `Test Files 60 passed (60)`
  - `Tests 196 passed (196)`

Additional focused check run during implementation:
- `./.venv/bin/python -m pytest tests/unit/test_telegram_channels.py tests/unit/test_20260408_0044_phase10_telegram_transport.py tests/integration/test_phase10_telegram_transport_api.py -q`
  - `11 passed in 2.40s`

## blockers/issues
- No implementation blockers.

## recommended next step
Seek explicit Control Tower merge approval for `P10-S2`, using this branch head and the verification evidence above.
