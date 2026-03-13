# Recommended ADRs

## ADR-001: Modular Monolith for V1

- Why it deserves an ADR: service boundaries, deployment complexity, team workflow, and failure modes all depend on this choice.
- Proposed status: Proposed

## ADR-002: Postgres + `pgvector` as V1 System of Record and Retrieval Store

- Why it deserves an ADR: it sets the data platform, query model, operational burden, and later migration path.
- Proposed status: Proposed

## ADR-003: Append-Only Continuity Model for Threads, Sessions, and Events

- Why it deserves an ADR: this decision defines auditability, replay behavior, and how memory derives from source truth.
- Proposed status: Proposed

## ADR-004: Memory as a Derived, Revisioned Projection

- Why it deserves an ADR: it governs data integrity, contradiction handling, consolidation, and user trust.
- Proposed status: Proposed

## ADR-005: Deterministic Context Compiler Contract

- Why it deserves an ADR: it affects explainability, cache reuse, testing strategy, and model portability.
- Proposed status: Proposed

## ADR-006: Auth and Per-User Isolation Model

- Why it deserves an ADR: username/password plus TOTP, database user context, and RLS policy shape are hard security boundaries.
- Proposed status: Proposed

## ADR-007: Policy Engine + Tool Proxy + Approval Boundary

- Why it deserves an ADR: this is the core safety architecture for any external action or sensitive data access.
- Proposed status: Proposed

## ADR-008: Relational Entity and Relationship Storage in V1

- Why it deserves an ADR: choosing relational storage over a graph database affects schema design, query strategy, and scale assumptions.
- Proposed status: Proposed

## ADR-009: Object Storage and Scoped Task Workspace Strategy

- Why it deserves an ADR: artifact handling, document ingestion, and task isolation depend on this storage boundary.
- Proposed status: Proposed

## ADR-010: Read-Only Connector Strategy for Gmail and Calendar

- Why it deserves an ADR: connector permission scope has major product, security, and delivery consequences.
- Proposed status: Proposed

## ADR-011: Trace-First Observability and Audit Logging Model

- Why it deserves an ADR: explainability, incident review, and ship-gate validation depend on what is logged and retained.
- Proposed status: Proposed

## ADR-012: Deployment Architecture for V1

- Why it deserves an ADR: VPS versus managed container hosting, secret handling, backup posture, and runtime topology affect both cost and risk.
- Proposed status: Proposed
