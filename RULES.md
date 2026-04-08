# Rules

## Baseline Truth

- Treat shipped Phase 9 capability as baseline truth, not as future roadmap scope.
- Do not rewrite shipped Phase 9 capabilities as future roadmap items.
- Do not rewrite shipped Alice Core, CLI, MCP, importer, or eval-harness behavior as aspirational work.

## Product Scope

- Alice remains a continuity product first, not a broad autonomous platform.
- Hosted product work must preserve a clear OSS-to-product boundary.
- Telegram is the only new user-facing channel in Phase 10 unless the roadmap changes.
- Do not add browser automation, broad connector expansion, enterprise collaboration, or new vertical agents under Phase 10.

## Architecture

- Phase 10 must not fork semantics between local, CLI, MCP, and Telegram.
- Telegram is another surface on the same core objects.
- Control plane owns identity, devices, channel bindings, preferences, feature flags, and telemetry.
- Data plane owns continuity objects, memory revisions, open loops, approvals, audit traces, and interop semantics.
- Compile answers from durable stored truth, not transcript replay.
- Preserve append-only continuity, correction history, and explicit provenance.

## Operations And Delivery

- Consequential actions remain approval-bounded on every surface.
- Inbound chat handling and outbound delivery must be idempotent and auditable.
- Daily briefs and notifications must respect timezone, preferences, and quiet hours.
- Public docs must distinguish shipped OSS surface from beta product surface.
- New public-facing flows require smoke validation, not only unit tests.

## Control Docs

- Keep `ROADMAP.md` future-facing, `.ai/handoff/CURRENT_STATE.md` factual, and `RULES.md` limited to durable guidance.
- Archive superseded planning and control snapshots instead of keeping them in live files.
- Do not create or overwrite `.ai/active/SPRINT_PACKET.md` unless the next execution sprint is explicitly defined.
