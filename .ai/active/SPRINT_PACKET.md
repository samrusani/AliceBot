# Sprint Packet

## Sprint Title
P13-S3: Memory Hygiene + Conversation Health

## Activation Note
- This packet is active.
- `v0.3.2` is the latest published tag.
- Phase 13 is active.
- Phase 13 sequence is fixed for now:
  - `P13-S1` One-Call Continuity (shipped)
  - `P13-S2` Alice Lite (shipped)
  - `P13-S3` Memory Hygiene + Conversation Health

## Sprint Type
feature

## Sprint Reason
`P13-S1` already reduced integration complexity, and `P13-S2` already reduced startup friction. The final Phase 13 sprint should make memory quality and conversation risk visible enough that Alice feels polished, legible, and operationally trustworthy.

## Git Instructions
- Branch Name: `codex/phase13-s3-memory-hygiene-conversation-health`
- Base Branch: `main`
- PR Strategy: one implementation branch, one PR
- Merge Policy: squash merge after review `PASS` and explicit approval

## Baseline To Preserve
- shipped Phases 9-12 baseline
- shipped Bridge `B1` through `B4`
- published `v0.3.2` baseline
- shipped `P13-S1` one-call continuity surface
- shipped `P13-S2` Alice Lite profile
- no semantic fork between API, CLI, MCP, hosted, provider-runtime, and Hermes paths

## Exact Goal
Make memory hygiene and conversation health visible and actionable:
- duplicates
- stale facts
- unresolved contradictions
- weakly trusted memory
- review queue pressure
- recent threads
- stale threads
- risky threads
- thread health posture

This sprint should improve operational legibility without adding new substrate work.

## In Scope
- hygiene visibility for duplicates, stale facts, unresolved contradictions, weak trust, and review pressure
- conversation/thread health visibility for recent, stale, and risky threads
- bounded UI/API/CLI surfaces needed to inspect those states
- prioritization or summary views that make the quality/risk posture obvious
- tests and docs for the new hygiene and conversation-health surfaces

## Out Of Scope
- new connectors or channels
- new retrieval research
- graph or persistence rearchitecture
- new provider/runtime substrate work
- deeper Alice Lite packaging work
- new continuity-surface work beyond what is required to expose the quality/health views

## Proposed Files And Modules
- `apps/api/src/alicebot_api/`
- `apps/web/` if UI surfaces are part of the implemented sprint
- `docs/memory/` or related docs paths
- `tests/unit/`
- `tests/integration/`
- control docs if sprint status updates are needed

## Planned Deliverables
- memory hygiene surfaces
- conversation health surfaces
- prioritization/summary outputs for stale, risky, contradictory, or review-heavy states
- docs and tests that make those surfaces usable and trustworthy

## Acceptance Criteria
- duplicates, stale facts, unresolved contradictions, weak trust, and review pressure are visible and actionable
- stale or risky conversations are visible without deep system knowledge
- the sprint improves quality visibility without introducing new substrate work
- the shipped one-call continuity surface and Alice Lite path remain intact and non-forked
- the result feels like visibility/polish work, not a fourth hidden architecture sprint

## Required Verification
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- targeted unit/integration coverage for the hygiene and conversation-health surfaces
- any UI/API/CLI verification required by the implemented sprint surface

## Control Tower Decisions Needed
- threshold model for risky/stale thread health
- whether review queue pressure is summarized only at a global level or also per thread/workspace slice
- whether the first shipped thread-health surface is API-only, UI-visible, or both

## Exit Condition
This sprint is complete when Alice makes memory hygiene and conversation health clearly visible and operationally useful without weakening the shipped continuity semantics or expanding into new substrate work.
