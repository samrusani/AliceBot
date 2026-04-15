# Current State

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- Phase 12 is shipped.
- Phase 13 is shipped.
- `v0.4.0` is the latest published tag.
- `P13-S1` One-Call Continuity is shipped.
- `P13-S2` Alice Lite is shipped.
- `P13-S3` Memory Hygiene + Conversation Health is shipped.
- No post-Phase-13 build sprint is active yet.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The shipped baseline now includes hybrid retrieval and reranking with traces, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- The shipped baseline also now includes the one-call continuity surface across API, CLI, and MCP from `P13-S1`.
- The shipped baseline also now includes the lighter Alice Lite startup/profile path from `P13-S2`.
- The shipped baseline also now includes memory hygiene and thread/conversation health visibility from `P13-S3`.
- `v0.4.0` is the current public pre-1.0 release boundary for that shipped baseline.

## Phase Transition Note
- Phase 12 is complete and remains baseline truth.
- Phase 13 is complete and remains baseline truth.
- `P13-S1` is complete and established the primary one-call continuity surface across API, CLI, and MCP.
- `P13-S2` is complete and established the lighter Alice Lite startup/profile path without semantic drift.
- `P13-S3` is complete and made hygiene and thread/conversation health visible and operationally useful.

## Immediate Control Tower Decisions Needed
- Define the next phase and its first sprint packet on top of the shipped `v0.4.0` baseline.
- Avoid reopening completed Phase 13 work unless a defect or follow-up is explicitly scoped.
