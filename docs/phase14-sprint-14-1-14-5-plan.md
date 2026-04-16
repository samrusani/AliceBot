# Phase 14 Sprint Plan

## Sequence
- `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter
- `P14-S2` Ollama + llama.cpp + vLLM Adapters
- `P14-S3` Model Packs
- `P14-S4` Reference Integrations
- `P14-S5` Design Partner Launch

This sequence is intentionally non-redundant:
- `P14-S1` stabilizes the provider contract and telemetry baseline
- `P14-S2` proves local and self-hosted compatibility on top of that contract
- `P14-S3` turns raw provider support into usable defaults
- `P14-S4` makes adoption concrete for external builders
- `P14-S5` turns technical readiness into real usage proof

## P14-S1: Provider Abstraction Cleanup + OpenAI-Compatible Adapter

### Objective
Create the stable provider foundation and unlock any OpenAI-compatible runtime.

### Deliverables
- finalized provider interface
- provider registry
- provider capability discovery
- OpenAI-compatible adapter
- invocation telemetry normalization
- provider configuration docs
- provider smoke tests

### Dependencies
None

### Release Target
Internal provider-foundation release candidate

### Status
Shipped

## P14-S2: Ollama + llama.cpp + vLLM Adapters

### Objective
Support the most important local and self-hosted inference paths without semantic drift.

### Deliverables
- Ollama adapter
- llama.cpp-compatible adapter
- vLLM adapter
- local model quickstart docs
- example configs
- local compatibility smoke tests

### Dependencies
`P14-S1`

### Release Target
`v0.5.0-rc1`

### Status
Shipped

## P14-S3: Model Packs

### Objective
Make common model families easy to use with sensible continuity defaults.

### Deliverables
- model-pack schema and API
- workspace pack binding workflow
- first-party packs for Llama, Qwen, Gemma, and `gpt-oss`
- pack compatibility matrix
- pack smoke tests

### Dependencies
`P14-S1`, `P14-S2`

### Release Target
`v0.5.0-rc2`

### Status
Shipped

## P14-S4: Reference Integrations

### Objective
Make Alice clearly adoptable by external agent builders.

### Deliverables
- polished Hermes integration docs
- polished OpenClaw integration docs
- generic Python agent example
- generic TypeScript agent example
- integration-path guidance
- reproducible demos for major paths

### Dependencies
`P14-S1` through `P14-S3`

### Release Target
`v0.5.0`

### Status
Active

## P14-S5: Design Partner Launch

### Objective
Move from platform readiness to real-world usage proof.

### Deliverables
- design-partner onboarding workflow
- pilot support checklist
- usage instrumentation
- partner feedback path
- partner success dashboard
- case-study template
- first 3 to 5 structured onboardings

### Dependencies
`P14-S1` through `P14-S4`

### Release Target
`v0.5.1` or `v0.6.0-beta`

### Status
Planned
