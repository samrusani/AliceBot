# Recommended ADRs

## Existing Accepted ADRs Still In Force

- `ADR-001` public core package boundary
- `ADR-002` public runtime baseline
- `ADR-003` MCP tool surface contract
- `ADR-004` OpenClaw integration boundary
- `ADR-005` import provenance and dedupe strategy
- `ADR-007` public evaluation harness scope

## Next ADRs To Author For Phase 10

### ADR-006: Hosted Identity, Session, and Device Trust Model

- Why it deserves an ADR: auth mode, session expiry, device linking, and trust levels become hard security boundaries for the hosted product layer.
- Proposed status: Proposed

### ADR-008: Alice Connect Control Plane vs Data Plane Boundary

- Why it deserves an ADR: this decision determines what lives in hosted orchestration versus Alice Core and prevents semantic drift across surfaces.
- Proposed status: Proposed

### ADR-009: Cross-Surface Continuity Parity Contract

- Why it deserves an ADR: Telegram must reuse local, CLI, and MCP semantics instead of inventing a separate chat behavior model.
- Proposed status: Proposed

### ADR-010: Telegram Message Normalization and Routing Contract

- Why it deserves an ADR: inbound idempotency, attachment handling, workspace resolution, and thread routing define the chat transport boundary.
- Proposed status: Proposed

### ADR-011: Daily Brief and Notification Policy Model

- Why it deserves an ADR: scheduling semantics, quiet hours, delivery retries, and brief composition will otherwise sprawl across product and ops code.
- Proposed status: Proposed

### ADR-012: Opt-In Encrypted Backup and Sync Boundary

- Why it deserves an ADR: backup scope, encryption posture, and recovery semantics affect trust, support burden, and OSS-to-product separation.
- Proposed status: Proposed

### ADR-013: Beta Rollout, Feature Flag, and Support Telemetry Model

- Why it deserves an ADR: safe rollout, rollback, observability, and support diagnostics are launch-critical and cut across every Phase 10 surface.
- Proposed status: Proposed
