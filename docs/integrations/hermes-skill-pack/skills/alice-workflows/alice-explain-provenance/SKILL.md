---
name: alice-explain-provenance
description: Explain why an answer is trustworthy by referencing Alice continuity provenance and correction state from MCP tool outputs.
version: 1.0.0
author: Alice
license: MIT
metadata:
  hermes:
    tags: [alice, continuity, provenance, explainability, mcp]
    related_skills: [alice-continuity-recall, alice-correction-loop]
---

# Alice Explain Provenance

## Goal

Provide evidence-backed explanations for Alice-based answers.

## Trigger Cues

Use this skill when the user asks:
- why are you saying this
- what source supports this
- can you show evidence or provenance

## Required MCP Tools

- `mcp_<alice_server>_alice_context_pack`
- Optional: `mcp_<alice_server>_alice_recall`

`<alice_server>` is usually `alice_core`.

## Workflow

1. Start from `alice_context_pack` for a scoped evidence set.
2. If needed, run a focused `alice_recall` query for missing evidence.
3. Explain answer claims by citing returned continuity object IDs and provenance fields.
4. If provenance is thin, state uncertainty and propose the next validating step.

## Tool Call Templates

```text
mcp_alice_core_alice_context_pack({"thread_id":"<uuid>","recent_decisions_limit":5,"recent_changes_limit":5,"open_loops_limit":5})
```

```text
mcp_alice_core_alice_recall({"thread_id":"<uuid>","query":"<claim>","limit":5})
```

## Output Contract

Always include:
- claim
- supporting object IDs
- provenance summary from returned records
- confidence posture (`high`, `medium`, `low`) based on evidence quality
