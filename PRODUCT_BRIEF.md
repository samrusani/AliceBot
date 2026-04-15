# Product Brief

## Product Summary
Alice is a pre-1.0 continuity platform for AI agents and agent-assisted workflows. It provides typed memory, provenance, correction-aware recall, open-loop tracking, resumable context, provider/runtime portability, and Hermes bridge integration.

## Shipped Baseline
- Phase 9 shipped the continuity core, CLI, MCP, importers, approvals, and evaluation foundation.
- Phase 10 shipped the hosted/product layer, identity/workspace model, and channel surfaces.
- Phase 11 shipped provider runtime abstraction, provider adapters, and model packs.
- Bridge `B1` through `B4` shipped Hermes lifecycle hooks, auto-capture, review flow, explainability, packaging docs, smoke validation, and demo path.
- Phase 12 shipped hybrid retrieval and reranking, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- `v0.3.2` is the latest published pre-1.0 release tag.

## Current Repo Posture
- Phase 13 is active.
- `P13-S1` One-Call Continuity is shipped.
- `P13-S2` Alice Lite is the active execution sprint.
- `P13-S3` Memory Hygiene + Conversation Health follows after Alice Lite.
- Phase 13 is an adoption and ergonomics phase built on top of the shipped Phase 12 baseline.

## Active Phase
### Phase 13: Alice Lite + Integration Ergonomics
Turn Alice from a powerful continuity system into an easier-to-adopt, easier-to-feel, and easier-to-integrate product for solo users, builders, and agent teams.

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

## In Scope For Phase 13
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

## Control Tower Decisions Needed
- Whether the next public release boundary should wrap the whole Phase 13 sequence or ship incrementally.
- Whether Alice Lite in `P13-S2` should remain a deployment-profile change only or later justify an embedded mode.
- Exact default inclusion behavior for `/v1/continuity/brief` when query, thread, and entity context all coexist.
