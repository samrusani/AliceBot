# Architecture

## System Overview

Phase 10 keeps the shipped Phase 9 modular monolith and adds a hosted product layer on top of the same continuity core. Alice Core remains authoritative for continuity objects, recall, resume, corrections, approvals, and provenance-backed retrieval. Hosted identity, Telegram, and scheduling orchestrate access to that core; they do not create a second semantics stack.

## Technical Stack

- API and core runtime: Python 3.12 + FastAPI under `apps/api/src/alicebot_api`
- Web app: Next.js 15 + React 19 under `apps/web`
- Background/task surface: `workers`
- Primary data store: Postgres with `pgvector`
- Local support services: Redis and MinIO via `docker-compose.yml`
- Packaging: `alice-core` in `pyproject.toml`
- Test surface: pytest, Vitest, and the Phase 9 evaluation harness

## Runtime Boundaries

### Core Data Plane

Owns:

- continuity capture and revision persistence
- typed continuity objects and memory revisions
- recall and resumption compilation
- entities, edges, and open loops
- approvals and audit traces
- CLI and MCP semantics
- importer provenance and deterministic dedupe

### Hosted Control Plane

Owns:

- user accounts and auth sessions
- devices and trust levels
- workspaces and bootstrap state
- channel bindings
- user preferences and notification policy
- beta cohorts and feature flags
- telemetry and support tooling

### Surface Layer

- local API and CLI
- MCP server
- Telegram adapter and chat routing layer
- web onboarding/settings/admin surfaces
- brief and notification scheduler

## Phase 10 Core Flows

### Onboarding

1. User authenticates with a hosted session.
2. User creates or boots a workspace.
3. Device and channel bindings are established.
4. Preferences and import choices are stored.
5. Alice generates a first brief against the existing continuity core.

### Inbound Chat

1. Telegram webhook receives an inbound message.
2. The message is normalized into a common channel message contract.
3. Routing resolves workspace, actor, and best-fit continuity context.
4. Core capture/recall/resume/correction logic executes.
5. A reply is dispatched back through the same channel thread.

### Approval

1. Core logic emits an approval request.
2. Chat surface presents approve/reject/context actions.
3. Approval resolution writes back to the same approval and audit objects used by other surfaces.

### Daily Brief

1. Scheduler selects workspaces due for delivery.
2. Brief compiler builds a deterministic summary from continuity state.
3. Notification policy and quiet hours are applied.
4. Delivery receipts and failures are recorded for support tooling.

## Data Model Summary

### Existing Baseline Objects

- continuity capture events
- typed continuity objects
- correction events and revisions
- open loops and brief-ready summaries
- import provenance with explicit `source_kind`

### Phase 10 Additions

Control-plane tables:

- `user_accounts`
- `auth_sessions`
- `devices`
- `workspaces`
- `workspace_members`
- `user_preferences`
- `beta_cohorts`
- `feature_flags`

Channel and scheduler tables:

- `channel_identities`
- `channel_messages`
- `channel_threads`
- `channel_delivery_receipts`
- `chat_intents`
- `continuity_briefs`
- `approval_challenges`
- `daily_brief_jobs`
- `notification_subscriptions`
- `open_loop_reviews`
- `chat_telemetry`

## Security and Governance

- Postgres remains the system of record.
- Hosted identity and channel access add to, but do not bypass, existing approval and provenance discipline.
- Append-only continuity and correction history stay intact.
- Device linking, channel binding, and session expiry are explicit control-plane concerns.
- Consequential actions remain approval-bounded even when initiated from chat.
- Opt-in backup/sync must preserve user isolation and encryption boundaries.

## Deployment

### Shipped Baseline

Canonical local startup path remains:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
APP_RELOAD=false ./scripts/api_dev.sh
```

### Phase 10 Production Additions

- hosted auth/session endpoints
- public webhook ingress for Telegram
- scheduler/worker execution for briefs and notifications
- support/admin visibility for beta operations

## Testing

Existing quality gates remain:

```bash
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
./scripts/run_phase9_eval.sh --report-path eval/reports/phase9_eval_latest.json
```

Phase 10 adds targeted verification for:

- auth and workspace bootstrap
- device and channel linking
- idempotent webhook ingest and outbound delivery
- cross-surface parity between local, CLI, MCP, and Telegram
- daily brief scheduling, quiet hours, and failure handling
- support telemetry and rollout controls

## Architecture Constraints

- Phase 10 must not fork semantics between local, CLI, MCP, and Telegram.
- Telegram is another surface on the same core objects, not a separate assistant stack.
- Control-plane additions must not rewrite shipped Alice Core contracts.
- Do not expand connector breadth beyond Telegram in Phase 10 without an explicit roadmap change.
- Keep docs clear about what is shipped OSS baseline versus planned beta surface.

## Historical Traceability

Superseded rollout planning and control snapshots live under `docs/archive/planning/2026-04-08-context-compaction/README.md`.
