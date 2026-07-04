# Phase 14 Product Spec

## Phase Theme
Provider Adapters + Design Partner Launch

## Baseline
Phase 13 closed in `v0.4.0` with:
- one-call continuity across API, CLI, and MCP
- Alice Lite local deployment profile
- memory hygiene visibility
- conversation health visibility
- passing release gates and public eval coverage

## Objective
Make Alice the easiest continuity layer to plug into local model runtimes, self-hosted inference servers, hosted enterprise providers, external agent runtimes, and early design-partner workflows.

## Phase Thesis
Alice now has enough continuity depth. Phase 14 should optimize for compatibility, proof, and adoption rather than more memory-substrate research.

## Primary Users
- builders integrating Alice into their own agents or workflows
- self-hosters running Ollama, llama.cpp, or vLLM
- enterprise-curious teams evaluating Azure or OpenAI-compatible infrastructure
- design partners using Alice in production-like conditions

## In Scope
- provider abstraction cleanup and first-class adapters
- model packs with sensible continuity defaults
- polished reference integrations
- design-partner onboarding and usage proof

## Out Of Scope
- new retrieval research
- graph-database migration
- new channels
- marketplace work
- enterprise governance/compliance expansion
- major vertical-agent expansion
- deep browser or action-automation work

## Success Criteria
- Alice runs cleanly with OpenAI-compatible providers, Ollama, llama.cpp, vLLM, and Azure-backed provider paths
- users can bind a model pack and get good continuity defaults without hand tuning
- Hermes and OpenClaw have polished, documented, tested Alice paths
- generic Python and TypeScript examples exist
- at least 3 design partners are active or in structured pilot
- external builders can quickly understand what Alice is, which runtimes it supports, how to integrate it, and how to get first value

## Definition Of Done
Phase 14 is done when Alice works cleanly across major provider/runtime classes, first-party model packs exist for major OSS model families, reference integrations are polished, design partners are live and producing feedback, and Alice is credibly operating as a continuity platform rather than just a repo.
