# Rules

## State Discipline
- Treat Phases 9-11 and Bridge `B1` through `B4` as shipped baseline truth.
- Treat `v0.2.0` as released baseline truth.
- Keep shipped baseline, active phase scope, and later roadmap scope separate.
- Keep [CURRENT_STATE.md](CURRENT_STATE.md) factual/current and [ROADMAP.md](ROADMAP.md) future-facing.
- Keep [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md) as the canonical handoff copy when duplicate current-state files exist.

## Retrieval Rules
- Retrieval must remain explainable: every result should be traceable to source objects, trust posture, timestamps, and lifecycle status.
- New ranking stages may improve selection quality, but they must not bypass supersession, provenance, or trust controls already in Alice.
- Retrieval changes should be benchmarked against fixture baselines before becoming default behavior.

## Mutation Rules
- Treat memory mutation as an explicit operation, not a silent overwrite.
- Corrections and changed facts should prefer `SUPERSEDE` or `UPDATE` semantics over destructive replacement.
- Low-confidence or inferred mutations default to review.
- Repeated syncs and retries must be idempotent.

## Contradiction And Trust Rules
- Contradictions must become reviewable objects, not hidden ranking artifacts.
- Unresolved contradictions should reduce promotion and retrieval confidence.
- Human correction and repeated corroboration may raise trust; weak single-source inference must not silently gain durable authority.

## Briefing Rules
- Keep durable memory separate from compiled briefs.
- Different workloads may receive different context packs, but all briefing outputs must remain deterministic and explainable.
- Briefing must not introduce claims that the underlying memory layer cannot justify.

## API And Architecture Rules
- For Hermes, use provider hooks for automation and MCP for explicit deep actions.
- Never fork continuity semantics by surface or runtime.
- Reuse the current continuity contracts where possible; add new surfaces only when the existing contract cannot express the phase goal cleanly.
- Do not fork semantics between CLI, MCP, hosted, provider-runtime, and Hermes paths.
- Keep MCP fallback viable even when provider or bridge integrations are the recommended mode.

## Security And Operations Rules
- Preserve user/workspace isolation across retrieval, mutation, eval, and briefing flows.
- Keep credentials, tokens, and secret references out of logs and error payloads.
- Keep local filesystem paths, workstation usernames, and machine-specific identifiers out of committed docs and reports.
- Keep consequential side effects approval-bounded.
- Commit public evidence only from exact commands and stable fixtures, never from inferred pass states.
- When a checked-in fixture catalog is declared canonical, runtime sync must prune removed definitions or read directly from the catalog as the source of truth.

## Scope Rules
- Do not widen Phase 12 into graph migration, marketplace, enterprise/compliance, or new channel work.
- Do not silently hardcode unresolved sprint Control Tower decisions as permanent runtime behavior without recording the decision.
- Surface underspecified decisions as Control Tower decisions instead of inventing scope.
