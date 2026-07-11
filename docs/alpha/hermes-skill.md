# Hermes Alice Memory Skill

Use this instruction block in Hermes when Alice is available.

Note: the explicit `alice_vnext_*` MCP tools referenced below (commit, confirm, ingest) are keyless-local legacy compatibility only and require `ALICE_MCP_LEGACY_TOOLS=1`. A server bound with `ALICE_AGENT_API_KEY` hides and rejects them; authenticated integrations use the eleven core tools in [mcp-tools.md](mcp-tools.md).

```text
You are connected to Alice, the user's local-first memory and continuity layer.

Default loop — one first call, then act, then write back:
1. Call alice_context_pack ONCE with a scoped query before planning, answering, or acting on important user context. Do not stitch together raw searches first; the pack already carries memories, open loops, sources, contradictions, and honest gaps.
2. Act on the task, treating staleness notes and contradicting_evidence as caution signals.
3. When the user explicitly says to remember, save, or add a durable fact to memory, call alice_memory_commit. For inferred, external, generated, ambiguous, or lower-confidence facts, call alice_capture instead (source-backed, review-gated).
4. Finish lifecycle work with alice_memory_manage (confirm / undo / forget) and track unresolved work with alice_open_loops.

Choosing context depth (request field context_depth; all tiers are deterministic retrieval — no tier synthesizes with a model):
- minimal: single-fact lookups and quick pre-flight checks. Full-text only, at most 4 memories, no sources or contradictions.
- low (default): normal task context before acting.
- medium: reviews, plans, and daily briefings — the contradiction check runs for every query type.
- high: audits and long-history questions — adds supersession chain notes for revised memories.
Explicit include_sources / include_contradictions flags override the tier default.

Never directly mutate trusted memory.
Never write directly to Postgres.
Never bypass Alice policy.
Never request sensitive domains unless needed and allowed.
Use /vnext review queues for human approval, audit, undo, correction, and forget flows.
```

`context_depth` (and `budget_strategy` for token budgets) are fields on
Alice's context-pack request; the matching `alice_context_pack` MCP tool
arguments arrive in the same release — trust the server's `tools/list`
schema and omit the argument if the server does not list it yet.

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

Recipes (each starts with one `alice_context_pack` call):

- Daily planning context: ask for today's project, professional, and open-loop context (`medium` depth — briefings should surface contradictions).
- Meeting preparation context: query the meeting name and attendees with `professional` and `project` domains (`low` depth).
- Quick fact check ("do we know X?"): `minimal` depth — cheapest useful call.
- Follow-up context: query open loops and recent decisions (`low` depth).
- Project briefing context: use project-scoped context before advising (`medium` depth; `high` when history or revisions matter).
- Personal assistant memory commit: commit only explicit stable preferences or durable decisions through Alice.
- Quote memory commit: use `memory_type=semantic`; if a domain is needed for quote collections, use `domain=learning`.
- Personal assistant memory proposal: propose inferred, external, or lower-confidence facts for review.
- Artifact submission: ingest plans and summaries as reviewable agent outputs.

Use only schema-backed enum values for persisted fields. Do not send invented labels such as `memory_type=quote`, `domain=quotes`, or `sensitivity=sensitive`; Alice normalizes common aliases, but canonical values keep MCP calls predictable.

Good explicit commit:

```json
{
  "agent_id": "hermes",
  "agent_type": "personal_assistant",
  "permission_profile": "trusted_local_agent",
  "intent": "explicit_remember",
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
- `confirmation_required`: show the proposed text and call `alice_vnext_confirm_memory` only after the user confirms.
- `review_required`: leave the candidate in `/vnext` review.
- `rejected`: do not retry without narrowing scope or asking the user.

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
  "canonical_text": "The user might dislike long reports.",
  "confidence": 0.31,
  "rationale": "Speculative inference from one short reply."
}
```
