# P14-S2 Control Tower Packet

## Sprint
`P14-S2` Ollama + llama.cpp + vLLM Adapters

## Goal
Support the highest-value local and self-hosted inference paths on top of the Phase 14 provider contract.

## Planned Branch
`codex/phase14-s2-local-self-hosted-adapters`

## In Scope
- Ollama adapter
- llama.cpp / llama-server adapter
- vLLM adapter
- provider-specific capability mappings
- local model quickstarts
- example configs
- local compatibility smoke tests

## Out Of Scope
- model-pack UX beyond compatibility hooks
- reference integrations
- design-partner workflows
- unrelated provider expansion

## Acceptance Criteria
- Alice works with local Ollama
- Alice works with llama.cpp-compatible servers
- Alice works with self-hosted vLLM
- continuity semantics stay stable across all three
- local quickstarts are reproducible
