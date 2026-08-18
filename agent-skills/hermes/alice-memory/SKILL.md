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

Default loop: remember, recall, continue.

1. Call `alice_memory_commit` whenever you learn a durable fact worth keeping, including when the user has not asked you to remember it. It is the write verb for ordinary memory and what it records is immediately recallable.
2. Call `alice_recall` to search memory and imported sources.
3. Call `alice_resume` to pick work back up: last decision, next action, open loops, recent changes.

`alice_capture` and `alice_context_pack` are full-surface tools. Use them only when the server lists them. Capture stores a source; its passages come back from `alice_recall` under `sources`, as material to read and quote rather than as facts Alice asserts. Candidates stay unsearchable until a reviewer promotes them. Import is a source. Commit is a fact. Do not tell the user they must clear a review queue before a note is usable.

Your host may prefix these tool names with the server name. Read the names from the host's own tool list rather than assuming the bare form.

Rules:

- never directly mutate trusted memory or the database
- never bypass Alice policy
- never request sensitive domains unless needed and allowed

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

If Alice returns `confirmation_required`, show the proposed text and, only after the user confirms, call `alice_memory_manage` with `action: "confirm"` and the `confirmation_id` Alice returned (full-surface). If Alice returns `review_required`, do not tell the user to clear a review queue.

Bad commit, too low confidence to be worth storing:

```json
{"title":"Possible reporting preference","canonical_text":"The user might dislike long reports.","confidence":0.31}
```

See `docs/alpha/hermes-skill.md` for full recipes.
