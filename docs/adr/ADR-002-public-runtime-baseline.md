# ADR-002: Public Runtime Baseline

## Status

Accepted (2026-04-07)

## Context

Alice currently runs locally with Postgres, `pgvector`, Redis, and MinIO in Docker Compose. Phase 9 needs a public runtime story that external technical users can install and verify without ambiguity. Supporting multiple storage/runtime modes too early would increase docs drift and make retrieval semantics harder to keep consistent.

## Decision

Adopt one supported public runtime baseline for Phase 9:

- Postgres
- `pgvector`
- Docker Compose for local infrastructure

Treat this as the canonical v0.1 setup path. Do not claim SQLite or other reduced local modes as supported public runtimes unless they preserve Alice’s continuity, retrieval, and correction semantics without special-case behavior.

Redis and MinIO remain acceptable support services when required by the current product, but the primary public runtime promise is the Postgres-backed local install path.

## Consequences

Positive:

- keeps the public quickstart simple and testable
- preserves retrieval and memory semantics already proven internally
- avoids splitting engineering time across multiple weakly supported install modes

Negative:

- raises the minimum local setup bar for some users
- defers simpler single-file runtimes unless they are validated later

## Alternatives Considered

### Support SQLite immediately as a public fallback

Rejected for Phase 9 because it risks semantic drift and extra support burden before the public product contract is stable.

### Support multiple deployment modes at launch

Rejected because Phase 9 needs one reliable path more than optional breadth.
