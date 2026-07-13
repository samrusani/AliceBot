# Architecture

## Scope Boundary
- **Shipped baseline:** `v0.9.4` is the latest published pre-1.0 release. It is tagged and immutable, with Trusted Publishing attestations and artifact digests in `docs/release/v0.9.4-checksums.txt`. It attempted the second-audit remediation, but a third independent audit found partial fixes and regressions; the published tag is a baseline, not proof that those findings are closed.
- **Current execution posture:** `v0.10.0` is the active audit-remediation candidate. Correctness, exact-SHA semantic release evidence, typing, web quality, backup, packaging, and documentation gates take priority over new features. No v0.10.0 work has shipped.

## Current System Overview
Alice is the continuity layer for AI agents: a modular continuity platform with shared continuity semantics across local, hosted, provider-runtime, CLI, MCP, Hermes-integrated, and imported-workflow surfaces.

## Technical Stack
- API/runtime: Python + FastAPI in [`apps/api/src/alicebot_api`](apps/api/src/alicebot_api)
- Persistence: Postgres (with `pgvector` for semantic retrieval) and Alembic migrations in [`apps/api/alembic/versions`](apps/api/alembic/versions)
- Optional cache/runtime support: Redis
- Web/admin: Next.js app in [`apps/web`](apps/web)
- CLI + MCP: the `alice-memory` wheel/sdist installs four public entrypoints:
  `alice-memory`, `alicebot`, `alice`, and `alicebot-mcp`; editable checkout
  installation is only the contributor variant.
- Ops/demo/test scripts: [`scripts`](scripts) are checkout-level maintenance,
  release, evaluation, and demonstration utilities; runtime users should use
  the packaged entrypoints above.

## Shipped Module Boundaries

### Continuity Core
- Capture, review, lifecycle, explainability, recall, resumption, open-loop workflows, and one-call continuity assembly.

### Retrieval And Evidence Foundations
- Hybrid retrieval over Postgres full-text search plus `pgvector` (HNSW) vector search, fused with reciprocal-rank fusion; embeddings come from any OpenAI-compatible endpoint via `ALICE_EMBEDDINGS_BASE_URL` / `ALICE_EMBEDDINGS_MODEL` / `ALICE_EMBEDDINGS_API_KEY`, and retrieval degrades to full-text-only (stated in traces) when no endpoint is configured.
- Entity/entity-edge support, reranking, trust-aware evidence shaping, and persisted retrieval traces.

### Mutation, Trust, And Briefing Foundations
- Explicit memory operations, contradiction cases, trust signals, public eval persistence, and task-adaptive briefing.

### Hosted/Product Layer
- Workspace, identity, devices, preferences, telemetry, web/admin, and channel surfaces.

### Provider Runtime Foundation
- Workspace-scoped provider records, capability snapshots, runtime invocation boundaries, model-pack primitives, and secret handling.

### Integration Surfaces
- CLI, MCP, Hermes bridge/provider flows, OpenClaw import/augmentation, deployment profiles such as Alice Lite, and generic external-builder reference examples.
- The MCP server exposes eleven core tools by default (`alice_capture`, `alice_recall`, `alice_resume`, `alice_context_pack`, `alice_open_loops`, `alice_recent_decisions`, `alice_memory_review`, `alice_memory_correct`, `alice_explain`, `alice_memory_commit`, `alice_memory_manage`). The 65-tool legacy surface is available only for deliberately keyless local-operator compatibility behind `ALICE_MCP_LEGACY_TOOLS=1`; setting `ALICE_AGENT_API_KEY` hides and rejects it.
- Agent HTTP calls authenticate with per-agent API keys (`alicebot agent keys create --agent-id <id> --profile <profile>`, sent as `Authorization: Bearer`); the key record overrides payload identity, payloads may only downgrade the profile, and keyless agent calls work only while zero active keys exist.

### vNext Preview Surfaces
- local-first vNext memory kernel with sources, source chunks, provenance links, generated artifacts, artifact quality ratings, event log, agent identities, scheduler workflows, and connector evidence
- live local capture connectors for allowlisted Telegram sync, local folder/Obsidian scan and watch, browser clip captures, and Hermes/OpenClaw-style agent output ingestion
- dedicated connector settings/state storage for connector defaults, sync modes, cursors, counters, failures, and restart-safe health posture
- local connector secret-provider abstraction with environment references, encrypted local fallback, and redaction before persistence
- research-informed memory ergonomics: review-only `memory_consolidation` scheduler workflow, first-class `procedure` memories in the existing memory/revision model, benchmark-aligned eval suites, and read-only agent context tree over existing records
- `/vnext` operator workspace with live/fixture-backed review, Ask Alice, generated artifacts, model comparison, scheduler controls, live connector configuration, connector health, dogfooding telemetry, and privacy settings

## Current Data Model Summary

### Continuity And Memory
- `memories`, `memory_revisions`, `memory_review_labels`
- `continuity_capture_events`, `continuity_objects`, `continuity_correction_events`
- `open_loops`
- `memory_operation_candidates`, `memory_operations`
- `contradiction_cases`, `trust_signals`
- `procedure` is a canonical `memories.memory_type` for repeatable playbooks; it uses the same review, revision, provenance, correction, and supersession model as other memories

### Retrieval And Evaluation
- `embedding_configs`, `memory_embeddings` (pgvector-backed)
- `entities`, `entity_edges`
- `retrieval_runs`, `retrieval_candidates`
- `eval_suites`, `eval_cases`, `eval_runs`, `eval_results`
- the eval harness ships six live suites — `retrieval_quality`, `correction_suppression`, `decision_recovery`, `provenance_explanation`, `entity_resolution`, and `graph_hop_retrieval` (see `eval/README.md`); live runs require `ALICEBOT_EVAL_DATABASE_URL` and are otherwise reported as skipped

### Product / Runtime
- `workspaces`, `workspace_members`, `auth_sessions`, `devices`
- `model_providers`, `provider_capabilities`, `model_packs`, `workspace_model_pack_bindings`
- `provider_invocation_telemetry`
- pilot launch/admin tables
- `task_briefs`
- `agent_api_keys` (hashed per-agent API keys for agent HTTP/MCP authentication)
- `connector_settings`, `connector_state`
- channel, task, trace, approval, and execution tables

## Key Flows In Force

### Capture And Review
1. Raw content enters continuity capture.
2. Alice creates capture events and candidate continuity objects.
3. Review/correction can confirm, edit, supersede, or delete.
4. Explainability preserves provenance and lifecycle state.

### Recall, Resumption, And Briefing
1. Recall loads continuity candidates.
2. Ranking considers semantic similarity, lexical/entity signals, trust, freshness, provenance, and supersession.
3. Resumption and one-call continuity compose ranked recall into decisions, open loops, recent changes, provenance, trust posture, and next action.

### Consolidation And Context Navigation
1. The governed scheduler can run `memory_consolidation` over accepted memories, reviewed sources, generated artifacts, recent events, corrections, and artifact ratings.
2. Consolidation creates reviewable artifacts and optional candidate memories only; it never promotes trusted memory automatically.
3. Agents can request a read-only context tree over projects, memories, sources, open loops, artifacts, and recent traces without receiving direct write access to the memory store.

### Provider Runtime
1. Workspace binds provider and optional model-pack configuration.
2. Runtime invokes through provider adapter boundaries.
3. Invocation telemetry and capability snapshots remain inspectable.

### External Builder Runtime
1. External runtimes use one-call continuity, MCP, Hermes provider-plus-MCP, or OpenClaw import/augmentation paths.
2. Provider and model-pack controls remain Alice-side supporting configuration.
3. Generic examples and reproducible demos package the shipped surface rather than defining a second runtime contract.

## Provider Runtime And Integration Baseline

### Provider Abstraction + OpenAI-Compatible Adapter
- Stabilized the provider adapter contract.
- Shipped workspace-scoped provider registration and update flows.
- Shipped capability discovery and capability snapshots.
- Shipped OpenAI-compatible adapter hardening.
- Shipped provider invocation telemetry persistence and hosted RLS posture for the telemetry table.

### Ollama + llama.cpp + vLLM Adapters
- Hardened the local/self-hosted runtime paths onto the stabilized provider contract.
- Added the dedicated `vllm` provider path with provider-native health semantics and registration/config support.
- Extended provider/runtime and pack-compatibility coverage for the local/self-hosted provider surface.

### Model Packs
- Added provider-aware workspace model-pack bindings on top of the shipped provider surface.
- Shipped the first-party `llama`, `qwen`, `gemma`, and `gpt-oss` pack catalog.
- Added pack-aware runtime and briefing defaults plus declarative compatibility enforcement.

### Reference Integrations
- Packaged the shipped continuity, provider, and pack surface into polished external-builder paths.
- Refreshed Hermes and OpenClaw documentation around the shipped one-call continuity and provider/pack baseline.
- Added generic Python and TypeScript reference agent examples plus reproducible demos.

### Logging Safety And Disk Guardrails
- Added explicit logging configuration and moved local/Lite defaults to stdout.
- Disabled access logs by default in Lite/local profile.
- Added bounded rotation when file logging is explicitly enabled.
- Documented the recommended `systemd`/`journald` posture for managed environments.
- Added smoke coverage proving no unbounded local log file is created in `/tmp`.

## Security And Reliability Rules
- Keep user/workspace isolation intact for continuity, provider, runtime, and pilot data.
- Keep agent API keys hashed at rest; raw keys are printed exactly once at creation and never logged.
- Keep provider credentials and secret references out of logs and outward-facing errors.
- Keep connector secrets out of settings rows, event logs, source metadata, artifact metadata, API responses, CLI output, and UI state.
- Keep connector cursors restart-safe and do not advance past failed data unless the skipped item is explicitly safe.
- Preserve approval-bounded execution for consequential side effects.
- Keep capture, mutation, provider, and Hermes sync paths idempotent.
- Preserve append-only evidence where the system depends on auditability.
- Do not let provider-specific behavior fork continuity semantics.
- Do not let model packs bypass provenance, trust, or contradiction rules already enforced by the baseline.
- Keep local/Lite logging bounded and operationally safe by default.

## Testing Strategy
- unit/integration tests for continuity, provider runtime, and API behavior
- provider smoke tests and provider-capability parity checks
- model-pack smoke tests and compatibility-matrix validation
- integration smoke tests for Hermes, OpenClaw, Python example, and TypeScript example paths
- pilot onboarding, linkage, usage-summary, and feedback-flow validation
- logging configuration and `/tmp` safety validation
- vNext live-capture connector smoke and capture-to-brief smoke validation
- vNext connector-hardening, secret-redaction, and dogfood-doctor smoke validation
- release gates remain green across Python, web, Alice Lite, Hermes smoke, and public eval harness
- docs verification is part of feature completion, not cleanup work

## Current Architectural Posture
- `v0.9.4` is the active published release boundary and the latest published release, superseding `v0.9.2` in that role; `v0.9.2` remains published but is no longer the latest.
- `v0.10.0` is the current third-audit remediation candidate over the published `v0.9.4` baseline; unrelated feature work remains paused and `v0.9.3` remains a withdrawn, never-published candidate. Release requires the repaired tree, independent re-review, canonical gates, and protected semantic evidence to pass against one exact clean source SHA and its installed artifacts.
- Alice is now a broader continuity platform with provider/runtime portability, model packs, runnable external-builder integrations, pilot launch/admin support, and safe local logging defaults.
- The continuity substrate remains the same system of record; the delivered work packages that substrate into practical adoption paths without changing the core continuity semantics.
