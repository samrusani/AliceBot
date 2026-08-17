---
name: alice-memory
description: Use Alice as the user's durable local memory. Load before answering from context, and whenever you learn something worth keeping across sessions.
version: 1.0.0
author: Alice Memory
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Memory, Continuity, MCP, Recall]
    related_skills: []
---

# Hermes Alice Memory Skill

Use Alice as the user's durable local memory and continuity layer.

Default loop — one first call, then act, then write back:

1. Call `alice_context_pack` ONCE with a scoped query before planning, answering, or acting on important user context. The pack already carries memories, open loops, sources, contradictions, and honest gaps — do not stitch together raw searches first.
2. Act, treating `staleness` notes and `contradicting_evidence` as caution signals.
3. Call `alice_memory_commit` whenever you learn a durable fact worth keeping, including when the user has not asked you to remember it. It is the write verb for ordinary memory and what it records is immediately recallable. Use `alice_capture` for source documents and raw notes you want on record: its passages come back from `alice_recall` under `sources`, as material to read and quote rather than as facts Alice asserts. It also proposes candidate memories, and those stay unsearchable until a reviewer promotes them, so do not tell the user their import is unusable until they clear a queue.
4. Finish lifecycle work with `alice_memory_manage` (`confirm`/`undo`/`forget`). Record unresolved work with `alice_memory_commit` using `memory_type: "open_loop"`; `alice_open_loops` reads and closes loops, it does not create them.

Your host may prefix these tool names with the server name. Read the names from the host's own tool list rather than assuming the bare form.

Context depth (request field `context_depth`; deterministic retrieval, never model synthesis): `minimal` for single-fact checks (full-text only, max 4 memories, no sources/contradictions), `low` (default) for normal task context, `medium` for briefings and reviews (contradiction check on for every query type), `high` for audits and revision history (adds supersession chain notes). Explicit `include_sources`/`include_contradictions` override the tier default. The matching MCP tool arguments arrive in the same release — follow the server's `tools/list` schema.

Rules:

- never directly mutate trusted memory or the database
- never bypass Alice policy
- never request sensitive domains unless needed and allowed
- use `alice_memory_review` and `alice_memory_correct` for human approval, audit, correction and forget flows

Default identity:

```json
{"agent_id":"hermes","agent_type":"personal_assistant","permission_profile":"trusted_local_agent","project_scope":[]}
```

Default scope is broad but policy-filtered. Avoid `health`, `family`, `spiritual`, `legal`, `financial`, and `regulated` unless the user explicitly enables that scope.

Good ambient commit, nobody asked for this one:

```json
{"title":"Preferred daily planning format","canonical_text":"The user prefers daily planning summaries with decisions, blockers, and next actions.","domain":"personal","sensitivity":"private","confidence":0.84}
```

Good explicit commit, the user said to remember it:

```json
{"agent_id":"hermes","agent_type":"personal_assistant","permission_profile":"trusted_local_agent","title":"Preferred daily planning format","canonical_text":"The user prefers daily planning summaries with decisions, blockers, and next actions.","domain":"personal","sensitivity":"private","confidence":0.93,"source_type":"direct_user_instruction"}
```

`title` and `canonical_text` are the only required fields. Everything else is optional, and any field not in the server's `tools/list` schema is rejected outright rather than ignored.

If Alice returns `confirmation_required`, show the proposed text and, only after the user confirms, call `alice_memory_manage` with `action: "confirm"` and the `confirmation_id` Alice returned. If Alice returns `review_required`, do not retry broadly; leave it for `alice_memory_review`.

Bad commit, too low confidence to be worth storing:

```json
{"title":"Possible reporting preference","canonical_text":"The user might dislike long reports.","confidence":0.31}
```

See `docs/alpha/hermes-skill.md` for full recipes.
