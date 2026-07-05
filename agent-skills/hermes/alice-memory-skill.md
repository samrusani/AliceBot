# Hermes Alice Memory Skill

Use Alice as the user's durable local memory and continuity layer.

Default loop — one first call, then act, then write back:

1. Call `alice_context_pack` ONCE with a scoped query before planning, answering, or acting on important user context. The pack already carries memories, open loops, sources, contradictions, and honest gaps — do not stitch together raw searches first.
2. Act, treating `staleness` notes and `contradicting_evidence` as caution signals.
3. When the user explicitly says to remember, save, or add a durable fact, call `alice_memory_commit`. For inferred, external, generated, ambiguous, or low-confidence facts, call `alice_capture` (review-gated) instead of forcing a write.
4. Finish lifecycle work with `alice_memory_manage` (`confirm`/`undo`/`forget`) and track unresolved work with `alice_open_loops`.

Context depth (request field `context_depth`; deterministic retrieval, never model synthesis): `minimal` for single-fact checks (full-text only, max 4 memories, no sources/contradictions), `low` (default) for normal task context, `medium` for briefings and reviews (contradiction check on for every query type), `high` for audits and revision history (adds supersession chain notes). Explicit `include_sources`/`include_contradictions` override the tier default. The matching MCP tool arguments arrive in the same release — follow the server's `tools/list` schema.

Rules:

- never directly mutate trusted memory or the database
- never bypass Alice policy
- never request sensitive domains unless needed and allowed
- use `/vnext` review queues for human approval, audit, undo, correction, and forget flows

Default identity:

```json
{"agent_id":"hermes","agent_type":"personal_assistant","permission_profile":"trusted_local_agent","project_scope":[]}
```

Default scope is broad but policy-filtered. Avoid `health`, `family`, `spiritual`, `legal`, `financial`, and `regulated` unless the user explicitly enables that scope.

Good memory proposal:

```json
{"canonical_text":"The user prefers daily planning summaries with decisions, blockers, and next actions.","domain":"personal","sensitivity":"private","confidence":0.84}
```

Good explicit commit:

```json
{"agent_id":"hermes","permission_profile":"trusted_local_agent","intent":"explicit_remember","title":"Preferred daily planning format","canonical_text":"The user prefers daily planning summaries with decisions, blockers, and next actions.","domain":"personal","sensitivity":"private","confidence":0.93,"source_type":"direct_user_instruction"}
```

If Alice returns `confirmation_required`, show the proposed text and call `alice_vnext_confirm_memory` only after the user confirms. If Alice returns `review_required`, do not retry broadly; leave it for `/vnext` review. The `alice_vnext_*` MCP tools are on the legacy surface and require `ALICE_MCP_LEGACY_TOOLS=1` on the Alice MCP server.

Bad memory proposal:

```json
{"canonical_text":"The user might dislike long reports.","confidence":0.31}
```

See `docs/alpha/hermes-skill.md` for full recipes.
