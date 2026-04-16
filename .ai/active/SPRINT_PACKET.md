# Sprint Packet

## Sprint Title
Phase 14 Closeout + `v0.5.1` Release

## Activation Note
- This packet remains active until the next phase packet is accepted.
- `v0.5.1` is the current public release boundary.
- Phase 14 is shipped.
- `HF-001` Logging Safety And Disk Guardrails is shipped.
- Shipped Phase 14 sequence:
  - `P14-S1` Provider Abstraction Cleanup + OpenAI-Compatible Adapter
  - `P14-S2` Ollama + llama.cpp + vLLM Adapters
  - `P14-S3` Model Packs
  - `P14-S4` Reference Integrations
  - `P14-S5` Design Partner Launch

## Sprint Type
release-closeout

## Sprint Reason
Phase 14 and the post-phase logging hotfix are complete. This packet keeps the active control slot aligned to the shipped `v0.5.1` baseline while the next phase is being defined.

## Git Instructions
- Branch Name: `main`
- Base Branch: `main`
- PR Strategy: none; this is a release-state packet
- Merge Policy: replace this packet when the next phase packet is accepted

## Baseline To Preserve
- shipped Phases 9-14 baseline
- shipped Bridge `B1` through `B4`
- published `v0.5.1` baseline
- shipped one-call continuity surface
- shipped Alice Lite profile
- shipped hygiene/thread-health visibility
- shipped Phase 14 provider contract, local/self-hosted compatibility, model packs, reference integrations, and design-partner launch surface
- shipped `HF-001` logging safety and disk guardrails
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Preserve a clean release-aligned control state after the completed Phase 14 sequence and the shipped post-phase logging hotfix.

## In Scope
- release-aligned control-doc truth
- release-aligned version markers
- phase closeout and release docs
- preserving the shipped `v0.5.1` baseline until the next phase is accepted

## Out Of Scope
- new feature work
- reopening completed Phase 14 implementation
- speculative next-phase scope before explicit acceptance

## Proposed Files And Modules
- control docs
- release docs
- public version markers
- evidence reports

## Planned Deliverables
- Phase 14 closeout summary
- `v0.5.1` release checklist, tag plan, and runbook
- updated release-aligned canonical docs
- updated version metadata and release tag

## Acceptance Criteria
- canonical docs accurately describe the shipped Phase 14 plus `HF-001` baseline
- version markers align to `v0.5.1`
- `v0.5.1` is the active public release boundary
- the packet is safe to leave in place until the next phase packet replaces it

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`

## Control Tower Decisions Needed
- define the next phase before opening another build sprint
- keep future work non-redundant with the shipped Phase 14 + `HF-001` boundary

## Exit Condition
This packet stays valid until the next phase packet is accepted and activated.
