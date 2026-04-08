# Roadmap

## Planning Basis

- Phase 9 is shipped baseline truth, not roadmap work.
- Phase 10 is the next delivery phase: Alice Connect.

## Phase 10 Milestones

### P10-S1: Identity + Workspace Bootstrap

- hosted account and session model
- workspace creation and bootstrap flow
- device linking
- user preferences and settings foundation
- beta cohort and feature-flag support

### P10-S2: Telegram Transport + Message Normalization

- Telegram bot and webhook ingress
- Telegram link/unlink flow
- normalized inbound message contract
- outbound dispatcher and delivery receipts
- workspace/thread routing for chat traffic

### P10-S3: Chat-Native Continuity + Approvals

- capture, recall, resume, correction, and open-loop review in Telegram
- deterministic routing to best-fit continuity context
- approval prompts and resolution in chat
- provenance-backed answers and correction uptake

### P10-S4: Daily Brief + Notifications + Open-Loop Review

- daily brief generation and delivery scheduler
- quiet hours and notification controls
- waiting-for and stale-item prompts
- one-tap open-loop review actions in chat

### P10-S5: Beta Hardening + Launch Readiness

- beta onboarding funnel
- admin/support tooling
- analytics and observability for chat flows
- rate limiting, abuse controls, and rollout flags
- launch assets and hosted-vs-OSS product clarity

## Sequencing Rules

- Do not start Telegram transport before identity and workspace bootstrap are stable.
- Do not add chat-native continuity before transport and routing are deterministic.
- Do not turn on scheduled briefs until chat continuity and notification preferences are trustworthy.
- Treat beta hardening as a launch gate, not optional polish.

## Phase 10 Exit

Phase 10 is done when a non-technical beta user can onboard, use Alice through Telegram, capture and recall continuity, receive a useful daily brief, approve simple actions in chat, and do so without semantic drift from Alice Core.

## Roadmap Guardrails

- Keep this file future-facing; completed work and sprint history belong in archive.
- Do not rewrite shipped Phase 9 capabilities as future milestones.
- Preserve the OSS baseline while layering product capabilities on top of it.

## Archived Planning

- Historical planning and superseded control docs: `docs/archive/planning/2026-04-08-context-compaction/README.md`
