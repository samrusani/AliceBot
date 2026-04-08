# Current State

## Status

- Phase 9 is complete and shipped.
- Phase 10 planning is defined as Alice Connect.
- P10-S1 (Identity + Workspace Bootstrap) is the first execution sprint packet.
- `P10-S1` (Identity + Workspace Bootstrap) is shipped.
- `P10-S2` (Telegram Transport + Message Normalization) is shipped.
- `P10-S3` (Chat-Native Continuity + Approvals) is shipped.
- `P10-S4` (Daily Brief + Notifications + Scheduled Open-Loop Review) is shipped.
- `P10-S5` (Beta Hardening + Launch Readiness) is the active execution sprint packet.
- No launch-ready beta hardening surface is shipped yet.

## Canonical Baseline

- Shipped OSS surface: local-first runtime, deterministic CLI, deterministic MCP transport, OpenClaw/Markdown/ChatGPT importers, continuity engine, approvals, and evaluation harness.
- Canonical shipped docs remain under `docs/quickstart/`, `docs/integrations/`, `docs/examples/phase9-command-walkthrough.md`, `docs/release/`, `docs/runbooks/phase9-public-release-runbook.md`, and `eval/`.
- Repo runtime remains a modular monolith: FastAPI API/core, Next.js web app, workers, Postgres, Redis, and MinIO.

## Current Phase 10 Target

- hosted identity and workspace bootstrap
- device and channel linking
- Telegram-first chat access
- chat-native capture, recall, resume, correction, open-loop review, and approvals
- daily brief and notification loop
- beta rollout, support, and observability tooling

## Active Sprint Focus

- `P10-S1` shipped the hosted account/session foundations, workspace bootstrap, device management, preferences, and beta controls.
- `P10-S2` shipped Telegram transport, link/unlink flow, message normalization, routing, and delivery receipts.
- `P10-S3` shipped chat-native continuity behavior and approval handling on top of the shipped Telegram transport.
- `P10-S4` shipped daily brief delivery, notification policy, quiet hours, and scheduled waiting-for / stale-item prompts.
- `P10-S5` covers beta onboarding hardening, support/admin visibility, analytics/observability, rollout/rate-limit controls, and launch-facing product clarity.
- Phase 9 shipped scope is baseline truth and must not be reopened as sprint work.

## Active Constraints

- Preserve parity between local, CLI, MCP, and future Telegram behavior.
- Keep OSS versus hosted product scope explicit in docs and APIs.
- Archive planning history instead of carrying it in live control files.

## Archive Pointers

- Superseded planning docs: `docs/archive/planning/2026-04-08-context-compaction/README.md`
- Superseded control snapshots: `.ai/archive/planning/2026-04-08-context-compaction/`
