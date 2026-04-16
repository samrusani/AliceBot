# Roadmap

## Baseline Context (Not Roadmap Work)
- Phase 9: shipped
- Phase 10: shipped
- Phase 11: shipped
- Bridge `B1`-`B4`: shipped
- Bridge Phase (`B1`-`B4`): shipped
- Phase 12: shipped
- Phase 13: shipped
- `v0.4.0`: released

These remain baseline truth and are not future milestones.

## Active Planning Status
- Phase 14 is active.
- `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter is shipped.
- `P14-S2` Ollama + llama.cpp + vLLM Adapters is shipped.
- `P14-S3` Model Packs is shipped.
- `P14-S4` Reference Integrations is the active execution sprint.
- `P14-S5` Design Partner Launch is planned.

## Phase 14 Planned Milestones

### P14-S1: Provider Abstraction Cleanup + OpenAI-Compatible Adapter
- finalize the provider interface and provider registry
- ship provider registration/update flows
- ship capability discovery and provider test/healthcheck paths
- ship OpenAI-compatible adapter normalization and invocation telemetry persistence
- keep one-call continuity working through the provider abstraction

Status: shipped
Release target: internal provider-foundation release candidate

### P14-S2: Ollama + llama.cpp + vLLM Adapters
- harden the existing local and self-hosted runtime paths onto the stabilized provider contract
- normalize capability mappings, telemetry behavior, and continuity semantics across Ollama, llama.cpp, and vLLM
- add local model quickstarts, example configs, and local compatibility smoke tests

Status: shipped
Release target: `v0.5.0-rc1`

### P14-S3: Model Packs
- ship versioned first-party model packs for the main OSS model families
- add pack binding workflow
- integrate pack defaults into runtime invocation and briefing
- publish a compatibility matrix

Status: shipped
Release target: `v0.5.0-rc2`

### P14-S4: Reference Integrations
- polish Hermes and OpenClaw integration paths
- ship generic Python and TypeScript example agents
- add “which integration path should I use?” guidance

Status: active
Release target: `v0.5.0`

### P14-S5: Design Partner Launch
- ship design-partner onboarding, tracking, instrumentation, and feedback workflows
- onboard 3 to 5 design partners into active or structured pilot use
- capture at least 1 candidate case study

Status: planned
Release target: `v0.5.1` or `v0.6.0-beta`

## Sequencing Rules
- Phase 14 is a platform-and-adoption phase.
- Prioritize provider adapters, model packs, reference integrations, and design partner onboarding.
- Do not allow scope drift into new substrate research, new channels, enterprise governance expansion, or major vertical-agent work unless required by a declared Phase 14 deliverable.
- Preserve one-call continuity semantics across provider classes.
- Treat docs as sprint deliverables, not cleanup work.
- Keep `P14-S4` narrow: it should package the shipped continuity/provider/pack surface into runnable integrations, not reopen provider or pack work under a docs label.

## Beyond Phase 14
- No post-Phase-14 feature plan is currently defined.
- The next step after Phase 14 is to evaluate design-partner proof, release posture, and the next phase boundary.
