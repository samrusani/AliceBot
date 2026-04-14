# Architecture

## Scope Boundary
- **Shipped baseline:** Phases 9-11 and Bridge `B1` through `B4`.
- **Current repo execution posture:** `v0.2.0` is released; `P12-S1`, `P12-S2`, and `P12-S3` are shipped; `P12-S4` is the active sprint.
- **Phase 12 delta:** retrieval quality, mutation explicitness, contradiction handling, public evals, and adaptive briefing.

## Current System Overview
Alice is a modular continuity platform with shared continuity semantics across local, hosted, provider-runtime, MCP, and Hermes-integrated surfaces.

## Technical Stack
- API/runtime: Python + FastAPI in [`apps/api/src/alicebot_api`](apps/api/src/alicebot_api)
- Persistence: Postgres with Alembic migrations in [`apps/api/alembic/versions`](apps/api/alembic/versions)
- Optional cache/runtime support: Redis
- Web/admin: Next.js app in [`apps/web`](apps/web)
- CLI + MCP: Python CLI/MCP plus package shims in [`packages/alice-cli`](packages/alice-cli) and [`packages/alice-core`](packages/alice-core)
- Ops/demo/test scripts: [`scripts`](scripts)

## Shipped Module Boundaries

### Continuity Core
- Capture, review, lifecycle, explainability, recall, resumption, and open-loop flows.
- Primary modules:
  - [`continuity_capture.py`](apps/api/src/alicebot_api/continuity_capture.py)
  - [`continuity_review.py`](apps/api/src/alicebot_api/continuity_review.py)
  - [`continuity_recall.py`](apps/api/src/alicebot_api/continuity_recall.py)
  - [`continuity_resumption.py`](apps/api/src/alicebot_api/continuity_resumption.py)
  - [`continuity_open_loops.py`](apps/api/src/alicebot_api/continuity_open_loops.py)

### Retrieval And Evidence Foundations
- Existing baseline already includes semantic retrieval, embeddings, entities, trusted-fact promotion, and fixture-based retrieval evaluation.
- Primary modules:
  - [`semantic_retrieval.py`](apps/api/src/alicebot_api/semantic_retrieval.py)
  - [`retrieval_evaluation.py`](apps/api/src/alicebot_api/retrieval_evaluation.py)
  - [`entity.py`](apps/api/src/alicebot_api/entity.py)
  - [`entity_edge.py`](apps/api/src/alicebot_api/entity_edge.py)
  - [`trusted_fact_promotions.py`](apps/api/src/alicebot_api/trusted_fact_promotions.py)

### Hosted/Product Layer
- Workspace, identity, devices, preferences, telemetry, web/admin, and channel surfaces.

### Provider Runtime
- Workspace-scoped provider registration, capability snapshots, model packs, invocation, and secret handling.

### Hermes Bridge
- Provider hook integration, prefetch, post-turn capture, review queue, explainability, and MCP fallback.

## Current Data Model Summary

### Continuity And Memory
- `memories`, `memory_revisions`, `memory_review_labels`
- `continuity_capture_events`, `continuity_objects`, `continuity_correction_events`
- `open_loops`

### Retrieval Foundations
- `embedding_configs`, `memory_embeddings`
- `entities`, `entity_edges`
- task-artifact chunk embeddings for artifact-scoped retrieval

### Product/Runtime
- `workspaces`, `workspace_members`, `auth_sessions`, `devices`
- `model_providers`, `provider_capabilities`, `model_packs`, `workspace_model_pack_bindings`
- channel, task, trace, approval, and execution tables

## Current Key Flows

### Capture And Review
1. Raw content enters continuity capture.
2. Alice creates capture events and candidate continuity objects.
3. Review/correction can confirm, edit, supersede, or delete.
4. Explainability preserves provenance and lifecycle state.

### Recall And Resumption
1. Recall loads continuity candidates.
2. Ranking already considers semantic similarity, trust, freshness, provenance, supersession, and entity/scope matches.
3. Resumption composes ranked recall into decisions, open loops, recent changes, and next action.

### Provider/Hermes Runtime
1. Workspace binds provider and model-pack configuration.
2. Runtime invokes through provider adapter boundaries.
3. Hermes can prefetch before a turn and capture after a turn while Alice remains the system of record.

## Phase 12 Architecture Delta

### P12-S1: Hybrid Retrieval + Reranking
Shipped in `P12-S1`:
- semantic stream
- lexical/BM25-style stream
- entity/edge traversal stream
- temporal filtering/weighting
- trust-aware reranking
- persisted retrieval traces

Planned additions:
- `retrieval_runs`
- `retrieval_candidates`
- debug surfaces for API, CLI, and MCP

Important baseline note: `P12-S1` is now the retrieval baseline for the rest of Phase 12 and should not be reopened except where later sprint integration requires it.

### P12-S2: Automated Memory Operations
Shipped in `P12-S2`:
- `ADD`
- `UPDATE`
- `SUPERSEDE`
- `DELETE`
- `NOOP`

Delivered additions:
- `memory_operation_candidates`
- `memory_operations`

Important baseline note: `P12-S2` is now the mutation baseline for the rest of Phase 12 and should not be reopened except where later sprint integration requires it.

### P12-S3: Contradiction Detection + Trust Calibration
Shipped in `P12-S3`:

Delivered additions:
- `contradiction_cases`
- `trust_signals`

Important baseline note: `P12-S3` is now the contradiction/trust baseline for the rest of Phase 12 and should not be reopened except where later sprint integration requires it.

### P12-S4: Public Eval Harness
Expand the current retrieval evaluation foundation into public multi-suite benchmark runs and checked-in baseline reports.

Planned additions:
- `eval_suites`
- `eval_cases`
- `eval_runs`
- `eval_results`

Important baseline note: `P12-S4` should measure shipped retrieval, mutation, and contradiction behavior rather than redesign those systems.
Source-of-truth note: the checked-in fixture catalog defines the authoritative suite/case set and ordering; persisted eval suite/case rows are synchronized snapshots for execution and audit, not an independent planning surface.

### P12-S5: Task-Adaptive Briefing
Separate durable memory from output-specific briefing layers.

Planned additions:
- `task_briefs`
- provider/model-pack briefing strategy fields

Important baseline note: Alice already has resumption, daily-brief, and chief-of-staff briefing surfaces. Phase 12 should treat those as starting points, not as greenfield briefing.

## Security And Reliability Rules
- Keep user/workspace isolation intact for continuity, provider, and channel data.
- Keep provider credentials and secret references out of logs and outward-facing errors.
- Preserve approval-bounded execution for consequential side effects.
- Keep capture, mutation, and Hermes sync paths idempotent.
- Preserve append-only evidence where the system depends on auditability.

## Deployment Topology

### Recommended
- Alice API + Postgres as system of record
- Alice MCP for explicit workflows
- Provider runtime where model abstraction is needed
- Hermes provider-plus-MCP for always-on continuity

### Fallback
- MCP-only remains supported when provider automation is unavailable

## Testing Strategy
- unit/integration tests for continuity, runtime, and API behavior
- fixture-based retrieval and eval suites
- web tests for shipped user/admin surfaces
- Hermes provider smoke, MCP smoke, and demo flows
- release/eval artifacts committed only when they correspond to exact commands and fixtures

## Control Tower Decisions Needed
- Should Phase 12 retrieval ship behind a feature flag before it replaces the default recall path?
- Should new endpoints use `/v1/retrieval/*`, `/v1/evals/*`, `/v1/briefs/*`, or extend existing continuity endpoints?
- Should contradictions attach to continuity objects only, memories only, or both with a shared abstraction?
- Should `DELETE` be restricted to logical deletion/tombstoning by default?
