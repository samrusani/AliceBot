# Product Brief

## Product Summary
Alice is a pre-1.0 continuity platform for AI agents and agent-assisted workflows. It provides typed memory, provenance, correction-aware recall, open-loop tracking, resumable context, provider/runtime portability, and Hermes bridge integration.

## Shipped Baseline
- Phase 9 shipped the continuity core, CLI, MCP, importers, approvals, and evaluation foundation.
- Phase 10 shipped the hosted/product layer, identity/workspace model, and channel surfaces.
- Phase 11 shipped provider runtime abstraction, provider adapters, and model packs.
- Bridge `B1` through `B4` shipped Hermes lifecycle hooks, auto-capture, review flow, explainability, packaging docs, smoke validation, and demo path.
- Phase 12 shipped hybrid retrieval and reranking, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- Phase 13 shipped one-call continuity, Alice Lite, and memory hygiene / conversation health visibility.
- `v0.4.0` is the latest published pre-1.0 release tag.

## Current Repo Posture
- Phase 13 is shipped.
- `P13-S1` One-Call Continuity is shipped.
- `P13-S2` Alice Lite is shipped.
- `P13-S3` Memory Hygiene + Conversation Health is shipped.
- No post-Phase-13 execution sprint is active yet.

## Latest Completed Phase
### Phase 13: Alice Lite + Integration Ergonomics
Phase 13 turned Alice from a powerful continuity system into an easier-to-adopt, easier-to-feel, and easier-to-integrate product for solo users, builders, and agent teams.

## Why This Phase Now
Phase 12 improved Alice's internal quality:
- hybrid retrieval
- explicit memory mutation
- contradiction and trust handling
- public evals
- task-adaptive briefing

Phase 13 should make those gains easier to adopt:
- simpler local install
- a single continuity call for external runtimes
- visible memory hygiene
- visible conversation health
- tighter docs and examples for real integrations

## Primary Users
- Solo technical users who want fast setup, local-first usage, and useful continuity without heavy ops.
- Agent builders who want one integration surface and less orchestration complexity.
- Teams evaluating Alice who want obvious quality, visible hygiene, and quick demo value.

## Phase 13 Scope That Shipped
- One-call continuity API / CLI / MCP surface.
- Alice Lite deployment profile and simplified local startup.
- Memory hygiene visibility for duplicates, stale facts, unresolved contradictions, weak trust, and review backlog.
- Conversation health visibility for recent threads, stale threads, risky threads, and thread activity.
- Integration docs and demos for existing runtimes.

## Non-Goals
- New channels.
- New major connectors.
- New vertical products.
- Graph-database migration.
- Marketplace work.
- Large enterprise/admin features.
- New provider/runtime substrate work unless directly required to support the Phase 13 deliverables.
- Deep new memory research.

## Success Criteria
- A solo user can install Alice through a lightweight local path and get a useful continuity brief quickly.
- An agent builder can call one main continuity surface instead of stitching together many tool calls.
- Memory hygiene and conversation health become visible enough that stale/conflicting/risky states are obvious without deep system knowledge.
- Alice feels simpler and more polished without weakening its continuity semantics.

## Immediate Product Posture
- `v0.4.0` is the current public release boundary for the completed Phase 13 surface.
- The next product decision is Phase 14 definition on top of the shipped Phase 13 baseline.
