# Rules

## State Discipline
- Treat Phases 9-12 and Bridge `B1` through `B4` as shipped baseline truth.
- Treat `v0.3.2` as released baseline truth.
- Keep shipped baseline, active phase scope, and later roadmap scope separate.
- Keep [CURRENT_STATE.md](CURRENT_STATE.md) factual/current and [ROADMAP.md](ROADMAP.md) future-facing.
- Keep [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md) as the canonical handoff copy when duplicate current-state files exist.

## Phase 13 Rules
- Phase 13 is an adoption layer on top of the shipped `v0.3.2` baseline.
- Prioritize one-call continuity first, then Alice Lite, then hygiene and conversation health.
- Only admit new substrate work when it is required to support those deliverables.
- If a proposed Phase 13 change does not reduce integration complexity, improve first-run experience, or make memory quality more visible, it probably does not belong in Phase 13.

## Continuity Surface Rules
- One-call continuity must compose existing retrieval, contradiction, trust, recent-change, open-loop, and briefing layers rather than fork them.
- One-call continuity output must remain explainable, provenance-backed, and trust-aware.
- Do not fork continuity semantics between API, CLI, MCP, hosted, provider-runtime, and Hermes paths.

## Alice Lite Rules
- Alice Lite is a deployment profile, not a separate product.
- Alice Lite must preserve the same continuity semantics as the full baseline.
- Do not move to SQLite or another embedded mode unless no semantics degrade, no retrieval features materially regress, and no explain/provenance breakage is introduced.

## Hygiene And Thread Health Rules
- Hygiene surfaces should make duplicates, stale facts, contradictions, weak trust, and review pressure visible without inventing a second memory system.
- Thread health should be diagnostic and operational, not a separate durable truth ontology.
- Visibility comes before cleverness. Make risky or stale states obvious before adding more scoring complexity.

## API And Integration Rules
- For Hermes, use provider hooks for automation and MCP for explicit deep actions.
- Keep MCP fallback viable even when provider or bridge integrations are the recommended mode.
- Reuse the current continuity contracts where possible; add new surfaces only when the existing contract cannot express the phase goal cleanly.

## Security And Operations Rules
- Preserve user/workspace isolation across retrieval, mutation, eval, briefing, hygiene, and thread-health flows.
- Keep credentials, tokens, and secret references out of logs and error payloads.
- Keep local filesystem paths, workstation usernames, and machine-specific identifiers out of committed docs and reports.
- Keep consequential side effects approval-bounded.
- Commit public evidence only from exact commands and stable fixtures, never from inferred pass states.

## Scope Rules
- Do not widen Phase 13 into retrieval research, graph migration, new channels, new provider/runtime work, marketplace work, or enterprise/admin expansion.
- Do not silently hardcode unresolved Control Tower decisions as permanent runtime behavior without recording the decision.
- Surface underspecified decisions as Control Tower decisions instead of inventing scope.
