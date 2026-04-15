# Sprint Packet

## Sprint Title
Phase 13 Closeout + `v0.4.0` Release

## Activation Note
- This packet remains active until the next phase packet is accepted.
- `v0.4.0` is the current public release boundary.
- Phase 13 is shipped.
- Phase 13 sequence shipped as:
  - `P13-S1` One-Call Continuity
  - `P13-S2` Alice Lite
  - `P13-S3` Memory Hygiene + Conversation Health

## Sprint Type
release-closeout

## Sprint Reason
Phase 13 is complete. This packet keeps the active control slot aligned to the shipped `v0.4.0` baseline while the next phase is being defined.

## Git Instructions
- Branch Name: `main`
- Base Branch: `main`
- PR Strategy: none; this is a release-state packet
- Merge Policy: replace this packet when the next phase is accepted

## Baseline To Preserve
- shipped Phases 9-13 baseline
- shipped Bridge `B1` through `B4`
- published `v0.4.0` baseline
- shipped `P13-S1` one-call continuity surface
- shipped `P13-S2` Alice Lite profile
- shipped `P13-S3` hygiene/thread-health visibility
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Preserve a clean release-aligned control state after the completed Phase 13 sequence and before the next phase packet is created.

## In Scope
- release-aligned control-doc truth
- release-aligned version markers
- release evidence and closeout docs
- preserving the shipped baseline until the next phase is accepted

## Out Of Scope
- new feature work
- reopening completed Phase 13 implementation
- speculative next-phase scope before explicit acceptance

## Proposed Files And Modules
- control docs
- release docs
- public version markers
- evidence reports

## Planned Deliverables
- Phase 13 closeout summary
- `v0.4.0` release checklist, tag plan, and runbook
- updated release-aligned canonical docs
- release evidence reports

## Acceptance Criteria
- canonical docs accurately describe the shipped Phase 13 baseline
- release evidence matches exact verification commands
- `v0.4.0` is the active public release boundary
- the packet is safe to leave in place until the next phase packet replaces it

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- full release gates recorded in `BUILD_REPORT.md`

## Control Tower Decisions Needed
- define the next phase before opening another build sprint
- keep future work non-redundant with the shipped Phase 13 boundary

## Exit Condition
This packet stays valid until the next phase packet is accepted and activated.
