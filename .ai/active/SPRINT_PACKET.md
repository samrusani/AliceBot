# Sprint Packet

## Sprint Title

Phase 10 Sprint 3 (P10-S3): Chat-Native Continuity + Approvals

Historical baseline marker: Phase 10 Sprint 1 (P10-S1): Identity + Workspace Bootstrap.

## Sprint Type

feature

## Sprint Reason

`P10-S1` shipped hosted identity, workspace bootstrap, device management, and preferences. `P10-S2` shipped Telegram transport, channel linking, normalized inbound messages, routing, and delivery receipts. `P10-S3` now turns that transport into a usable continuity surface by routing Telegram chats into capture, recall, resume, correction, open-loop review, and approval resolution on top of the shipped Alice Core semantics.

Reference baseline markers: `P10-S1` Identity + Workspace Bootstrap and `P10-S2` Telegram Transport + Message Normalization.

## Sprint Intent

- Telegram-native capture, recall, resume, correction, and open-loop review flows
- deterministic routing from normalized Telegram messages into the right continuity action
- approval prompts and approval resolution in Telegram
- provenance-backed replies and correction-aware answer behavior
- reuse of shipped transport seams without widening into scheduling or brief delivery

## Git Instructions

- Branch Name: `codex/phase10-sprint-3-chat-continuity-approvals`
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
  - `P10-S2` Telegram transport, link/unlink, normalization, routing, and delivery receipts
  - Phase 9 shipped scope is baseline truth, not sprint work
- Required now:
  - intent routing from normalized Telegram messages into continuity and approval actions
  - Telegram-native continuity answers and correction-aware reply posture
  - open-loop review actions and approval resolution in chat
  - provenance-backed outbound responses built from durable stored truth
- Explicitly out of `P10-S3`:
  - new hosted auth, session, or workspace bootstrap flows
  - Telegram transport or link/unlink contract redesign
  - daily brief generation or scheduler execution
  - support/admin dashboards
  - broad channel expansion beyond Telegram
  - launch hardening

## Exact APIs In Scope

- `POST /v1/channels/telegram/messages/{message_id}/handle`
- `GET /v1/channels/telegram/messages/{message_id}/result`
- `GET /v1/channels/telegram/recall`
- `GET /v1/channels/telegram/resume`
- `GET /v1/channels/telegram/open-loops`
- `POST /v1/channels/telegram/open-loops/{open_loop_id}/review-action`
- `GET /v1/channels/telegram/approvals`
- `POST /v1/channels/telegram/approvals/{approval_id}/approve`
- `POST /v1/channels/telegram/approvals/{approval_id}/reject`

## Exact Data Additions In Scope

- `approval_challenges`
- `open_loop_reviews`
- additive Telegram message intent/result fields required to persist routed continuity and approval outcomes

## Exact Files And Modules In Scope

- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/telegram_channels.py`
- `apps/api/src/alicebot_api/continuity_capture.py`
- `apps/api/src/alicebot_api/continuity_recall.py`
- `apps/api/src/alicebot_api/continuity_resumption.py`
- `apps/api/src/alicebot_api/continuity_review.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- `apps/api/src/alicebot_api/approvals.py`
- new Telegram continuity orchestration helpers under `apps/api/src/alicebot_api/` if needed
- API migrations under `apps/api/alembic/versions/`
- hosted Telegram chat-status / approval-status pages or components under `apps/web/app/` and `apps/web/components/`
- sprint-owned unit, integration, and web tests under `tests/` and `apps/web/app/**/*.test.tsx`
- sprint-owned documentation updates required to keep active control truth aligned

## Implementation Workstreams

### API And Persistence

- add intent classification and action routing from shipped normalized Telegram messages into continuity and approval handlers
- persist Telegram message handling results, approval challenge state, and open-loop review actions without forking the underlying Alice Core objects
- reuse shipped `P10-S2` channel/thread routing and delivery-receipt posture rather than creating a parallel chat pipeline

### Chat Behavior

- support capture, recall, resume, correction, and open-loop review from Telegram messages
- support approval prompts and approval resolution in Telegram using the existing approval discipline
- ensure replies remain provenance-backed and correction-aware rather than transcript-summarized

### Verification

- add unit coverage for Telegram intent routing, continuity result formatting, and approval action helpers
- add integration coverage for all `P10-S3` endpoints, including wrong-intent routing, correction uptake, open-loop review actions, and approval approve/reject flows
- add web tests for Telegram continuity / approval status UX if sprint-owned UI changes are introduced
- keep control-doc truth checks passing after packet and current-state updates

## Required Deliverables

- Telegram chat handling for capture, recall, resume, correction, and open-loop review
- deterministic intent routing from shipped normalized Telegram messages
- approval prompts and approve/reject handling in Telegram
- provenance-backed Telegram replies
- persisted handling results that later daily-brief work can build on

## Acceptance Criteria

- a linked Telegram user can capture a new continuity item and receive a deterministic acknowledgment in chat
- a linked Telegram user can ask recall and resume questions and receive provenance-backed answers from durable stored truth
- correction messages update subsequent Telegram answers in a correction-aware way
- a linked Telegram user can review open loops and resolve approval prompts in chat
- `P10-S1` and `P10-S2` hosted/transport semantics remain baseline truth and are not reopened as sprint work
- no `P10-S3` endpoint or screen claims that scheduled daily briefs or notification loops are already active

## Required Verification Commands

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
- `pnpm --dir apps/web test`

## Review Evidence Requirements

- `BUILD_REPORT.md` must list the exact sprint-owned files changed and the exact command results above
- `REVIEW_REPORT.md` must grade against `P10-S3` specifically, not generic Phase 10 planning
- if local archive paths remain dirty, they must be called out explicitly as excluded from sprint merge scope

## Implementation Constraints

- do not fork continuity semantics between hosted surfaces and Alice Core
- keep OSS versus product boundaries explicit in docs and API naming
- preserve existing approval, provenance, and correction discipline
- do not widen `P10-S3` into daily briefs, notification scheduling, or launch tooling
- do not ship a scheduler in `P10-S3`
- reuse the shipped `P10-S1` and `P10-S2` identity/workspace/channel foundations instead of duplicating control-plane state
- prefer additive hosted-control-plane seams over invasive rewrites of shipped Phase 9 paths

## Exit Condition

`P10-S3` is complete when a linked Telegram user can use capture, recall, resume, correction, open-loop review, and approval resolution against the shipped Alice Core semantics through the shipped Telegram transport, with provenance-backed replies and no reopening of hosted identity or transport scope.
