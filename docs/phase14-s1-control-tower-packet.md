# P14-S1 Control Tower Packet

## Sprint
`P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter

## Goal
Create the stable provider foundation and unlock any OpenAI-compatible runtime without changing continuity semantics.

## Branch
`codex/phase14-s1-provider-foundation-openai-compatible`

## In Scope
- define the stable provider adapter interface in code
- build provider registration and update flows
- implement provider capability discovery
- implement the OpenAI-compatible adapter
- normalize usage, latency, and error telemetry
- document provider configuration
- add provider-level smoke tests

## Out Of Scope
- local adapter delivery beyond keeping the interface general
- model-pack UX
- reference integrations
- design-partner operations

## Acceptance Criteria
- a provider can be registered via API and config
- Alice can invoke a compliant OpenAI-compatible endpoint
- provider capabilities are stored and visible
- invocation telemetry is persisted
- one-call continuity works through the provider abstraction

## Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted provider runtime tests
- compliant-endpoint smoke coverage
