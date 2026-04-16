# Sprint Packet

## Sprint Title
P14-S5: Design Partner Launch

## Activation Note
- This packet is active.
- `v0.4.0` is the current public release boundary.
- Phase 14 is active on top of the shipped Phase 13 baseline.
- Phase 14 sequence is fixed for now:
  - `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter: shipped
  - `P14-S2` Ollama + llama.cpp + vLLM Adapters: shipped
  - `P14-S3` Model Packs: shipped
  - `P14-S4` Reference Integrations: shipped
  - `P14-S5` Design Partner Launch: active

## Sprint Type
feature

## Sprint Reason
`P14-S1` through `P14-S4` established the provider contract, local/self-hosted compatibility layer, first-party model-pack defaults, and runnable external-builder paths. `P14-S5` now turns that platform readiness into real-world usage proof and structured launch feedback.

## Git Instructions
- Branch Name: `codex/phase14-s5-design-partner-launch`
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
- shipped `P14-S4` reference integrations, generic examples, and reproducible demo paths
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Turn the shipped Phase 14 platform surface into real usage proof through tracked design-partner onboarding, support, instrumentation, and feedback.

## In Scope
- design-partner objects and workspace linkage
- onboarding workflow and support checklist
- partner usage summaries
- feedback intake path
- partner success dashboard
- case-study template
- first 3 to 5 partner onboardings

## Out Of Scope
- general enterprise governance expansion
- unrelated channel work
- broad marketing-site work beyond what partner launch requires
- retrieval research, graph migration, new channels, marketplace work, or enterprise governance expansion

## Proposed Files And Modules
- `apps/api/src/alicebot_api/`
- `apps/api/alembic/versions/`
- `tests/unit/`
- `tests/integration/`
- `docs/design-partners/`
- launch/runbook/support artifacts
- control docs if baseline status markers need updates

## Planned Deliverables
- design-partner objects and workspace linkage
- onboarding workflow and support checklist
- usage summaries
- feedback intake path
- partner success dashboard
- case-study template
- first 3 to 5 partner onboardings

## Acceptance Criteria
- at least 3 design partners are active or in structured pilot
- usage summaries are visible
- feedback is captured in a structured way
- at least one candidate case study is underway
- the sprint turns the shipped platform surface into usage proof rather than expanding into general enterprise scope

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted unit/integration coverage for design-partner objects, linkage, and feedback paths
- usage-summary and support-flow validation
- launch-runbook and partner-artifact validation

## Control Tower Decisions Needed
- which first 3 to 5 partner pilots are the canonical launch set
- what minimum usage instrumentation is required before counting a pilot as active
- how strict the case-study readiness bar is for phase closeout

## Exit Condition
This sprint is complete when the shipped Phase 14 platform surface is connected to tracked design-partner pilots, structured usage summaries and feedback exist, and at least one candidate case study is underway without drifting into general enterprise expansion.
