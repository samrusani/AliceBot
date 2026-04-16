# Current State

This file is a synced repo-root copy for planning visibility.
Canonical handoff state lives at [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md).

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- Phase 12 is shipped.
- Phase 13 is shipped.
- `v0.4.0` is the latest published tag.
- Phase 14 is shipped.
- `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter is shipped.
- `P14-S2` Ollama + llama.cpp + vLLM Adapters is shipped.
- `P14-S3` Model Packs is shipped.
- `P14-S4` Reference Integrations is shipped.
- `P14-S5` Design Partner Launch is shipped.
- `HF-001` Logging Safety And Disk Guardrails is the active execution sprint.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The shipped baseline includes hybrid retrieval and reranking with traces, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- The shipped baseline includes one-call continuity across API, CLI, and MCP.
- The shipped baseline includes the Alice Lite startup/profile path.
- The shipped baseline includes memory hygiene and thread/conversation health visibility.
- Phase 14 shipped baseline now also includes the stabilized provider contract, workspace-scoped provider registration/update flows, provider capability snapshots, invocation telemetry persistence, and the OpenAI-compatible adapter hardening delivered in `P14-S1`.
- Phase 14 shipped baseline now also includes the local/self-hosted compatibility layer from `P14-S2`, including the dedicated `vllm` provider path, aligned health semantics, and pack-compatibility/runtime coverage for the shipped local/self-hosted provider surface.
- Phase 14 shipped baseline now also includes provider-aware model-pack bindings, the first-party `llama` / `qwen` / `gemma` / `gpt-oss` catalog, and pack-aware runtime/briefing defaults delivered in `P14-S3`.
- Phase 14 shipped baseline now also includes polished Hermes/OpenClaw reference integrations, generic Python/TypeScript examples, and reproducible reference demos delivered in `P14-S4`.
- Phase 14 shipped baseline now also includes the design-partner launch/admin surface delivered in `P14-S5`.
- `v0.4.0` is the current public pre-1.0 release boundary for that shipped baseline.

## Phase Transition Note
- Phase 13 is complete and remains baseline truth.
- Phase 14 starts from the shipped `v0.4.0` baseline.
- Phase 14 is complete as a feature phase.
- `P14-S1` is complete and establishes the provider contract, capability snapshot, and invocation telemetry baseline for the rest of the phase.
- `P14-S2` is complete and closed the local/self-hosted compatibility sprint without reopening provider-foundation work.
- `P14-S3` is complete and turned the shipped provider surface into usable pack defaults without reopening provider work.
- `P14-S4` is complete and turned the shipped surface into runnable adoption paths for external builders.
- `P14-S5` is complete and turns the shipped Phase 14 platform into tracked pilot adoption and launch evidence.
- `HF-001` is a post-phase bugfix sprint focused only on logging safety and disk guardrails for local/Lite runtime behavior.

## Immediate Control Tower Decisions Needed
- Decide whether bounded file logging remains an opt-in supported mode or is restricted to managed deployments.
- Decide the default file-rotation size/count if file logging remains supported.
- Decide whether the hotfix should also update release/runbook docs beyond runtime/deployment guidance.
