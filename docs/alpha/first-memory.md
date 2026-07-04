# First Memory Guide

Use this guide when Alice is installed correctly but a tester says, "I do not see any memories."

Alice is not automatic chat-history memory. The current public preview has several memory paths, and they have different trust and review behavior.

Note: the default MCP surface is the nine core tools (see [mcp-tools.md](mcp-tools.md)); `alice_capture` is the core path for submitting reviewable memory. The `alice_vnext_*` MCP tools referenced below are on the legacy surface and require `ALICE_MCP_LEGACY_TOOLS=1` on the Alice MCP server.

## What To Expect

| Path | Best for | Result |
| --- | --- | --- |
| `alice_vnext_commit_memory` | explicit user-directed "remember/save this" instructions from a trusted agent | active memory, confirmation, review, or rejection through Alice policy |
| `alice_vnext_ingest_agent_output` with `propose_memory=true` | agent summaries, sprint outputs, meeting notes, or inferred durable facts | reviewable memory proposal in `/vnext` |
| `alicebot vnext sources capture-text ...` | raw evidence capture from text, files, browser clips, or connectors | source evidence plus deterministic candidate memories when extractable |
| Hermes provider `sync_turn` | post-turn bridge capture for structured turns | best-effort capture candidates, not general conversation memory |
| legacy explicit signal capture | simple preferences and commitments | deterministic memory/open-loop admission for supported phrases |

Normal conversation is not guaranteed to become memory. Agents should use the explicit commit/proposal tools when the user clearly asks Alice to remember something.

## Fastest First Trusted Memory

Run the shipped smoke test:

```bash
alicebot vnext smoke agentic-memory-commit
```

If `alicebot` is not on your shell path:

```bash
./.venv/bin/alicebot vnext smoke agentic-memory-commit
```

Expected result:

- direct trusted commit works for allowed explicit memory
- sensitive or ambiguous memory is routed to confirmation or review
- undo, correction, forget, and audit gates are exercised

## First Manual Source Capture

Capture a simple source that should produce reviewable candidate memory:

```bash
alicebot vnext sources capture-text "Fact: The user prefers concise daily planning summaries." --domain personal --sensitivity private
```

Then open `/vnext` and check:

- Inbox for the captured source
- Memory Review for candidate memory
- Trace for source-to-candidate provenance

This path creates reviewable evidence first. It does not silently promote trusted memory.

## First Agent Memory Commit

For MCP-connected agents, use `alice_vnext_commit_memory` when the user explicitly says to remember, save, or add something to memory.

Example payload:

```json
{
  "agent_id": "hermes",
  "agent_type": "personal_assistant",
  "permission_profile": "trusted_local_agent",
  "intent": "explicit_remember",
  "title": "Preferred planning format",
  "canonical_text": "The user prefers concise daily planning summaries with decisions, blockers, and next actions.",
  "domain": "personal",
  "sensitivity": "private",
  "confidence": 0.93,
  "source_type": "direct_user_instruction"
}
```

Alice returns one of:

- `committed`
- `confirmation_required`
- `review_required`
- `rejected`

Do not write directly to Postgres or bypass Alice policy.

## Structured Phrases That Capture Better

The deterministic paths are intentionally narrow. These phrases are good first-run tests:

```text
I prefer concise summaries
I like short daily planning briefs
remember to follow up with the investor tomorrow
remind me to review the launch checklist
Fact: The user prefers concise daily planning summaries.
Decision: Use Alice as the continuity layer for this agent.
Preference: Keep daily briefs short.
Todo: Confirm the launch checklist owner.
Next action: Send the partner follow-up.
```

Unstructured chat, slang, and non-English natural-language memory requests may not match the deterministic capture rules. Use explicit MCP commit/proposal tools for those cases.

## Hermes Provider Notes

The Hermes memory provider adds recall, prefetch, resumption briefs, open-loop lookup, and optional post-turn capture. It does not make every Hermes conversation an automatic trusted memory.

Check the provider config:

```json
{
  "bridge_mode": "assist",
  "sync_turn_capture_enabled": true
}
```

Important behavior:

- `sync_turn_capture_enabled: false` disables post-turn capture.
- `bridge_mode: manual` disables bridge capture behavior.
- post-turn capture is structured and policy-bound.
- trusted memory still requires explicit commit policy, confirmation, or review.

For Hermes, the recommended setup is provider plus MCP: use the provider for always-on continuity context, and MCP for explicit `alice_vnext_commit_memory` calls.

## Troubleshooting Checklist

If no memory appears:

1. Run `alicebot vnext smoke agentic-memory-commit`.
2. Confirm the agent has MCP access to `alice_vnext_commit_memory`.
3. Confirm the agent is using a permission profile that can commit or propose memory.
4. Check `/vnext` Memory Review before assuming nothing was captured.
5. Check Trace for captured source evidence and candidate links.
6. For Hermes, verify `sync_turn_capture_enabled` and avoid `bridge_mode: manual` if post-turn capture is expected.
7. Test with one of the structured English phrases above.

If that works, Alice memory is functioning. The missing piece is agent prompting/integration, not the memory store.
