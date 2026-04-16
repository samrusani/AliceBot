# Current State

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- Phase 12 is shipped.
- Phase 13 is shipped.
- Phase 14 is shipped.
- `HF-001` Logging Safety And Disk Guardrails is shipped.
- `v0.5.1` is the latest published tag.
- No post-Phase-14 build sprint is active yet.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The shipped baseline includes hybrid retrieval and reranking with traces, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- The shipped baseline includes one-call continuity across API, CLI, and MCP.
- The shipped baseline includes the Alice Lite startup/profile path.
- The shipped baseline includes memory hygiene and thread/conversation health visibility.
- The shipped baseline includes the Phase 14 provider contract, workspace-scoped provider registration/update flows, provider capability snapshots, invocation telemetry persistence, and the OpenAI-compatible adapter hardening from `P14-S1`.
- The shipped baseline includes the Phase 14 local/self-hosted compatibility layer from `P14-S2`, including the dedicated `vllm` provider path, aligned health semantics, and pack-compatibility/runtime coverage for the local/self-hosted provider surface.
- The shipped baseline includes provider-aware model-pack bindings, the first-party `llama` / `qwen` / `gemma` / `gpt-oss` catalog, and pack-aware runtime/briefing defaults from `P14-S3`.
- The shipped baseline includes polished Hermes/OpenClaw reference integrations, generic Python/TypeScript examples, and reproducible reference demos from `P14-S4`.
- The shipped baseline includes the design-partner launch/admin surface from `P14-S5`.
- The shipped baseline includes logging safety and disk guardrails from `HF-001`, including stdout-by-default local logging, disabled local/Lite access logs by default, and bounded file logging when explicitly enabled.
- `v0.5.1` is the current public pre-1.0 release boundary for that shipped baseline.

## Phase Transition Note
- Phase 14 is complete as a feature phase.
- `HF-001` is complete as a defect-only hardening sprint.
- `v0.5.1` closes the shipped Phase 14 platform plus the post-phase logging safety hardening.

## Immediate Control Tower Decisions Needed
- Define the next phase on top of the shipped `v0.5.1` baseline.
- Avoid reopening completed Phase 14 or `HF-001` scope unless a concrete defect or release-readiness issue is identified.
