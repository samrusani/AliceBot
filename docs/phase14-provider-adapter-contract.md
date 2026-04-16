# Phase 14 Provider Adapter Contract

## Purpose
Define the stable provider interface that every Alice runtime connector must implement in Phase 14.

## Required Methods
- `healthcheck()`
- `list_models()`
- `invoke_responses()`
- `invoke_embeddings()`
- `supports_tools()`
- `supports_reasoning()`
- `supports_vision()`
- `normalize_response()`
- `normalize_usage()`
- `normalize_tool_schema()`
- `discover_capabilities()`
- `invoke()`

## Extension Note
Phase `P14-S1` standardizes the methods above. Streaming and provider-specific JSON-mode helpers can be added later if a future sprint needs them, but they are not part of the current stable contract.

## Provider Responsibilities
- translate provider-specific request/response details into Alice runtime semantics
- expose capabilities without changing continuity behavior
- normalize usage, latency, and error reporting
- persist capability checks and invocation telemetry through the shared store

## Continuity Invariants
A provider adapter may affect:
- capability support
- latency
- token budgets
- model-specific behavior

A provider adapter must not change:
- the continuity object model
- memory and trust semantics
- contradiction handling
- provenance contracts
- one-call continuity behavior

## Shared Surface
`P14-S1` provider work supports:
- provider registration and update
- workspace bootstrap config seeding
- provider test and capability persistence
- runtime invocation through the shared continuity path

## Initial Phase 14 Target Adapters
- OpenAI-compatible for this sprint
- Azure-backed path and local/self-hosted adapters remain follow-on Phase 14 work

## Verification Expectation
Every adapter must have parity-focused smoke coverage proving that continuity semantics remain stable while provider capabilities and operational behavior vary.
