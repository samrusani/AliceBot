# Sprint Packet

## Sprint Title

Phase 10 Sprint 5 (P10-S5): Beta Hardening + Launch Readiness

Historical baseline marker: Phase 10 Sprint 1 (P10-S1): Identity + Workspace Bootstrap.

## Sprint Type

feature

## Sprint Reason

`P10-S1` shipped hosted identity, workspace bootstrap, device management, and preferences. `P10-S2` shipped Telegram transport, channel linking, normalized inbound messages, routing, and delivery receipts. `P10-S3` shipped chat-native continuity and approval handling. `P10-S4` shipped daily brief delivery, notification policy, quiet hours, and scheduled prompts. `P10-S5` is the launch gate sprint: beta onboarding hardening, support/admin visibility, analytics and observability for hosted chat flows, rate limiting and abuse controls, rollout flags, and launch-facing product clarity.

Reference baseline markers: `P10-S1` Identity + Workspace Bootstrap, `P10-S2` Telegram Transport + Message Normalization, `P10-S3` Chat-Native Continuity + Approvals, and `P10-S4` Daily Brief + Notifications + Scheduled Open-Loop Review.

## Sprint Intent

- beta onboarding funnel hardening
- support and admin visibility for hosted Telegram operations
- analytics and observability for hosted chat and scheduled delivery flows
- rate limiting, abuse controls, and rollout-flag enforcement
- launch assets and hosted-vs-OSS product clarity without widening feature scope

## Git Instructions

- Branch Name: `codex/phase10-sprint-5-beta-hardening-launch`
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
  - `P10-S4` Telegram daily briefs, notification policy, quiet hours, and scheduled prompts
  - Phase 9 shipped scope is baseline truth, not sprint work
- Required now:
  - beta onboarding readiness and failure-state hardening
  - support/admin surfaces for hosted operational inspection
  - analytics, observability, rate limiting, and abuse controls
  - rollout-flag enforcement and launch-facing documentation clarity
- Explicitly out of `P10-S5`:
  - new hosted auth, session, or workspace bootstrap flows
  - Telegram transport or link/unlink contract redesign
  - generic chat-native capture/recall/resume/correction behavior already shipped in `P10-S3`
  - daily brief and notification feature redesign already shipped in `P10-S4`
  - broad channel expansion beyond Telegram
  - new product-surface scope beyond the Phase 10 plan

## Exact APIs In Scope

- `GET /v1/admin/hosted/overview`
- `GET /v1/admin/hosted/workspaces`
- `GET /v1/admin/hosted/delivery-receipts`
- `GET /v1/admin/hosted/incidents`
- `GET /v1/admin/hosted/rollout-flags`
- `PATCH /v1/admin/hosted/rollout-flags`
- `GET /v1/admin/hosted/analytics`
- `GET /v1/admin/hosted/rate-limits`

## Exact Data Additions In Scope

- `chat_telemetry`
- additive rollout, support, incident, and rate-limit evidence fields required on hosted delivery / job / workspace records

## Exact Files And Modules In Scope

- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/telegram_channels.py`
- `apps/api/src/alicebot_api/telegram_notifications.py`
- new hosted admin / telemetry / rollout helpers under `apps/api/src/alicebot_api/`
- API migrations under `apps/api/alembic/versions/`
- hosted admin / support / onboarding-status pages or components under `apps/web/app/` and `apps/web/components/`
- sprint-owned unit, integration, and web tests under `tests/` and `apps/web/app/**/*.test.tsx`
- sprint-owned launch-facing docs and product-clarity updates required to keep control truth aligned

## Implementation Workstreams

### API And Persistence

- add telemetry, rollout, incident, and rate-limit contracts needed for hosted beta operations
- add support/admin query surfaces that summarize hosted workspace, delivery, and failure posture without mutating shipped product behavior
- persist launch-gate evidence without creating a second truth source for the underlying continuity flows

### Hardening And Launch

- harden onboarding and hosted flow failure handling around the already shipped Phase 10 surfaces
- enforce rollout flags and abuse/rate-limit protections on hosted chat and scheduled delivery paths
- make hosted-vs-OSS product boundaries explicit in launch-facing docs and surfaces

### Verification

- add unit coverage for rollout gating, rate limiting, and telemetry aggregation helpers
- add integration coverage for admin/support endpoints, rollout-flag enforcement, abuse/rate-limit behavior, and hosted failure-state visibility
- add web tests for sprint-owned admin/support or onboarding-status UX
- keep control-doc truth checks passing after packet and current-state updates

## Required Deliverables

- beta onboarding hardening
- hosted admin/support visibility
- analytics and observability for hosted chat and scheduled delivery flows
- rate limiting, abuse controls, and rollout flags
- launch-facing docs and OSS-versus-hosted product clarity

## Acceptance Criteria

- hosted beta operators can inspect workspace, delivery, incident, and rollout posture without touching the database directly
- hosted chat and scheduled-delivery paths enforce rollout and abuse/rate-limit controls deterministically
- onboarding and hosted failure states are visible enough to support a beta user without reopening shipped feature seams
- launch-facing docs and surfaces clearly distinguish OSS Alice Core from hosted Alice Connect beta scope
- `P10-S1` through `P10-S4` semantics remain baseline truth and are not reopened as sprint work
- no `P10-S5` work widens scope beyond beta hardening and launch readiness

## Required Verification Commands

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
- `pnpm --dir apps/web test`

## Review Evidence Requirements

- `BUILD_REPORT.md` must list the exact sprint-owned files changed and the exact command results above
- `REVIEW_REPORT.md` must grade against `P10-S5` specifically, not generic Phase 10 planning
- if local archive paths remain dirty, they must be called out explicitly as excluded from sprint merge scope

## Implementation Constraints

- do not fork continuity semantics between hosted surfaces and Alice Core
- keep OSS versus product boundaries explicit in docs and API naming
- preserve existing approval, provenance, and correction discipline
- do not widen `P10-S5` into new feature-surface scope beyond hardening and launch readiness
- reuse the shipped `P10-S1` through `P10-S4` identity/workspace/channel/chat/scheduling foundations instead of duplicating control-plane state
- do not re-implement generic continuity, approval, or notification behavior that already shipped in earlier sprints
- prefer additive hosted-control-plane seams over invasive rewrites of shipped Phase 9 paths

## Exit Condition

`P10-S5` is complete when hosted beta operations have enough onboarding hardening, support/admin visibility, telemetry, rollout control, abuse protection, and launch-facing documentation clarity to treat Phase 10 as a launch-ready beta without reopening shipped identity, transport, chat-continuity, or notification scope.
