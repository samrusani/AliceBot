# Sprint Packet

## Sprint Title
Hotfix: unbounded local log growth can exhaust disk

## Activation Note
- This packet is active.
- `v0.4.0` is the current public release boundary.
- Phase 14 is shipped.
- This is a post-Phase-14 hotfix sprint on top of the shipped baseline.
- Shipped Phase 14 sequence:
  - `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter: shipped
  - `P14-S2` Ollama + llama.cpp + vLLM Adapters: shipped
  - `P14-S3` Model Packs: shipped
  - `P14-S4` Reference Integrations: shipped
  - `P14-S5` Design Partner Launch: shipped

## Sprint Type
bugfix

## Sprint Reason
The shipped local and Lite runtime paths can allow unbounded local log growth. This is an operational defect with disk-exhaustion risk, so it should be handled as a narrow hotfix sprint rather than rolled into a new feature phase.

## Git Instructions
- Branch Name: `codex/hotfix-unbounded-local-log-growth`
- Base Branch: `main`
- PR Strategy: one implementation branch, one PR
- Merge Policy: squash merge after review `PASS` and explicit approval

## Baseline To Preserve
- shipped Phases 9-14 baseline
- shipped Bridge `B1` through `B4`
- published `v0.4.0` baseline
- shipped one-call continuity surface
- shipped Alice Lite profile
- shipped hygiene/thread-health visibility
- shipped `P14-S1` provider contract, capability snapshot, and invocation telemetry baseline
- shipped `P14-S2` local/self-hosted compatibility layer, including the dedicated `vllm` provider path and aligned runtime/pack compatibility hooks
- shipped `P14-S3` provider-aware model-pack bindings, first-party pack catalog, and pack-aware runtime/briefing defaults
- shipped `P14-S4` reference integrations, generic examples, and reproducible demo paths
- shipped `P14-S5` design-partner launch/admin surface
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Eliminate the disk-exhaustion risk from unbounded local logging while preserving the shipped Phase 14 runtime and deployment behavior.

## In Scope
- explicit logging configuration
- stdout as the default logging sink
- access logs disabled by default in Lite/local profile
- bounded rotation when file logging mode is enabled
- systemd/journald deployment guidance
- smoke validation that no unbounded log file is created in `/tmp`

## Out Of Scope
- new product surface
- unrelated refactors
- provider, pack, integration, or design-partner feature expansion
- changes that are not required to remove the logging-growth defect

## Proposed Files And Modules
- `apps/api/src/alicebot_api/`
- local/Lite startup scripts and runtime config
- `tests/unit/`
- `tests/integration/`
- deployment and ops docs
- control docs if baseline status markers need updates

## Planned Deliverables
- explicit logging config
- stdout default instead of file logging
- Lite/local access-log suppression by default
- bounded file rotation when file mode is enabled
- systemd/journald guidance
- smoke test for `/tmp` log-file safety

## Acceptance Criteria
- the default local and Lite paths log to stdout rather than an unbounded local file
- access logs are disabled by default in Lite/local profile
- file logging, when enabled, is rotated and bounded
- deployment docs recommend systemd/journald for managed environments
- a smoke test confirms no unbounded log file is created in `/tmp`
- the fix does not expand the product scope beyond the logging defect

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted unit/integration coverage for logging configuration and Lite/local behavior
- smoke validation for `/tmp` log-file safety
- documentation validation for the recommended systemd/journald path

## Control Tower Decisions Needed
- whether bounded file logging is retained as an opt-in mode or limited to managed deployments only
- what the default rotation size/count should be if file mode remains supported
- whether the hotfix should also update any release runbook or only runtime/deployment docs

## Exit Condition
This sprint is complete when the shipped local/Lite runtime can no longer create unbounded local log growth by default, bounded file logging exists when explicitly enabled, and the `/tmp` smoke test plus deployment docs prove the intended operational posture.
