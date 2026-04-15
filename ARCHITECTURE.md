# Architecture

## Scope Boundary
- **Shipped baseline:** Phases 9-12 and Bridge `B1` through `B4`.
- **Current repo execution posture:** `v0.3.2` is the latest published tag; Phase 13 is active; `P13-S1` is shipped; `P13-S2` is the active execution sprint.
- **Phase principle:** Phase 13 is an adoption layer on top of Phase 12, not a new substrate phase.

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
- Shipped baseline includes semantic retrieval, embeddings, entities, trusted-fact promotion, fixture-based retrieval evaluation, hybrid retrieval streams, reranking, and persisted retrieval traces.
- Primary modules:
  - [`semantic_retrieval.py`](apps/api/src/alicebot_api/semantic_retrieval.py)
  - [`retrieval_evaluation.py`](apps/api/src/alicebot_api/retrieval_evaluation.py)
  - [`entity.py`](apps/api/src/alicebot_api/entity.py)
  - [`entity_edge.py`](apps/api/src/alicebot_api/entity_edge.py)
  - [`trusted_fact_promotions.py`](apps/api/src/alicebot_api/trusted_fact_promotions.py)

### Mutation, Trust, And Briefing Foundations
- Shipped baseline includes explicit memory operations, contradiction cases, trust signals, public eval persistence, and task-adaptive briefing.
- Primary modules:
  - [`memory.py`](apps/api/src/alicebot_api/memory.py)
  - [`task_briefing.py`](apps/api/src/alicebot_api/task_briefing.py)
  - [`contracts.py`](apps/api/src/alicebot_api/contracts.py)

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
- `memory_operation_candidates`, `memory_operations`
- `contradiction_cases`, `trust_signals`

### Retrieval And Evaluation
- `embedding_configs`, `memory_embeddings`
- `entities`, `entity_edges`
- `retrieval_runs`, `retrieval_candidates`
- `eval_suites`, `eval_cases`, `eval_runs`, `eval_results`
- task-artifact chunk embeddings for artifact-scoped retrieval

### Product / Runtime
- `workspaces`, `workspace_members`, `auth_sessions`, `devices`
- `model_providers`, `provider_capabilities`, `model_packs`, `workspace_model_pack_bindings`
- `task_briefs`
- channel, task, trace, approval, and execution tables

## Current Key Flows

### Capture And Review
1. Raw content enters continuity capture.
2. Alice creates capture events and candidate continuity objects.
3. Review/correction can confirm, edit, supersede, or delete.
4. Explainability preserves provenance and lifecycle state.

### Recall And Resumption
1. Recall loads continuity candidates.
2. Ranking considers semantic similarity, lexical/entity signals, trust, freshness, provenance, and supersession.
3. Resumption composes ranked recall into decisions, open loops, recent changes, and next action.

### Provider / Hermes Runtime
1. Workspace binds provider and model-pack configuration.
2. Runtime invokes through provider adapter boundaries.
3. Hermes can prefetch before a turn and capture after a turn while Alice remains the system of record.

## Phase 12 Baseline In Force
- Hybrid retrieval and reranking are the recall baseline.
- Explicit mutation operations are the memory-change baseline.
- Contradiction cases and trust signals are the conflict/trust baseline.
- The public eval harness is the quality-evidence baseline.
- Task-adaptive briefing is the current compiled-context baseline.

## Phase 13 Planned Delta

### P13-S1: One-Call Continuity
- Status: shipped
- Add the primary integration surface:
  - API: `POST /v1/continuity/brief`
  - CLI: `alice brief`
  - MCP: `alice_brief`
- Input should support:
  - `query`
  - optional `thread_id`
  - optional `task_id`
  - optional `project`
  - optional `person`
  - optional `since`
  - optional `until`
  - `brief_type`
  - `max_relevant_facts`
  - `max_recent_changes`
  - `max_open_loops`
  - `max_conflicts`
  - `max_timeline_highlights`
  - `include_non_promotable_facts`
- Output should include:
  - summary
  - relevant facts
  - recent changes
  - open loops
  - conflicts
  - timeline highlights
  - next suggested action
  - provenance bundle
  - trust posture
- This surface must compose shipped Phase 12 layers rather than reimplement them.

### P13-S2: Alice Lite
- Status: active
- Add a lighter local deployment profile for solo users and builders.
- Target outcomes:
  - one-command local startup
  - smaller-footprint profile
  - sample workspace bootstrap
  - faster first useful result
- Alice Lite must remain a deployment/profile change, not a separate product or semantics fork.
- SQLite or another embedded mode is not in scope unless semantics remain intact.

### P13-S3: Memory Hygiene + Conversation Health
- Status: queued
- Add visible hygiene surfaces for:
  - duplicates
  - stale facts
  - unresolved contradictions
  - weakly trusted memory
  - review queue pressure
- Add conversation/thread health surfaces for:
  - recent threads
  - stale threads
  - risky threads
  - thread activity / health posture
- This work is visibility and operational legibility first, not new substrate work.

## Security And Reliability Rules
- Keep user/workspace isolation intact for continuity, provider, and channel data.
- Keep provider credentials and secret references out of logs and outward-facing errors.
- Preserve approval-bounded execution for consequential side effects.
- Keep capture, mutation, and Hermes sync paths idempotent.
- Preserve append-only evidence where the system depends on auditability.
- Do not let the one-call continuity surface bypass provenance, trust, or supersession rules already enforced by the baseline.
- Do not let Alice Lite weaken continuity semantics in exchange for easier install.

## Deployment Topology

### Recommended
- Alice API + Postgres as system of record
- Alice MCP for explicit workflows
- Provider runtime where model abstraction is needed
- Hermes provider-plus-MCP for always-on continuity

### Phase 13 Addition
- Alice Lite should be a lighter deployment/profile around the same core runtime, not a separate architecture.

### Fallback
- MCP-only remains supported when provider automation is unavailable

## Testing Strategy
- unit/integration tests for continuity, runtime, and API behavior
- fixture-based retrieval and eval suites
- API/CLI/MCP parity tests for `P13-S1`
- startup/smoke coverage for Alice Lite profile work in `P13-S2`
- hygiene/thread-health tests for `P13-S3`
- web tests for shipped user/admin surfaces
- Hermes provider smoke, MCP smoke, and demo flows

## Control Tower Decisions Needed
- Whether Alice Lite can reduce services in `P13-S2` without harming semantics or release credibility.
- Exact default payload posture for `/v1/continuity/brief`.
- Threshold model for thread risk and health visibility in `P13-S3`.
