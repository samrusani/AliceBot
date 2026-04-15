# Sprint Packet

## Sprint Title
P13-S1: One-Call Continuity

## Activation Note
- This packet is active.
- `v0.3.2` is the latest published tag.
- Phase 13 is active.
- Phase 13 sequence is fixed for now:
  - `P13-S1` One-Call Continuity
  - `P13-S2` Alice Lite
  - `P13-S3` Memory Hygiene + Conversation Health

## Sprint Type
feature

## Sprint Reason
Phase 12 already shipped the quality substrate:
- hybrid retrieval
- explicit mutation
- contradiction and trust handling
- public evals
- task-adaptive briefing

The first Phase 13 job is to operationalize that work behind one primary integration surface so external agents do not need tool choreography to get strong continuity.

## Git Instructions
- Branch Name: `codex/phase13-s1-one-call-continuity`
- Base Branch: `main`
- PR Strategy: one implementation branch, one PR
- Merge Policy: squash merge after review `PASS` and explicit approval

## Baseline To Preserve
- shipped Phases 9-12 baseline
- shipped Bridge `B1` through `B4`
- published `v0.3.2` baseline
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Create the primary one-call continuity surface:
- API: `POST /v1/continuity/brief`
- CLI: `alice brief`
- MCP: `alice_brief`

This should become the default integration endpoint for external agents and should compose existing retrieval, open-loop, contradiction, trust, and briefing systems into one strong response.

## In Scope
- one-call continuity contract and assembly logic
- `POST /v1/continuity/brief`
- `alice brief`
- `alice_brief`
- supported brief types:
  - `general`
  - `resume`
  - `agent_handoff`
  - `coding_context`
  - `operator_context`
- continuity bundle output including:
  - summary
  - relevant facts
  - recent changes
  - open loops
  - conflicts
  - timeline highlights
  - next suggested action
  - provenance bundle
  - trust posture
- API/CLI/MCP parity tests and integration docs

## Out Of Scope
- Alice Lite packaging/profile work
- hygiene or thread-health dashboards
- new connectors or channels
- new retrieval research
- new provider/runtime substrate work unless directly required for this surface

## Proposed Files And Modules
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/cli.py`
- `apps/api/src/alicebot_api/mcp_tools.py`
- `apps/api/src/alicebot_api/contracts.py`
- one new continuity-brief assembly module if needed
- `docs/integrations/`
- `tests/unit/`
- `tests/integration/`

## Planned Deliverables
- API endpoint `POST /v1/continuity/brief`
- CLI command `alice brief`
- MCP tool `alice_brief`
- one-call response contract
- parity coverage and docs/examples for external runtimes

## Acceptance Criteria
- an external agent can call one primary continuity surface and get a useful continuity bundle
- the bundle includes summary, recent changes, open loops, conflicts, next action, provenance, and trust posture
- the surface composes shipped Phase 12 systems rather than reimplementing them
- API, CLI, and MCP surfaces stay semantically aligned
- docs make this the default integration path for external agents

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted unit/integration coverage for API, CLI, and MCP parity of the new continuity brief surface

## Control Tower Decisions Needed
- default `brief_type` and default inclusion posture for optional sections when the caller does not specify flags
- whether timeline highlights are included by default or only on request
- whether coding/operator context should differ only by selection strategy or also by response shape

## Exit Condition
This sprint is complete when Alice exposes a single primary continuity call across API, CLI, and MCP that meaningfully reduces integration complexity without weakening continuity semantics.
