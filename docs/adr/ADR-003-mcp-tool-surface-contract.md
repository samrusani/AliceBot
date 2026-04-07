# ADR-003: MCP Tool Surface Contract

## Status

Accepted (2026-04-07)

## Context

Phase 9 includes exposing Alice through an MCP server so external assistants can use Alice as a memory and continuity layer. A large or unstable MCP surface would increase support burden, make evaluation harder, and encourage clients to depend on accidental internal behavior rather than the intended continuity contract.

## Decision

Start with a deliberately small MCP tool surface aligned to the public v0.1 contract.

Recommended first tools:

- `alice_capture`
- `alice_recall`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_context_pack`

Tool design rules:

- inputs and outputs must be deterministic and provenance-backed where applicable
- names should describe user-facing continuity jobs, not internal implementation details
- tool semantics must stay narrow and stable across early public releases
- do not expose write-capable side effects beyond Alice’s own continuity and correction domain in the initial MCP release

## Consequences

Positive:

- keeps the interop story understandable and testable
- aligns MCP behavior with the product wedge instead of generic agent sprawl
- limits contract churn for early adopters

Negative:

- some external-agent use cases will need to wait for later MCP expansion
- pressure may remain to expose internal helper seams that are not yet stable

## Alternatives Considered

### Publish a broad MCP surface from the current internal API

Rejected because it would expose unstable internals and create support obligations before the public contract is proven.

### Delay MCP boundary decisions until Sprint 35

Rejected because Sprint 33 and Sprint 34 need a stable public contract to package and document against.
