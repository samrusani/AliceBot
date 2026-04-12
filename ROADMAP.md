# Roadmap

## Planning Basis

- Phase 10 is the next delivery phase: Alice Connect. (historical marker retained for control-doc truth checks)
- P10-S1: Identity + Workspace Bootstrap (historical marker retained for control-doc truth checks)
- Phase 10 is complete and shipped baseline truth.
- This roadmap tracks future delivery only (Phase 11 onward).

## Phase 11 Objective

Make Alice the continuity layer that works across local, self-hosted, enterprise, and external-agent model stacks via provider adapters and model packs.

## Phase 11 Milestones

### P11-S1: Provider Abstraction + OpenAI-Compatible Base

- provider interface, registry, config schema
- OpenAI-compatible base adapter
- capability discovery and usage normalization
- runtime invoke/test APIs and harness

### P11-S2: Ollama + llama.cpp Adapters

- local adapter implementations
- model enumeration + healthchecks
- local setup docs and end-to-end examples

### P11-S3: vLLM Adapter + Self-Hosted Performance Path

- vLLM adapter support via same abstraction
- provider-specific option passthrough boundary
- normalized latency/usage telemetry for vLLM calls

### P11-S4: Model Packs Tier 1

- first-party packs: Llama, Qwen, Gemma, gpt-oss
- pack catalog + versioning + binding APIs
- pack-driven context/tool/response behavior

### P11-S5: Azure Adapter + AutoGen Integration

- Azure OpenAI / Azure Foundry adapter
- enterprise credential/auth hardening
- AutoGen integration guide and sample path

### P11-S6: Model Packs Tier 2 + Launch Clarity Assets

- packs: DeepSeek, Kimi, Mistral
- runtime and pack compatibility matrices
- docs for local, self-hosted, enterprise, and external-agent paths

### P11-R1: Provider Runtime Hardening (Security Remediation Sprint 1)

- outbound URL validation and SSRF resistance for provider registration and runtime/test calls
- sanitized upstream provider error surfaces for API responses and persistence
- URL userinfo rejection plus defensive redaction on serialized provider rows

## Sequencing Rules

- Stabilize abstraction and normalization before adding provider breadth.
- Complete tier-1 providers before tier-2 model-pack breadth.
- Ship tier-1 packs cleanly before expanding long-tail packs.
- Treat enterprise adapter and credential hardening as a release gate, not polish.
- Clear provider-runtime security holds before Phase 11 release closeout.

## Phase 11 Exit

Phase 11 exits when users can choose model backends and agent runtimes without changing Alice continuity semantics, and supported paths are operationally documented.

## Roadmap Guardrails

- Keep roadmap future-facing; move completed work to handoff/archive docs.
- Do not restate shipped Phase 10 scope as future milestones.
- Avoid provider/model sprawl not justified by adapter and pack contracts.
