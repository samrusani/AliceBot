---
name: alice-correction-loop
description: Run deterministic correction workflows with Alice MCP review and correction tools, then verify that future outputs reflect the update.
version: 1.0.0
author: Alice
license: MIT
metadata:
  hermes:
    tags: [alice, continuity, correction, review, mcp]
    related_skills: [alice-explain-provenance, alice-open-loop-review]
---

# Alice Correction Loop

## Goal

Apply corrections through Alice review tools and confirm that recall/resumption behavior updates accordingly.

## Trigger Cues

Use this skill when the user asks:
- this is outdated or wrong
- correct this memory
- supersede or mark stale

## Required MCP Tools

- `mcp_<alice_server>_alice_memory_review`
- `mcp_<alice_server>_alice_memory_correct`
- Verification: `mcp_<alice_server>_alice_recall` or `mcp_<alice_server>_alice_resume`

`<alice_server>` is usually `alice_core`.

## Workflow

1. Fetch review queue or detail with `alice_memory_review`.
2. Select correction action:
   - `confirm`
   - `edit`
   - `delete`
   - `supersede`
   - `mark_stale`
3. Apply correction with `alice_memory_correct`.
4. Re-run `alice_recall` or `alice_resume` to verify behavior changed.
5. Report both the correction action and the observed post-correction result.

## Tool Call Templates

```text
mcp_alice_core_alice_memory_review({"status":"correction_ready","limit":10})
```

```text
mcp_alice_core_alice_memory_correct({"continuity_object_id":"<uuid>","action":"supersede","replacement_title":"<title>","replacement_body":{}})
```

## Output Contract

Always include:
- corrected object ID
- action applied
- reason
- post-correction verification result
