# Sprint Packet

## Sprint Title
P14-S3: Model Packs

## Activation Note
- This packet is active.
- `v0.4.0` is the current public release boundary.
- Phase 14 is active on top of the shipped Phase 13 baseline.
- Phase 14 sequence is fixed for now:
  - `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter: shipped
  - `P14-S2` Ollama + llama.cpp + vLLM Adapters: shipped
  - `P14-S3` Model Packs: active
  - `P14-S4` Reference Integrations
  - `P14-S5` Design Partner Launch

## Sprint Type
feature

## Sprint Reason
`P14-S1` and `P14-S2` established the provider contract, telemetry baseline, and local/self-hosted compatibility layer. `P14-S3` now turns that provider surface into usable defaults so external builders do not need to hand-tune pack behavior per workspace.

## Git Instructions
- Branch Name: `codex/phase14-s3-model-packs`
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
- shipped `P14-S2` local/self-hosted compatibility layer, including the dedicated `vllm` provider path and aligned runtime/pack compatibility hooks
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Make common model families easy to use with sensible continuity defaults on top of the shipped provider/runtime baseline.

## In Scope
- model-pack schema and storage hardening where needed
- model-pack API and workspace pack-binding workflow
- first-party packs for Llama, Qwen, Gemma, and `gpt-oss`
- pack-aware invocation and briefing defaults
- compatibility matrix docs
- pack smoke tests

## Out Of Scope
- provider-contract redesign
- new provider classes beyond what is required to support declared pack families
- reference integrations
- design-partner workflows
- retrieval research, graph migration, new channels, marketplace work, or enterprise governance expansion

## Proposed Files And Modules
- `apps/api/src/alicebot_api/`
- `apps/api/alembic/versions/`
- `tests/unit/`
- `tests/integration/`
- `docs/` model-pack and compatibility docs
- control docs if baseline status markers need updates

## Planned Deliverables
- model-pack schema and API surface
- workspace pack binding flow
- first-party pack definitions for Llama, Qwen, Gemma, and `gpt-oss`
- pack-aware runtime and briefing defaults
- compatibility matrix docs
- pack smoke tests

## Acceptance Criteria
- a workspace can bind a provider to a pack
- pack defaults affect briefing and runtime behavior correctly
- first-party packs are versioned and documented
- users get good defaults without manual tuning
- pack behavior composes the shipped provider/runtime baseline instead of reopening provider work

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted unit/integration coverage for model-pack storage, binding, and runtime/briefing defaults
- pack smoke validation against the shipped provider/runtime surface
- compatibility-matrix and pack-doc validation

## Control Tower Decisions Needed
- whether DeepSeek or Mistral stay explicitly deferred after the first-party pack set ships
- how strict the initial pack-to-provider compatibility matrix is at launch
- which pack quirks are allowed as declarative defaults versus requiring runtime code changes

## Exit Condition
This sprint is complete when workspaces can bind documented first-party packs to the shipped provider/runtime baseline, pack-aware defaults behave correctly, and the result reduces manual tuning without creating a second continuity model.
