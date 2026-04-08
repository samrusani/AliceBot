# Sprint Packet

## Sprint Title

Phase 10 Sprint 4 (P10-S4): Daily Brief + Notifications + Scheduled Open-Loop Review

Historical baseline marker: Phase 10 Sprint 1 (P10-S1): Identity + Workspace Bootstrap.

## Sprint Type

feature

## Sprint Reason

`P10-S1` shipped hosted identity, workspace bootstrap, device management, and preferences. `P10-S2` shipped Telegram transport, channel linking, normalized inbound messages, routing, and delivery receipts. `P10-S3` shipped chat-native continuity and approval handling. `P10-S4` now adds the scheduled habit loop: daily brief generation, notification policy enforcement, quiet-hours-respecting delivery, and scheduled prompts for waiting-for and stale open-loop review.

Reference baseline markers: `P10-S1` Identity + Workspace Bootstrap, `P10-S2` Telegram Transport + Message Normalization, and `P10-S3` Chat-Native Continuity + Approvals.

## Sprint Intent

- daily brief generation and Telegram delivery
- notification policy enforcement including quiet hours and user preferences
- scheduled waiting-for and stale-item prompts
- scheduled open-loop review nudges that reuse shipped `P10-S3` review actions
- deterministic job and delivery evidence without widening into launch tooling

## Git Instructions

- Branch Name: `codex/phase10-sprint-4-daily-brief-notifications`
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
  - `P10-S3` Telegram chat-native continuity, open-loop review, and approval handling
  - Phase 9 shipped scope is baseline truth, not sprint work
- Required now:
  - daily brief compilation from durable continuity state
  - scheduler execution and due-job selection
  - notification policy enforcement using timezone, quiet hours, and brief preferences
  - scheduled waiting-for and stale open-loop prompts delivered through shipped Telegram transport
- Explicitly out of `P10-S4`:
  - new hosted auth, session, or workspace bootstrap flows
  - Telegram transport or link/unlink contract redesign
  - generic chat-native capture/recall/resume/correction behavior already shipped in `P10-S3`
  - support/admin dashboards
  - broad channel expansion beyond Telegram
  - launch hardening

## Exact APIs In Scope

- `GET /v1/channels/telegram/daily-brief`
- `POST /v1/channels/telegram/daily-brief/deliver`
- `GET /v1/channels/telegram/notification-preferences`
- `PATCH /v1/channels/telegram/notification-preferences`
- `GET /v1/channels/telegram/open-loop-prompts`
- `POST /v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver`
- `GET /v1/channels/telegram/delivery-receipts`
- `GET /v1/channels/telegram/scheduler/jobs`

## Exact Data Additions In Scope

- `continuity_briefs`
- `daily_brief_jobs`
- `notification_subscriptions`
- additive scheduled-delivery fields required on `channel_delivery_receipts` and related scheduler/job records

## Exact Files And Modules In Scope

- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/telegram_channels.py`
- `apps/api/src/alicebot_api/chief_of_staff.py`
- `apps/api/src/alicebot_api/continuity_open_loops.py`
- new daily-brief / notification scheduling helpers under `apps/api/src/alicebot_api/`
- API migrations under `apps/api/alembic/versions/`
- hosted brief-preference / notification-status pages or components under `apps/web/app/` and `apps/web/components/`
- sprint-owned unit, integration, and web tests under `tests/` and `apps/web/app/**/*.test.tsx`
- sprint-owned documentation updates required to keep active control truth aligned

## Implementation Workstreams

### API And Persistence

- add brief/job/subscription contracts and persistence for scheduled delivery
- add due-job selection and delivery bookkeeping that reuses shipped Telegram delivery seams
- persist scheduled prompt and brief outcomes without creating a parallel chat history model

### Delivery Behavior

- compile useful daily brief payloads from durable continuity and chief-of-staff state
- enforce timezone, quiet hours, and notification preferences before delivery
- deliver scheduled waiting-for and stale-item prompts that point back into shipped `P10-S3` open-loop review handling

### Verification

- add unit coverage for brief compilation, quiet-hours gating, and due-job selection
- add integration coverage for all `P10-S4` endpoints, including quiet-hours suppression, disabled notifications, repeated-job idempotency, and stale-item prompt delivery
- add web tests for brief-preference / notification-status UX if sprint-owned UI changes are introduced
- keep control-doc truth checks passing after packet and current-state updates

## Required Deliverables

- daily brief compiler and Telegram delivery path
- notification preference and quiet-hours enforcement
- scheduled waiting-for and stale-item prompts
- persisted brief/job/subscription evidence
- status surface for brief and notification posture

## Acceptance Criteria

- a linked Telegram user with notifications enabled can receive a useful daily brief generated from durable stored state
- quiet hours and notification preference settings suppress or defer delivery deterministically
- waiting-for and stale open-loop prompts are generated and delivered without reopening generic open-loop review semantics already shipped in `P10-S3`
- delivery jobs and receipts are persisted with deterministic status evidence
- `P10-S1`, `P10-S2`, and `P10-S3` semantics remain baseline truth and are not reopened as sprint work
- no `P10-S4` endpoint or screen claims that beta admin/support tooling or launch hardening is already active

## Required Verification Commands

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
- `pnpm --dir apps/web test`

## Review Evidence Requirements

- `BUILD_REPORT.md` must list the exact sprint-owned files changed and the exact command results above
- `REVIEW_REPORT.md` must grade against `P10-S4` specifically, not generic Phase 10 planning
- if local archive paths remain dirty, they must be called out explicitly as excluded from sprint merge scope

## Implementation Constraints

- do not fork continuity semantics between hosted surfaces and Alice Core
- keep OSS versus product boundaries explicit in docs and API naming
- preserve existing approval, provenance, and correction discipline
- do not widen `P10-S4` into beta admin tooling or launch work
- reuse the shipped `P10-S1`, `P10-S2`, and `P10-S3` identity/workspace/channel/chat foundations instead of duplicating control-plane state
- do not re-implement generic open-loop review actions that already shipped in `P10-S3`; this sprint only adds scheduled prompting and brief delivery
- prefer additive hosted-control-plane seams over invasive rewrites of shipped Phase 9 paths

## Exit Condition

`P10-S4` is complete when a linked Telegram user can receive a daily brief and scheduled waiting-for/stale prompts under deterministic quiet-hours and notification-policy enforcement, with persisted job and delivery evidence and no reopening of hosted identity, transport, or generic chat-continuity scope.
