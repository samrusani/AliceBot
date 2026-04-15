# Current State

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- Phase 12 is shipped.
- `v0.3.2` is the latest published tag.
- Phase 13 is active.
- `P13-S1` One-Call Continuity is shipped.
- `P13-S2` Alice Lite is shipped.
- `P13-S3` Memory Hygiene + Conversation Health is the active execution sprint.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The shipped baseline now includes hybrid retrieval and reranking with traces, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- The shipped baseline also now includes the one-call continuity surface across API, CLI, and MCP from `P13-S1`.
- The shipped baseline also now includes the lighter Alice Lite startup/profile path from `P13-S2`.
- `v0.3.2` is the current public pre-1.0 release boundary for that shipped baseline.

## Phase Transition Note
- Phase 12 is complete and remains baseline truth.
- Phase 13 is the adoption and ergonomics phase on top of that baseline.
- `P13-S1` is complete and established the primary one-call continuity surface across API, CLI, and MCP.
- `P13-S2` is complete and established the lighter Alice Lite startup/profile path without semantic drift.
- `P13-S3` is active and should make hygiene and thread/conversation health visible and operationally useful.

## Immediate Control Tower Decisions Needed
- Decide whether the next public release should wrap the full Phase 13 sequence or ship incrementally.
- Decide the threshold model for risky/stale thread health in `P13-S3`.
- Decide whether the first shipped thread-health surface is API-only, UI-visible, or both.
