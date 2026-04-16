# Sprint Packet

## Sprint Title
P14-S2: Ollama + llama.cpp + vLLM Adapters

## Activation Note
- This packet is active.
- `v0.4.0` is the current public release boundary.
- Phase 14 is active on top of the shipped Phase 13 baseline.
- Phase 14 sequence is fixed for now:
  - `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter: shipped
  - `P14-S2` Ollama + llama.cpp + vLLM Adapters: active
  - `P14-S3` Model Packs
  - `P14-S4` Reference Integrations
  - `P14-S5` Design Partner Launch

## Sprint Type
feature

## Sprint Reason
`P14-S1` established the provider contract and telemetry baseline. `P14-S2` now hardens the existing local and self-hosted runtime paths against that contract so later model-pack, integration, and design-partner work sits on compatibility proof instead of assumptions.

## Git Instructions
- Branch Name: `codex/phase14-s2-local-self-hosted-adapters`
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
- shipped `P14-S1` provider contract, capability snapshot, and invocation telemetry baseline
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Harden Alice's existing Ollama, llama.cpp, and vLLM paths onto the stabilized provider contract and prove local/self-hosted compatibility without changing continuity semantics.

## In Scope
- Ollama adapter alignment to the stabilized provider interface
- llama.cpp / llama-server adapter alignment to the stabilized provider interface
- vLLM adapter alignment to the stabilized provider interface
- provider-specific capability mapping cleanup
- consistent telemetry and continuity behavior across the three runtime classes
- local model quickstarts and example configs
- local compatibility smoke tests

## Out Of Scope
- new provider classes beyond what is required to keep the interface stable
- model-pack UX/polish beyond compatibility hooks
- reference integrations
- design-partner workflows
- retrieval research, graph migration, new channels, marketplace work, or enterprise governance expansion

## Proposed Files And Modules
- `apps/api/src/alicebot_api/`
- `apps/api/alembic/versions/`
- `tests/unit/`
- `tests/integration/`
- `docs/` provider/runtime docs
- local/self-hosted runtime smoke helpers
- control docs if baseline status markers need updates

## Planned Deliverables
- Ollama adapter contract alignment
- llama.cpp / llama-server adapter contract alignment
- vLLM adapter contract alignment
- normalized capability mappings and telemetry behavior for local/self-hosted runtimes
- local model quickstarts and example configs
- local compatibility smoke tests

## Acceptance Criteria
- Alice works with a local Ollama deployment through the stabilized provider contract
- Alice works with a llama.cpp-compatible server through the stabilized provider contract
- Alice works with a self-hosted vLLM deployment through the stabilized provider contract
- capability mapping and telemetry behavior are consistent and inspectable across all three
- one-call continuity semantics stay stable across all three local/self-hosted paths
- local quickstarts are reproducible

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted unit/integration coverage for Ollama, llama.cpp, and vLLM adapter behavior
- smoke validation for local/self-hosted runtime paths
- doc/quickstart validation for local runtime setup paths

## Control Tower Decisions Needed
- whether Azure polish is pulled into this sprint or explicitly deferred to later integration/documentation work
- whether any pre-Phase-14 local adapter behavior must be deprecated now instead of carried forward
- what minimum local runtime versions are declared as supported in the Phase 14 docs

## Exit Condition
This sprint is complete when Alice's existing Ollama, llama.cpp, and vLLM paths are aligned to the stabilized provider contract, backed by compatibility proof and local quickstarts, and still preserve one-call continuity semantics.
