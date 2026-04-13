# Product Brief

## Product Summary
Alice is a shipped continuity platform (Phases 9-11). The new bridge-phase product scope is **Hermes Auto-Capture**: automatic continuity prefetch and post-turn capture through a Hermes memory provider, with MCP tools kept for explicit deep workflows.

## Who It Is For
- Hermes users who want continuity without manually calling memory tools every turn.
- Teams already using Alice continuity objects and provenance/correction rules who need a low-friction Hermes path.

## Problem
Current MCP-only use is explicit and reliable but requires manual invocation discipline. Users forget capture calls and lose continuity quality.

## Why It Matters
- Makes continuity automatic in normal chat flow.
- Preserves Alice’s existing semantic contracts instead of creating a Hermes-only memory model.
- Keeps power-user explicit actions available through MCP.

## Shipped Baseline Truth (Not New Scope)
- Phase 9 shipped: local-first continuity engine, deterministic CLI/MCP semantics, importers, approvals, eval harness.
- Phase 10 shipped: hosted/product layer (identity/workspaces/channels, Telegram, daily brief loop).
- Phase 11 shipped: provider adapters and model packs across local/self-hosted/enterprise paths.

## Bridge-Phase V1 Scope (Planned)
- Extend the shipped Alice Hermes external memory provider with standardized lifecycle automation hooks:
  - pre-turn prefetch
  - post-response candidate extraction + commit policy
  - session-end flush
- Keep Alice MCP server available for explicit actions (recall, review, explainability, corrections).
- Add/standardize automation-oriented tool surface:
  - `alice_prefetch_context`
  - `alice_capture_candidates`
  - `alice_commit_captures`
  - `alice_session_flush`
  - `alice_review_queue`
  - `alice_review_apply`
- Ship operating modes:
  - `manual`
  - `assist` (default)
  - `auto`
- Provide docs, config examples, smoke tests, and MCP-only fallback guidance.

## Non-Goals (Bridge Phase)
- Rebuilding shipped Phase 11 provider/model-pack scope.
- Replacing MCP with provider-only workflows.
- Expanding into unrelated channels/agent surfaces in this bridge phase.
- Auto-promoting single-turn inferences into higher-order trusted patterns/playbooks.

## Success Criteria
A Hermes user can enable Alice once and get:
- automatic pre-turn continuity context
- automatic post-turn candidate extraction
- automatic save of high-confidence explicit items
- low-confidence items routed to review queue
- explicit deep actions still accessible via MCP
- session-end consolidation

## Auto-Save Policy (Product Contract)
Auto-save eligible in `assist`:
- explicit correction
- explicit preference
- explicit decision
- explicit commitment
- explicit open-loop create/resolve

Review-required:
- inferred preferences
- weakly implied project state
- broad summaries
- speculative patterns
- low-confidence extractions

## Active Sprint Status
Bridge Sprint 2 (`B2`) is now the active execution sprint. It is limited to the auto-capture pipeline on top of the shipped Hermes provider surface and the `B1` contract foundation.

## Known Gaps To Resolve Before Build
- Candidate scoring rubric and confidence calibration method are not specified.
- Final storage contract for review queue/candidates is not explicitly defined in source.
- Provider authentication/authorization boundary for local vs hosted deployments is not explicitly defined.
