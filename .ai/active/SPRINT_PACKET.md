# Sprint Packet

## Sprint Title

Phase 10 Sprint 2 (P10-S2): Telegram Transport + Message Normalization

## Sprint Type

feature

## Sprint Reason

`P10-S1` established hosted identity, workspace bootstrap, device management, and preference foundations. `P10-S2` now adds the first chat surface by wiring Telegram transport, channel linking, normalized inbound message handling, deterministic workspace routing, and outbound delivery receipts on top of those shipped hosted-control seams.

Reference baseline marker: Phase 10 Sprint 1 (P10-S1): Identity + Workspace Bootstrap.

## Sprint Intent

- Telegram bot and webhook ingress
- Telegram link and unlink flow bound to hosted workspaces
- normalized inbound Telegram message contract
- deterministic workspace and thread routing for Telegram traffic
- outbound dispatcher and delivery receipts
- auditable idempotent message handling without widening into chat-native continuity behavior

## Git Instructions

- Branch Name: `codex/phase10-sprint-2-telegram-transport-normalization`
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
  - `P10-S1` hosted auth, workspace bootstrap, device management, preferences, beta cohorts, and feature flags
  - Phase 9 shipped scope is baseline truth, not sprint work
- Required now:
  - Telegram channel identity model and hosted link/unlink lifecycle
  - normalized inbound message shape shared by later chat continuity work
  - deterministic workspace and thread routing for Telegram traffic
  - outbound delivery dispatch with receipt recording
- Explicitly out of `P10-S2`:
  - changes to magic-link or hosted auth semantics beyond what Telegram linking requires to consume
  - new workspace bootstrap flows
  - chat-native capture, recall, resume, correction, or approval resolution behavior
  - daily brief generation or scheduler execution
  - support/admin dashboards
  - broad channel expansion beyond Telegram
  - launch hardening

## Exact APIs In Scope

- `POST /v1/channels/telegram/link/start`
- `POST /v1/channels/telegram/link/confirm`
- `POST /v1/channels/telegram/unlink`
- `GET /v1/channels/telegram/status`
- `POST /v1/channels/telegram/webhook`
- `GET /v1/channels/telegram/messages`
- `GET /v1/channels/telegram/threads`
- `POST /v1/channels/telegram/messages/{message_id}/dispatch`
- `GET /v1/channels/telegram/delivery-receipts`

## Exact Data Additions In Scope

- `channel_identities`
- `channel_link_challenges`
- `channel_messages`
- `channel_threads`
- `channel_delivery_receipts`
- `chat_intents`

## Exact Files And Modules In Scope

- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- new Telegram transport / channel routing / outbound delivery modules under `apps/api/src/alicebot_api/`
- API migrations under `apps/api/alembic/versions/`
- hosted Telegram-link and transport-status pages/components under `apps/web/app/` and `apps/web/components/`
- sprint-owned unit, integration, and web tests under `tests/` and `apps/web/app/**/*.test.tsx`
- sprint-owned documentation updates required to keep active control truth aligned

## Implementation Workstreams

### API And Persistence

- add Telegram channel identity, link challenge, message, thread, intent, and delivery-receipt contracts
- add webhook normalization and idempotency enforcement for inbound Telegram events
- add deterministic workspace resolution using shipped hosted user/workspace identity from `P10-S1`
- keep channel records additive to the hosted control plane and separate from continuity-object semantics

### Hosted UX

- add the minimal hosted settings flow needed to start, confirm, inspect, and remove Telegram linkage
- expose Telegram transport readiness and recent transport state only; do not imply chat continuity answers exist yet
- keep the surface narrow and operational, not launch-polish or support-dashboard work

### Verification

- add unit coverage for Telegram normalization, idempotency, link lifecycle, and routing helpers
- add integration coverage for all `P10-S2` endpoints, including duplicate webhook delivery, invalid link tokens, unlink/relink, and unknown-chat routing failures
- add web tests for Telegram link/status UX
- keep control-doc truth checks passing after packet and current-state updates

## Required Deliverables

- Telegram bot/webhook ingress
- Telegram link/unlink flow
- normalized inbound Telegram message contract
- deterministic workspace and thread routing
- outbound delivery dispatcher and receipt persistence
- hosted Telegram status/settings page

## Acceptance Criteria

- a hosted user with a `P10-S1` workspace can initiate and confirm Telegram linking without touching local tooling
- duplicate inbound Telegram webhook deliveries are handled idempotently
- inbound Telegram events are normalized into a stable internal contract with explicit workspace and thread routing
- outbound Telegram dispatch persists delivery receipts and failure posture deterministically
- `P10-S1` hosted identity/bootstrap semantics remain baseline truth and are not reopened as sprint work
- no `P10-S2` endpoint or screen claims that continuity capture/recall/approvals already operate in Telegram

## Required Verification Commands

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
- `pnpm --dir apps/web test`

## Review Evidence Requirements

- `BUILD_REPORT.md` must list the exact sprint-owned files changed and the exact command results above
- `REVIEW_REPORT.md` must grade against `P10-S2` specifically, not generic Phase 10 planning
- if local archive paths remain dirty, they must be called out explicitly as excluded from sprint merge scope

## Implementation Constraints

- do not fork continuity semantics between hosted surfaces and Alice Core
- keep OSS versus product boundaries explicit in docs and API naming
- preserve existing approval, provenance, and correction discipline
- do not widen `P10-S2` into chat-native continuity or notifications
- do not ship a scheduler in `P10-S2`
- reuse the shipped `P10-S1` session/workspace/device foundations instead of duplicating identity state
- prefer additive hosted-control-plane seams over invasive rewrites of shipped Phase 9 paths

## Exit Condition

`P10-S2` is complete when a hosted user can link Telegram to a shipped `P10-S1` workspace, Telegram inbound events are normalized and routed idempotently, outbound dispatches record delivery receipts, and the system is explicitly ready for `P10-S3` chat-native continuity work without reopening hosted identity/bootstrap scope.
