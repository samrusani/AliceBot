# OpenClaw Alice Project Memory Skill

Use this instruction block in OpenClaw when Alice is available.

Note: the structured ingestion and memory-commit MCP payloads below target the legacy `alice_vnext_*` tool surface. They require a deliberately keyless local server with `ALICE_MCP_LEGACY_TOOLS=1`; a server bound with `ALICE_AGENT_API_KEY` hides and rejects them. New authenticated integrations should use the eleven core tools in [mcp-tools.md](mcp-tools.md).

```text
You are OpenClaw. Use Alice as the project-scoped memory and continuity layer.

Default loop — one first call, then act, then write back:
1. Identify as OpenClaw.
2. Call alice_context_pack ONCE, project-scoped, before build or review work. The pack already carries decisions, procedures, open loops, sources, and contradictions — do not run raw searches first.
3. Perform the assigned task, treating staleness notes and contradicting_evidence as caution signals.
4. Commit durable project memory via alice_memory_commit whenever you learn something worth keeping, including when the user has not asked you to remember it. It is the write verb for ordinary memory and what it records is immediately recallable. Use alice_capture for source documents, external evidence and raw notes: it is review-gated, so alice_recall will not return it until a human reviews it. Submit sprint outputs as reviewable agent outputs.
5. Finish lifecycle work with alice_memory_manage (confirm / undo / forget) and create open loops for unresolved work with alice_open_loops.
6. Do not access or write non-project personal domains.

Choosing context depth (request field context_depth; every tier is deterministic retrieval — none synthesizes with a model):
- minimal: quick fact checks ("did we already decide X?"). Full-text only, at most 4 memories, no sources or contradictions.
- low (default): normal pre-task context.
- medium: code review, sprint planning, or status reporting — contradiction check forced on for every query type.
- high: audits and revision-history questions — adds supersession chain notes for superseded/superseding memories.
Explicit include_sources / include_contradictions flags override the tier default.
```

`context_depth` (and `budget_strategy` for `max_tokens` packing) are
fields on the context-pack request; the matching `alice_context_pack` MCP
tool arguments arrive in the same release — trust the server's
`tools/list` schema and omit them if not listed yet.

Default identity:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "permission_profile": "project_scoped_agent",
  "project_scope": ["Alice"]
}
```

Allowed direct commit domain: `project`.

Context/read domains may include `project`, `professional`, and `system` when policy allows.

Restricted by default: `personal`, `family`, `health`, `spiritual`, `legal`, `financial`, `regulated`.

Project context recipe. On the core `alice_context_pack` the scope fields are flat, not nested
under `scope` and `options`:

```json
{
  "query": "current sprint decisions, architecture constraints, open loops",
  "domains": ["project"],
  "projects": ["Alice"],
  "sensitivity_allowed": ["public", "internal", "private", "unknown"],
  "max_items": 10
}
```

Sprint output, submitted through `alice_capture` so it lands review-gated. The field carrying
the text is `raw_text`:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "openclaw-sprint-001",
  "task_id": "public-alpha-packaging",
  "project_scope": ["Alice"],
  "title": "OpenClaw sprint summary",
  "raw_text": "Decision: Public alpha agents use scoped context packs and review-only memory proposals.",
  "domain": "project",
  "sensitivity": "private"
}
```

Project memory commit:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "permission_profile": "project_scoped_agent",
  "project_scope": ["Alice"],
  "title": "Release gate decision",
  "canonical_text": "Alice public preview release gates require doctor, smokes, evals, and git diff checks before merge.",
  "domain": "project",
  "sensitivity": "private",
  "confidence": 0.94,
  "source_type": "direct_user_instruction"
}
```

`title` and `canonical_text` are the only required fields. Every other property must appear in
the server's `tools/list` schema for the tool you are calling; an unrecognised property is
rejected outright rather than ignored. In particular `intent` exists only on the legacy
`alice_vnext_commit_memory` tool and is **not** accepted by `alice_memory_commit`. A
`project_scoped_agent` must send `domain: "project"`, or the commit is rejected.

If Alice returns `review_required`, leave the item for `alice_memory_review`. If Alice returns
`rejected`, do not retry outside the `project` domain. Use `alice_memory_manage` with an
`action` of `undo`, `forget` or `expire` for repairs; never write directly to the database.

Do propose memory for:

- accepted architecture decisions
- durable project direction
- unresolved release risks
- post-sprint state changes

Do not propose memory for:

- raw logs
- temporary implementation chatter
- duplicated source text
- private personal context outside the project scope
