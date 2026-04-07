# Architecture

## System Overview

Alice is a local-first memory and continuity engine built around durable continuity storage, deterministic context compilation, correction-aware memory, open-loop tracking, trust-calibrated retrieval, and approval-bounded operational workflows.

The current implementation already includes:

- continuity capture, recall, resumption, review, and open-loop seams
- trust-calibrated memory quality and retrieval posture
- a chief-of-staff layer with prioritization, follow-through, preparation, review, and governed handoff workflows
- deterministic gate and release evidence infrastructure

Phase 9 does not replace that architecture. It packages and exposes it through public-safe boundaries.

Current public-core packaging state is defined in `P9-S33`: one install path, one runtime baseline, and one deterministic sample-data fixture for recall and resumption verification.

## Technical Stack

- Backend: Python + FastAPI
- Web: Next.js + React
- Database: Postgres
- Vector support: `pgvector`
- Local infrastructure: Docker Compose, Redis, MinIO
- Testing: pytest, Vitest
- Packaging target for `P9-S33`:
  - `alice-core` (published package name in `pyproject.toml`)
  - deterministic fixture loader (`scripts/load_sample_data.sh`)
- Deferred packaging targets (`P9-S34+`):
  - `apps/cli`
  - `apps/mcp-server`
  - importer/adapter packages

## High-Level Architecture

### Current Runtime Layers

1. Continuity and memory engine
2. Retrieval and resumption compiler
3. Trust and memory-quality layer
4. Chief-of-staff product layer
5. Governed task/approval/handoff layer
6. Web operator shell and test/evidence scripts

### Phase 9 Public Packaging Layers

1. `alice-core`
   - continuity capture
   - recall
   - resumption
   - open-loop retrieval
   - correction-aware memory behavior
2. `alice-cli` (deferred)
   - terminal access to public core flows
3. `alice-mcp-server` (deferred)
   - stable MCP tool surface for external assistants
4. `alice-importers` (deferred)
   - markdown, chat export, CSV, and adapter-backed imports
5. `alice-openclaw` (deferred)
   - OpenClaw-specific ingestion and interop mapping

## Module Boundaries

### Current Modules

- `apps/api`: core product seams and current HTTP surface
- `apps/web`: operator shell and review workspaces
- `scripts`: local dev, migration, gate, evidence, and operational commands
- `tests`: backend and web validation

### Phase 9 Public Boundaries

Public-safe:

- continuity core
- recall and resumption compiler
- correction and review seams
- open-loop seams
- trust-calibrated retrieval posture
- CLI command layer
- MCP tool layer
- importer layer
- external adapter layer

Keep internal or deferred:

- broad connector write actions
- unsafe autonomous execution
- hosted SaaS assumptions
- broad channel distribution layers

## Core Flows

### Continuity Flow

1. Capture immutable continuity event.
2. Conservatively derive typed continuity object when justified.
3. Retrieve scoped continuity by query, thread, project, person, or time.
4. Compile deterministic resumption and review artifacts.
5. Apply correction events before mutating active truth posture.

### Public CLI Flow

1. User runs CLI command.
2. Command resolves local config and user context.
3. Core engine executes continuity or correction flow.
4. CLI returns deterministic terminal-friendly output with provenance snippets.

### MCP Flow

1. External client calls a small stable Alice MCP tool.
2. MCP server converts tool input into core continuity operation.
3. Alice returns deterministic serialized output.
4. External client uses Alice results for recall, resumption, or context packing.

### Import Flow

1. Importer reads external data source.
2. Mapping logic transforms source records into capture events and continuity objects.
3. Dedupe and provenance tagging are applied.
4. Imported data becomes queryable through normal Alice recall and resumption paths.

## Data Model Summary

Core durable objects already in use:

- continuity capture events
- typed continuity objects
- correction events
- open loops
- memory revisions
- trust and quality posture summaries
- chief-of-staff artifacts and handoff records

Phase 9 should preserve current semantics and add packaging, import, and interop boundaries around them rather than redesigning these structures.

## API and Interface Boundaries

Current internal/publicizing HTTP seams include:

- continuity capture, recall, resumption, review, open loops
- memories quality gate and trust dashboard
- chief-of-staff outputs and governed handoff flows

Phase 9 should add public interfaces through:

- CLI commands
- MCP tool schemas
- importer entrypoints
- adapter-specific import/interop commands

The initial MCP surface should stay intentionally small and stable.

## Security and Permissions Model

- Postgres is the system of record.
- Row-level security remains required for user-owned tables.
- Append-only event and revision surfaces remain authoritative.
- Consequential actions remain approval-bounded.
- External side effects must not be introduced through Phase 9 packaging work.
- Public interop should not bypass current trust, provenance, or approval boundaries.

## Deployment Model

Phase 9 public deployment target is local-first.

Primary supported path:

- Docker Compose
- local Postgres with `pgvector`
- documented `.env` path
- one stable boot flow for API/core services
- deterministic fixture load via `./scripts/load_sample_data.sh`

Optional fallback runtime support should only be introduced if it can be supported cleanly without compromising determinism.

## Testing Strategy

Phase 9 should preserve existing backend and web test coverage while adding:

- install smoke tests
- CLI golden-output tests
- MCP contract tests
- importer tests and fixtures
- interop tests for at least one external client/adapter
- public quickstart validation path
- evaluation harness for recall, resumption, correction, and open-loop quality

## Observability and Logging

Current deterministic release and evidence infrastructure remains the baseline.

Phase 9 should add:

- install success/failure visibility
- importer success/failure reporting
- MCP tool error visibility
- public evaluation artifacts

This should extend current evidence discipline, not replace it.

## Open Technical Risks

- Public package boundaries may be blurrier than current internal module layout.
- Import and dedupe quality can quickly degrade trust if rushed.
- MCP surface can sprawl if too many tools are exposed early.
- Public docs can drift from actual runtime behavior if install testing is weak.
- Optional runtime fallback support can create more confusion than value if introduced too early.

## Legacy Compatibility Marker

Documentation lineage remains continuous through Phase 3 Sprint 9.
