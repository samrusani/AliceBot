# Current State

This file is a synced repo-root copy for planning visibility.
Canonical handoff state lives at [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md).

## Status Snapshot
- Phase 9 is shipped.
- Phase 10 is shipped.
- Phase 11 is shipped.
- Bridge `B1` through `B4` are shipped.
- Phase 12 is shipped.
- `v0.3.2` is the latest published tag.
- Phase 13 is active.
- `P13-S1` One-Call Continuity is the active execution sprint.
- `P13-S2` Alice Lite is planned next.
- `P13-S3` Memory Hygiene + Conversation Health is planned after Alice Lite.

## Current Baseline Truth
- Alice has typed memory, provenance, trust classes, correction/supersession behavior, open loops, recall, resumption, and explainability.
- Alice exposes CLI, MCP, hosted/product, provider-runtime, and Hermes bridge surfaces.
- The shipped baseline now includes hybrid retrieval and reranking with traces, explicit memory mutation operations, contradiction/trust handling, the public eval harness, and task-adaptive briefing.
- `v0.3.2` is the current public pre-1.0 release boundary for that shipped baseline.

## Phase Transition Note
- Phase 12 is complete and remains baseline truth.
- Phase 13 is the adoption and ergonomics phase on top of that baseline.
- `P13-S1` is active and should create the primary one-call continuity surface across API, CLI, and MCP.
- `P13-S2` should simplify startup and local adoption without semantic drift.
- `P13-S3` should make hygiene and thread/conversation health visible and operationally useful.

## Immediate Control Tower Decisions Needed
- Decide whether the next public release should wrap the full Phase 13 sequence or ship incrementally.
- Decide whether Alice Lite remains purely a lighter deployment profile in `P13-S2`.
- Decide the threshold model for risky/stale thread health in `P13-S3`.
