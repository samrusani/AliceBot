# Hermes Alice Memory Skill

Use this instruction block in Hermes when Alice is available.

Note: the explicit `alice_vnext_*` MCP tools referenced below (commit, confirm, ingest) are keyless-local legacy compatibility only and require `ALICE_MCP_LEGACY_TOOLS=1`. A server bound with `ALICE_AGENT_API_KEY` hides and rejects them. Authenticated integrations use the default three tools in [mcp-tools.md](mcp-tools.md): `alice_memory_commit`, `alice_recall`, `alice_resume`. Capture and the pack are on the full surface (`ALICE_MCP_FULL_TOOLS=1`).

```text
You are connected to Alice, the user's local-first memory and continuity layer.

Default loop: remember, recall, continue.
1. Call alice_memory_commit whenever you learn a durable fact worth keeping, including when the user has not asked you to remember it. It is the write verb for ordinary memory and what it records is immediately recallable.
2. Call alice_recall to search memory and imported sources.
3. Call alice_resume to pick work back up: last decision, next action, open loops, recent changes.

alice_capture and alice_context_pack are full-surface tools. Use them only when the server lists them. Capture stores a source; its passages come back from alice_recall under sources, as material to read and quote rather than as facts Alice asserts. Candidates stay unsearchable as memories. Import is a source. Commit is a fact. Do not tell the user they must clear a review queue before a note is usable.

Never directly mutate trusted memory.
Never write directly to Postgres.
Never bypass Alice policy.
Never request sensitive domains unless needed and allowed.
```

`context_depth` (and `budget_strategy` for token budgets) are fields on
Alice's context-pack request. The matching `alice_context_pack` MCP tool
is full-surface. Trust the server's `tools/list` schema and omit the
argument if the server does not list the tool.

Default identity:

```json
{
  "agent_id": "hermes",
  "agent_type": "personal_assistant",
  "permission_profile": "trusted_local_agent",
  "project_scope": []
}
```

Default permissions:

- scope: broad but policy-filtered
- allowed domains: `professional`, `project`, `personal` where configured
- restricted by default: `health`, `family`, `spiritual`, `legal`, `financial`, `regulated`

Recipes:

- Daily planning: `alice_resume`, then `alice_recall` if you need a specific fact.
- Meeting preparation: `alice_recall` with the meeting name and attendees.
- Quick fact check ("do we know X?"): `alice_recall`.
- Follow-up context: `alice_resume` with a query for open loops and recent decisions.
- Project briefing: `alice_resume` scoped to the project, then `alice_recall` for the gap.
- Personal assistant memory commit: commit only explicit stable preferences or durable decisions through Alice.
- Quote memory commit: use `memory_type=semantic`; if a domain is needed for quote collections, use `domain=learning`.
- Full-surface pack (only if listed): one `alice_context_pack` call before a long review.

Use only schema-backed enum values for persisted fields. Do not send invented labels such as `memory_type=quote`, `domain=quotes`, or `sensitivity=sensitive`; Alice normalizes common aliases, but canonical values keep MCP calls predictable.

Good explicit commit:

```json
{
  "agent_id": "hermes",
  "agent_type": "personal_assistant",
  "permission_profile": "trusted_local_agent",
  "title": "Preferred daily planning format",
  "canonical_text": "The user prefers daily planning summaries with decisions, blockers, and next actions.",
  "domain": "personal",
  "sensitivity": "private",
  "confidence": 0.93,
  "source_type": "direct_user_instruction"
}
```

Expected outcomes:

- `committed`: Alice stored the memory as active and auditable.
- `confirmation_required`: show the proposed text and, only after the user confirms, call
  `alice_memory_manage` with `action: "confirm"` and the returned `confirmation_id` (full-surface).
- `review_required`: leave the candidate. Do not tell the user to clear a review queue.
- `rejected`: do not retry without narrowing scope or asking the user.

`title` and `canonical_text` are the only required fields. Every other property must appear in
the server's `tools/list` schema for the tool you are calling; an unrecognised property is
rejected outright rather than ignored. In particular `intent` exists only on the legacy
`alice_vnext_commit_memory` tool and is **not** accepted by `alice_memory_commit`.

Good proposal:

```json
{
  "title": "Preferred daily planning format",
  "canonical_text": "The user prefers daily planning summaries with decisions, blockers, and next actions.",
  "domain": "personal",
  "sensitivity": "private",
  "confidence": 0.84,
  "rationale": "The user stated this preference explicitly."
}
```

Bad proposal:

```json
{
  "title": "Possible reporting preference",
  "canonical_text": "The user might dislike long reports.",
  "confidence": 0.31,
  "rationale": "Speculative inference from one short reply."
}
```
