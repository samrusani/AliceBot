# Product Brief

## Product Summary
Alice is a pre-1.0 continuity platform for AI agents and agent-assisted workflows. It provides typed memory, provenance, correction-aware recall, open-loop tracking, resumable context, provider/runtime portability, and integration paths for external agent runtimes.

## Shipped Baseline
- Phase 9 shipped the continuity core, CLI, MCP, importers, approvals, and evaluation foundation.
- Phase 10 shipped the hosted/product layer, identity/workspace model, and channel surfaces.
- Phase 11 shipped provider runtime foundations, initial provider adapters, and model-pack primitives.
- Bridge `B1` through `B4` shipped Hermes lifecycle hooks, auto-capture, review flow, explainability, packaging docs, smoke validation, and demo path.
- Phase 12 shipped hybrid retrieval and reranking, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- Phase 13 shipped one-call continuity, Alice Lite, and memory hygiene / conversation health visibility.
- `v0.4.0` is the latest published pre-1.0 release tag.

## Current Repo Posture
- Phase 14 is active.
- `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter is the active execution sprint.
- `P14-S2` Ollama + llama.cpp + vLLM Adapters is planned.
- `P14-S3` Model Packs is planned.
- `P14-S4` Reference Integrations is planned.
- `P14-S5` Design Partner Launch is planned.

## Active Phase
### Phase 14: Provider Adapters + Design Partner Launch
Turn Alice from a strong continuity system into a practical integration platform for local runtimes, self-hosted inference servers, enterprise-curious teams, and early design partners.

## Why This Phase Now
Alice now has enough depth in continuity semantics. The next constraint is compatibility, proof, and adoption:
- model/runtime compatibility
- first-class provider adapters
- plug-and-play model packs
- reference integrations
- design partner onboarding
- usage proof in real environments

## Primary Users
- Builders who want to plug Alice into their own agents or workflows.
- Self-hosters running local or private model stacks through Ollama, llama.cpp, or vLLM.
- Enterprise-curious teams evaluating Alice with Azure or OpenAI-compatible infrastructure.
- Design partners using Alice in production-like environments and generating adoption proof.

## In Scope For Phase 14
- Stable provider abstraction and workspace-scoped provider management.
- First-class adapters for OpenAI-compatible, Ollama, llama.cpp, vLLM, and Azure-backed paths.
- Declarative, versioned model packs with workspace binding and sensible defaults.
- Reference integrations for Hermes, OpenClaw, generic Python agents, and generic TypeScript agents.
- Design-partner onboarding, tracking, instrumentation, and structured feedback capture.

## Non-Goals
- New retrieval research.
- Graph-database migration.
- New channels.
- Marketplace work.
- Enterprise governance/compliance expansion.
- Major vertical-agent work.
- Deep browser/action automation.

## Success Criteria
- Alice runs cleanly with OpenAI-compatible providers, Ollama, llama.cpp, vLLM, and Azure-backed paths.
- Users can bind a model pack and get sensible continuity defaults without hand tuning.
- Hermes and OpenClaw have polished, documented, and tested Alice paths.
- Generic Python and TypeScript examples exist and are reproducible.
- At least 3 design partners are onboarded or in active pilot, with concrete usage evidence and at least 1 strong reference workflow.

## Immediate Product Posture
- `v0.4.0` remains the current public release boundary.
- Phase 14 is a platform-and-adoption phase on top of the shipped Phase 13 baseline.
- No Phase 14 deliverable is shipped yet; `P14-S1` is the first execution sprint.
