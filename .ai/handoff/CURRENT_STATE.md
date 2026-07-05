# Current State

Canonical handoff copy. A synced summary lives at the repo root [CURRENT_STATE.md](../../CURRENT_STATE.md).

## Snapshot
- `v0.8.0` is the latest release: the memory-frontier waves plus Alice's first published benchmark result.
- Alice is positioned as the continuity layer for AI agents; agent developers are the customer. Collaborative posture: a layer, not a lock-in — designed to run alongside other memory tools.

## What `v0.8.0` Contains
- **LongMemEval_s 64.6%** — official judge protocol, full per-question evidence and reproduction script in `docs/benchmarks/longmemeval/`; knowledge-update 74.4%; multi-session synthesis (45.1%) is the top roadmap item.
- **Budgeted, opinionated context packs** — enforced `max_tokens` with truncation reporting; contradictions and recent changes populated; staleness notes per memory.
- **Typed, staleness-aware retrieval** — `memory_types`/`projects`/`created_by_agents` filters end-to-end; expired facts excluded by default; `stale` status plus the daily `staleness_sweep` review workflow.
- **Agentic write protocol on the core MCP surface** — 11 tools including `alice_memory_commit` and `alice_memory_manage`; the Memory Operations Protocol is documented with audit guarantees and honest boundaries.
- **Real scopes** — `project_id`/`created_by_agent_id`/`run_id` columns, key-bound project scope (narrow-only), policy-blocked out-of-scope writes.
- **Merging consolidation** — embedding clustering to merge/dedup candidates through the review gate; grounding-gated model merges with structured refusals; never automatic supersession.
- **Temporal slice** — edge event time, first-class supersession pointers, as-of queries, supersession chains in `alice_explain`, graph substrate on the SQLite on-ramp.
- **Verification** — 1,460 unit and 377/377 integration tests green; four live eval suites on both backends; migrations 0075–0077 additive and reversible.

## Boundaries That Hold
- Review-governed writes: agent memory commits resolve to commit, confirm, review, or reject through policy; no direct database writes by agents.
- Local-first, single-user; no hosted service; no OAuth connectors; no automatic capture from arbitrary conversation.

## Not Current State
- No npm packages, no hosted offering, no SLA. `merge`/`expire` memory operations are planned, not shipped (consolidation produces merge candidates; acceptance flows are the review actions).
