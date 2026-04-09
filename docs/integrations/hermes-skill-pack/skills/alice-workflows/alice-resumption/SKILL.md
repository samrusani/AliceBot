---
name: alice-resumption
description: Build deterministic continuation briefs with Alice MCP resumption tools when users want to pick up interrupted work.
version: 1.0.0
author: Alice
license: MIT
metadata:
  hermes:
    tags: [alice, continuity, resume, mcp]
    related_skills: [alice-continuity-recall, alice-open-loop-review]
---

# Alice Resumption

## Goal

Resume work from deterministic continuity state instead of reconstructing history manually.

## Trigger Cues

Use this skill when the user asks:
- continue where we left off
- give me a restart brief
- summarize decisions, next action, blockers

## Required MCP Tools

- `mcp_<alice_server>_alice_resume`
- Optional: `mcp_<alice_server>_alice_context_pack`

`<alice_server>` is usually `alice_core`.

## Workflow

1. Call `alice_resume` with scoped filters and bounded limits.
2. If broader context is needed, call `alice_context_pack`.
3. Prioritize these sections in your answer:
   - last decision
   - next action
   - open loops
   - recent changes
4. Keep the final brief actionable and short.

## Tool Call Templates

```text
mcp_alice_core_alice_resume({"thread_id":"<uuid>","max_recent_changes":5,"max_open_loops":5})
```

```text
mcp_alice_core_alice_context_pack({"thread_id":"<uuid>","recent_changes_limit":5,"open_loops_limit":5,"recent_decisions_limit":5})
```

## Output Contract

Always include:
- `last_decision`
- `next_action`
- `blockers_or_waiting_for`
- `recent_changes`
- explicit note when `thread_id` or scope is missing
