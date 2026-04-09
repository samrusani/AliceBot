---
name: alice-continuity-recall
description: Use Alice MCP recall tools for continuity-grounded answers with provenance when users ask what was decided, what changed, or what to remember.
version: 1.0.0
author: Alice
license: MIT
metadata:
  hermes:
    tags: [alice, continuity, recall, mcp]
    related_skills: [alice-resumption, alice-explain-provenance]
---

# Alice Continuity Recall

## Goal

Produce recall answers from Alice continuity records instead of free-form memory.

## Trigger Cues

Use this skill when the user asks:
- what was decided
- what happened in a thread/project/person scope
- what should be remembered from prior work

## Required MCP Tools

- `mcp_<alice_server>_alice_recall`
- Optional: `mcp_<alice_server>_alice_recent_decisions`

`<alice_server>` is usually `alice_core`.

## Workflow

1. Prefer `alice_recall` over inference-only answers.
2. Use scope filters when available (`thread_id`, `project`, `person`, `since`, `until`).
3. Keep `limit` bounded (normally `3` to `10`).
4. Return summary plus provenance-backed evidence IDs.

## Tool Call Templates

```text
mcp_alice_core_alice_recall({"query":"<topic>","thread_id":"<uuid>","limit":5})
```

```text
mcp_alice_core_alice_recent_decisions({"thread_id":"<uuid>","limit":5})
```

## Output Contract

Always include:
- direct answer
- top evidence items (`id`, `title`, `object_type`)
- provenance notes from the returned item fields
- uncertainty note if evidence is weak or absent
