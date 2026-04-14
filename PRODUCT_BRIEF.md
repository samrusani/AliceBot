# Product Brief

## Product Summary
Alice is a pre-1.0 continuity platform for AI agents and agent-assisted workflows. It provides typed memory, provenance, correction-aware recall, open-loop tracking, resumable context, provider/runtime portability, and Hermes bridge integration.

## Baseline Truth (Shipped)
- Phase 9 shipped the continuity core, CLI, MCP, importers, approvals, and evaluation foundation.
- Phase 10 shipped the hosted/product layer, identity/workspace model, and channel surfaces.
- Phase 11 shipped provider runtime abstraction, provider adapters, and model packs.
- Bridge `B1` through `B4` shipped Hermes lifecycle hooks, auto-capture, review flow, explainability, packaging docs, smoke validation, and demo path.

## Current Repo Posture
- `v0.2.0` is tagged and released.
- Release Sprint 1 (`R1`) is complete and now baseline truth.
- Phase 12 is active.
- `P12-S1` Hybrid Retrieval + Reranking is shipped.
- `P12-S2` Automated Memory Operations is shipped.
- `P12-S3` Contradiction Detection + Trust Calibration is shipped.
- `P12-S4` Public Eval Harness is shipped.
- `P12-S5` Task-Adaptive Briefing is the active sprint.

## Next Phase
### Phase 12: Retrieval Quality + Adaptive Continuity
Raise Alice from a strong continuity substrate to a measurably better memory system by improving:
- retrieval precision
- memory freshness handling
- contradiction handling
- public quality evidence
- task-specific briefing for agents and workers

## Who It Is For
- Teams operating MCP-capable or provider-integrated agents that need durable continuity across sessions and runtimes.
- Developers who want one continuity layer across local, self-hosted, enterprise, and external-agent paths.
- Operators using Hermes who want always-on continuity without giving up reviewability or trust controls.

## Why This Phase Now
Alice already has durable memory, provenance, trust classes, revision/supersession behavior, resumption, open loops, and provider/MCP interoperability. The next phase is a quality step in the core loop:

`capture -> retrieve -> resume -> correct -> prove`

## In Scope For Phase 12
- Hybrid retrieval and reranking.
- Explicit memory mutation operations.
- First-class contradiction detection and trust calibration.
- Public multi-suite eval harness and baseline reports.
- Task-adaptive briefing for user recall, resume, worker subtask, and agent handoff.

## Non-Goals
- Full graph database migration.
- Marketplace work.
- Enterprise/compliance expansion.
- Latent KV-compaction research.
- New channels such as WhatsApp.
- New vertical products.

## Success Criteria
- Retrieval precision improves on baseline fixtures.
- Stale or superseded facts are less likely to outrank current truth.
- Contradictions become explicit, reviewable, and visible in explain flows.
- Public evals can demonstrate recall, resumption, correction, contradiction, and open-loop quality.
- Worker-task briefs are smaller and sharper than generic recall context without degrading resumption quality.

## Control Tower Decisions Needed
- Whether new Phase 12 APIs should live under new `/v1` feature namespaces or extend the existing continuity surface.
- Whether `DELETE` in memory operations means hard delete, logical tombstone, or a restricted administrative path.
