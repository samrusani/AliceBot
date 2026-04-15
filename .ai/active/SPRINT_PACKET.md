# Sprint Packet

## Sprint Title
P13-S2: Alice Lite

## Activation Note
- This packet is active.
- `v0.3.2` is the latest published tag.
- Phase 13 is active.
- Phase 13 sequence is fixed for now:
  - `P13-S1` One-Call Continuity (shipped)
  - `P13-S2` Alice Lite
  - `P13-S3` Memory Hygiene + Conversation Health

## Sprint Type
feature

## Sprint Reason
`P13-S1` already shipped the one-call continuity surface. The next job is to make Alice easier to start, lighter to run locally, and faster to understand in the first ten minutes without creating a second product or weakening semantics.

## Git Instructions
- Branch Name: `codex/phase13-s2-alice-lite`
- Base Branch: `main`
- PR Strategy: one implementation branch, one PR
- Merge Policy: squash merge after review `PASS` and explicit approval

## Baseline To Preserve
- shipped Phases 9-12 baseline
- shipped Bridge `B1` through `B4`
- published `v0.3.2` baseline
- shipped `P13-S1` one-call continuity surface
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Create Alice Lite as a lighter deployment and onboarding profile:
- one-command local startup
- smaller-footprint deployment profile
- simplified quickstart
- sample workspace/bootstrap path
- faster first useful result

Alice Lite must use the same continuity semantics and the same one-call continuity entrypoint already shipped in `P13-S1`.

## In Scope
- lighter local startup path
- smaller-footprint profile for local/dev use
- quickstart and first-result tightening
- sample workspace/bootstrap flow
- docs and scripts that make the one-call continuity surface the default demo/integration entrypoint
- startup/smoke verification for the Lite profile

## Out Of Scope
- hygiene or thread-health dashboards
- new connectors or channels
- new retrieval research
- graph or persistence rearchitecture
- SQLite or embedded-mode redesign unless it is strictly necessary and semantics remain intact
- new provider/runtime substrate work unless directly required for the lighter profile

## Proposed Files And Modules
- `README.md`
- `docs/quickstart/`
- `scripts/`
- local startup/profile config files
- `docker-compose` / deployment-profile files if needed
- startup/smoke tests
- docs that describe Lite as a profile, not a separate product

## Planned Deliverables
- one-command local start for Alice Lite
- smaller-footprint local/dev profile
- simplified quickstart and fast first useful result
- docs/examples that use the shipped one-call continuity surface as the default Alice demo path
- smoke coverage for the Lite path

## Acceptance Criteria
- a solo builder can start Alice more easily through a lighter local path
- Alice Lite preserves the same continuity semantics as the full baseline
- the shipped one-call continuity surface remains the default integration/demo entrypoint
- quickstart and first-result path are materially simpler than before
- Lite is clearly documented as a deployment profile, not a separate product

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted startup/smoke coverage for the Lite path
- any docs/quickstart verification required by the implemented Lite profile

## Control Tower Decisions Needed
- whether Alice Lite can reduce services or bootstrap steps without harming semantics or release credibility
- whether Lite is strictly Docker-profile based or also exposes a scripted local bootstrap path
- what the canonical "first useful result" flow is for Lite

## Exit Condition
This sprint is complete when Alice offers a meaningfully simpler local/dev startup path and first-run experience while preserving the shipped continuity semantics and one-call continuity surface.
