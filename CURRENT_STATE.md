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
- Phase 14 is active.
- `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter is shipped.
- `P14-S2` Ollama + llama.cpp + vLLM Adapters is the active execution sprint.
- `P14-S3` through `P14-S5` are planned and scoped.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The shipped baseline includes hybrid retrieval and reranking with traces, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- The shipped baseline includes one-call continuity across API, CLI, and MCP.
- The shipped baseline includes the Alice Lite startup/profile path.
- The shipped baseline includes memory hygiene and thread/conversation health visibility.
- Phase 14 shipped baseline now also includes the stabilized provider contract, workspace-scoped provider registration/update flows, provider capability snapshots, invocation telemetry persistence, and the OpenAI-compatible adapter hardening delivered in `P14-S1`.
- `v0.4.0` is the current public pre-1.0 release boundary for that shipped baseline.

## Phase Transition Note
- Phase 13 is complete and remains baseline truth.
- Phase 14 starts from the shipped `v0.4.0` baseline.
- Phase 14 is focused on compatibility, packaging, reference integrations, and design-partner proof.
- `P14-S1` is complete and establishes the provider contract, capability snapshot, and invocation telemetry baseline for the rest of the phase.
- `P14-S2` is intentionally not a second provider-foundation sprint; it is the contract-alignment, compatibility-proof, and documentation sprint for the already-existing local/self-hosted runtime paths.

## Immediate Control Tower Decisions Needed
- Lock the first-party pack set for the initial Phase 14 model-pack release.
- Decide whether Azure polish is pulled fully into `P14-S2` or held to the later integration/documentation layer.
- Select the first 3 to 5 design partners and their initial pilot scopes early enough for `P14-S5`.
