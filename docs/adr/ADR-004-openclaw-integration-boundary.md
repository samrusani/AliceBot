# ADR-004: OpenClaw Integration Boundary

## Status

Accepted (2026-04-07)

## Context

`P9-S36` is the first external adapter sprint after the shipped public-core (`P9-S33`), CLI (`P9-S34`), and MCP transport (`P9-S35`) seams. The product goal for this sprint is proving Alice can ingest external agent memory while preserving the same continuity semantics already shipped.

A broad importer framework in this sprint would add contract risk and blur the boundary between adapter work and platform work.

## Decision

Adopt a narrow OpenClaw-first integration boundary in `P9-S36`:

- support file-based OpenClaw import only (JSON file or workspace directory with JSON memory payloads)
- map OpenClaw memory entries into shipped Alice continuity objects (no bypass path)
- preserve explicit imported provenance with `source_kind = openclaw_import`
- apply deterministic dedupe using a stable workspace+payload fingerprint
- keep MCP augmentation limited to existing shipped tools (`alice_recall`, `alice_resume`, etc.) without adding new MCP tools

Input contract for this sprint is intentionally small:

- root object payloads with one of `durable_memory`, `memories`, `items`, or `records`
- optional `workspace` metadata object
- optional directory contract using known JSON filenames (`workspace.json`, `openclaw_workspace.json`, `durable_memory.json`, `memories.json`, `openclaw_memories.json`)

## Consequences

Positive:

- proves real external adapter ingestion without reopening continuity semantics
- keeps import behavior auditable and deterministic
- gives a concrete template for future importer work in `P9-S37`

Negative:

- does not yet provide generalized multi-source importer abstractions
- non-OpenClaw sources remain out of scope for this sprint

## Alternatives Considered

### Introduce a generic importer framework in `P9-S36`

Rejected because it increases scope and contract surface before the first concrete adapter is proven.

### Add new MCP import tools for OpenClaw

Rejected because MCP surface expansion is out of `P9-S36` scope and would dilute parity guarantees with shipped continuity seams.
