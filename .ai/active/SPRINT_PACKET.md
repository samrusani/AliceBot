# Sprint Packet

## Sprint Title
P14-S1: Provider Abstraction Cleanup + OpenAI-Compatible Adapter

## Activation Note
- This packet is active.
- `v0.4.0` is the current public release boundary.
- Phase 14 is active on top of the shipped Phase 13 baseline.
- Phase 14 sequence is fixed for now:
  - `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter
  - `P14-S2` Ollama + llama.cpp + vLLM Adapters
  - `P14-S3` Model Packs
  - `P14-S4` Reference Integrations
  - `P14-S5` Design Partner Launch

## Sprint Type
feature

## Sprint Reason
Alice already has strong continuity depth. The next constraint is compatibility and adoption. `P14-S1` creates the stable provider foundation that later local adapters, model packs, reference integrations, and design-partner workflows will depend on.

## Git Instructions
- Branch Name: `codex/phase14-s1-provider-foundation-openai-compatible`
- Base Branch: `main`
- PR Strategy: one implementation branch, one PR
- Merge Policy: squash merge after review `PASS` and explicit approval

## Baseline To Preserve
- shipped Phases 9-13 baseline
- shipped Bridge `B1` through `B4`
- published `v0.4.0` baseline
- shipped one-call continuity surface
- shipped Alice Lite profile
- shipped hygiene/thread-health visibility
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Create the stable provider foundation and unlock any OpenAI-compatible runtime without changing continuity semantics.

## In Scope
- provider abstraction cleanup
- finalized provider interface in code
- provider registry and workspace-scoped provider management flows
- provider capability discovery
- OpenAI-compatible adapter
- normalized runtime invocation telemetry
- provider configuration docs
- smoke tests against a compliant endpoint

## Out Of Scope
- Ollama, llama.cpp, and vLLM adapters beyond what is required to keep the interface general
- model-pack UX/polish beyond foundation compatibility hooks
- reference integrations
- design-partner workflows
- retrieval research, graph migration, new channels, marketplace work, or enterprise governance expansion

## Proposed Files And Modules
- `apps/api/src/alicebot_api/`
- `apps/api/alembic/versions/`
- `tests/unit/`
- `tests/integration/`
- `docs/` provider/runtime docs
- control docs if baseline status markers need updates

## Planned Deliverables
- stable provider adapter interface
- provider registration/update flows
- capability check endpoint
- OpenAI-compatible provider adapter
- normalized runtime invocation telemetry persistence
- provider configuration docs
- provider-level smoke tests

## Acceptance Criteria
- a provider can be registered via API and config
- Alice can call a compliant OpenAI-compatible endpoint
- provider capabilities are stored and visible
- runtime invocation telemetry is persisted
- one-call continuity works cleanly through the provider abstraction

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted unit/integration coverage for provider registration, capability discovery, and runtime invocation telemetry
- smoke tests against a compliant OpenAI-compatible endpoint

## Control Tower Decisions Needed
- exact provider capability surface stored in `provider_capabilities`
- whether provider registration remains API-first, config-first, or explicitly dual-path from the first sprint
- how much Azure-specific capability shape is deferred while keeping the interface stable

## Exit Condition
This sprint is complete when Alice has a stable provider abstraction, a working OpenAI-compatible adapter, visible provider capabilities, persisted invocation telemetry, and preserved one-call continuity semantics.
