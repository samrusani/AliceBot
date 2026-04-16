# Architecture

## Scope Boundary
- **Shipped baseline:** Phases 9-13 and Bridge `B1` through `B4`.
- **Current repo execution posture:** `v0.4.0` is the latest published tag; Phase 14 is active; `P14-S1` is the active execution sprint.
- **Phase principle:** Phase 14 is a platform-and-adoption phase, not a new substrate-research phase.

## Current System Overview
Alice is a modular continuity platform with shared continuity semantics across local, hosted, provider-runtime, CLI, MCP, Hermes-integrated, and imported-workflow surfaces.

## Technical Stack
- API/runtime: Python + FastAPI in [`apps/api/src/alicebot_api`](apps/api/src/alicebot_api)
- Persistence: Postgres with Alembic migrations in [`apps/api/alembic/versions`](apps/api/alembic/versions)
- Optional cache/runtime support: Redis
- Web/admin: Next.js app in [`apps/web`](apps/web)
- CLI + MCP: Python CLI/MCP plus package shims in [`packages/alice-cli`](packages/alice-cli) and [`packages/alice-core`](packages/alice-core)
- Ops/demo/test scripts: [`scripts`](scripts)

## Shipped Module Boundaries

### Continuity Core
- Capture, review, lifecycle, explainability, recall, resumption, open-loop workflows, and one-call continuity assembly.

### Retrieval And Evidence Foundations
- Hybrid retrieval, embeddings, entity/entity-edge support, reranking, trust-aware evidence shaping, and persisted retrieval traces.

### Mutation, Trust, And Briefing Foundations
- Explicit memory operations, contradiction cases, trust signals, public eval persistence, and task-adaptive briefing.

### Hosted/Product Layer
- Workspace, identity, devices, preferences, telemetry, web/admin, and channel surfaces.

### Provider Runtime Foundation
- Workspace-scoped provider records, capability snapshots, runtime invocation boundaries, model-pack primitives, and secret handling.

### Integration Surfaces
- CLI, MCP, Hermes bridge/provider flows, OpenClaw import/augmentation, and deployment profiles such as Alice Lite.

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

### Product / Runtime
- `workspaces`, `workspace_members`, `auth_sessions`, `devices`
- current provider/runtime tables from the shipped baseline
- channel, task, trace, approval, and execution tables

## Current Key Flows

### Capture And Review
1. Raw content enters continuity capture.
2. Alice creates capture events and candidate continuity objects.
3. Review/correction can confirm, edit, supersede, or delete.
4. Explainability preserves provenance and lifecycle state.

### Recall, Resumption, And Briefing
1. Recall loads continuity candidates.
2. Ranking considers semantic similarity, lexical/entity signals, trust, freshness, provenance, and supersession.
3. Resumption and one-call continuity compose ranked recall into decisions, open loops, recent changes, provenance, trust posture, and next action.

### Provider / Hermes Runtime
1. Workspace binds provider and model-pack configuration.
2. Runtime invokes through provider adapter boundaries.
3. Hermes can prefetch before a turn and capture after a turn while Alice remains the system of record.

## Phase 13 Baseline In Force
- One-call continuity is the primary continuity integration surface.
- Alice Lite is the lighter local deployment profile.
- Hygiene and thread-health visibility are part of the shipped baseline.

## Phase 14 Shared Delta

### Platform Concepts
- **Provider:** a runtime connector Alice uses to talk to a specific model-serving interface.
- **Model pack:** a versioned profile shaping prompt/context behavior, tool strategy, briefing strategy, token budgets, and model-specific quirks.
- **Integration kit:** a runtime-specific starter path for Hermes, OpenClaw, Python agents, and TypeScript agents.
- **Design partner workspace:** a tracked workspace with onboarding, support, instrumentation, and pilot outcome logging.

### P14-S1 API Additions
- Provider management:
  - `POST /v1/providers`
  - `GET /v1/providers`
  - `GET /v1/providers/{provider_id}`
  - `PATCH /v1/providers/{provider_id}`
  - `POST /v1/providers/test`
- Runtime invocation:
  - `POST /v1/runtime/invoke`

### P14-S1 Table Additions And Refinements
- `model_providers`
- `provider_capabilities`
- `provider_invocation_telemetry`

### Provider Adapter Contract
- Required methods:
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
- Design rule:
  - providers may affect capability support, latency, token budgets, and model-specific behavior
  - providers must not fork continuity object semantics, contradiction handling, provenance contracts, or one-call continuity behavior

### P14-S1 Notes
- Workspace bootstrap can seed OpenAI-compatible providers from `WORKSPACE_PROVIDER_CONFIGS_JSON`.
- Invocation telemetry persists normalized provider test and runtime invoke records.
- Later Phase 14 API/table expansions stay in roadmap and spec docs until they are implemented.

## Phase 14 Sprint Sequence
- `P14-S1` Provider abstraction cleanup + OpenAI-compatible adapter
- `P14-S2` Ollama + llama.cpp + vLLM adapters
- `P14-S3` Model packs
- `P14-S4` Reference integrations
- `P14-S5` Design partner launch

## Security And Reliability Rules
- Keep user/workspace isolation intact for continuity, provider, runtime, and design-partner data.
- Keep provider credentials and secret references out of logs and outward-facing errors.
- Preserve approval-bounded execution for consequential side effects.
- Keep capture, mutation, and provider/Hermes sync paths idempotent.
- Preserve append-only evidence where the system depends on auditability.
- Do not let provider-specific behavior fork continuity semantics.
- Do not let model packs bypass provenance, trust, or contradiction rules already enforced by the baseline.

## Testing Strategy
- unit/integration tests for continuity, provider runtime, and API behavior
- provider smoke tests and provider-capability parity checks
- model-pack smoke tests and compatibility-matrix validation
- integration smoke tests for Hermes, OpenClaw, Python example, and TypeScript example paths
- release gates remain green across Python, web, Alice Lite, Hermes smoke, and public eval harness
- docs verification is part of sprint completion, not cleanup work

## Current Architectural Posture
- `v0.4.0` remains the active public release boundary.
- Phase 14 extends the shipped provider/runtime foundation into a more stable integration platform.
- The continuity substrate remains the same system of record; Phase 14 is about compatibility, packaging, reference integrations, and design-partner proof.
