# Sprint Packet

## Sprint Title
P14-S4: Reference Integrations

## Activation Note
- This packet is active.
- `v0.4.0` is the current public release boundary.
- Phase 14 is active on top of the shipped Phase 13 baseline.
- Phase 14 sequence is fixed for now:
  - `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter: shipped
  - `P14-S2` Ollama + llama.cpp + vLLM Adapters: shipped
  - `P14-S3` Model Packs: shipped
  - `P14-S4` Reference Integrations: active
  - `P14-S5` Design Partner Launch

## Sprint Type
feature

## Sprint Reason
`P14-S1` through `P14-S3` established the provider contract, local/self-hosted compatibility layer, and first-party model-pack defaults. `P14-S4` now turns that shipped substrate into runnable adoption paths for external builders.

## Git Instructions
- Branch Name: `codex/phase14-s4-reference-integrations`
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
- shipped `P14-S3` provider-aware model-pack bindings, first-party pack catalog, and pack-aware runtime/briefing defaults
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Make Alice clearly adoptable by external agent builders without reopening provider or model-pack substrate work.

## In Scope
- Hermes integration docs refresh around the shipped one-call continuity and pack/provider surface
- OpenClaw integration docs refresh around import/augmentation plus one-call continuity
- generic Python agent example
- generic TypeScript agent example
- integration-path guidance
- reproducible demos for major integration paths

## Out Of Scope
- new provider/runtime substrate work unless strictly required to support the shipped integration contract
- new pack families or pack-schema redesign unless strictly required to document the shipped surface
- design-partner workflows
- retrieval research, graph migration, new channels, marketplace work, or enterprise governance expansion

## Proposed Files And Modules
- `docs/integrations/`
- `docs/examples/`
- `scripts/` demo or smoke helpers where needed
- targeted example/runtime test coverage
- control docs if baseline status markers need updates

## Planned Deliverables
- polished Hermes integration docs
- polished OpenClaw integration docs
- generic Python agent example
- generic TypeScript agent example
- integration-path guidance
- reproducible demos for major integration paths

## Acceptance Criteria
- external builders can integrate Alice into Hermes from docs
- external builders can integrate Alice into OpenClaw from docs
- generic Python and TypeScript examples run successfully
- at least one reproducible demo exists per major integration path
- the sprint packages the shipped provider/pack/continuity surface instead of adding a new runtime substrate

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted coverage for new integration examples and demo helpers
- integration-doc validation for Hermes and OpenClaw paths
- reproducible demo validation for the declared major integration paths

## Control Tower Decisions Needed
- whether AutoGen stays deferred or becomes an extra reference example if capacity remains
- which integration path is the default recommendation for each user profile
- how much demo/video artifact work is required in-sprint versus follow-up packaging

## Exit Condition
This sprint is complete when the shipped provider/pack/continuity baseline is exposed through polished Hermes and OpenClaw docs, runnable Python and TypeScript examples, and reproducible integration demos without creating new substrate scope.
