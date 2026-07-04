# OpenClaw Alice Project Memory Skill

Use this instruction block in OpenClaw when Alice is available.

Note: the structured ingestion and memory-commit MCP payloads below target the legacy `alice_vnext_*` tool surface, which requires `ALICE_MCP_LEGACY_TOOLS=1` on the Alice MCP server. The default surface is the nine core tools in [mcp-tools.md](mcp-tools.md).

```text
You are OpenClaw. Use Alice as the project-scoped memory and continuity layer.

1. Identify as OpenClaw.
2. Request a project-scoped context pack before build or review work.
3. Perform the assigned task.
4. Submit the sprint output to Alice as reviewable agent output.
5. Commit durable memory only for explicit user-directed project facts through Alice's memory commit path.
6. Propose review-only memory for generated summaries, external evidence, contradictions, or lower-confidence facts.
7. Create open loops for unresolved work.
8. Do not access or write non-project personal domains.
```

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

Project context recipe:

```json
{
  "query": "current sprint decisions, architecture constraints, open loops",
  "scope": {
    "domains": ["project"],
    "projects": ["Alice"]
  },
  "options": {
    "sensitivity_allowed": ["public", "internal", "private", "unknown"],
    "max_items": 10
  }
}
```

Sprint output ingestion:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "openclaw-sprint-001",
  "task_id": "public-alpha-packaging",
  "project_scope": ["Alice"],
  "title": "OpenClaw sprint summary",
  "content": "Decision: Public alpha agents use scoped context packs and review-only memory proposals.",
  "output_type": "sprint_summary",
  "domain": "project",
  "sensitivity": "private",
  "propose_memory": true
}
```

Explicit project memory commit:

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "permission_profile": "project_scoped_agent",
  "project_scope": ["Alice"],
  "intent": "explicit_remember",
  "title": "Release gate decision",
  "canonical_text": "Alice public preview release gates require doctor, smokes, evals, and git diff checks before merge.",
  "domain": "project",
  "sensitivity": "private",
  "confidence": 0.94,
  "source_type": "direct_user_instruction"
}
```

If Alice returns `review_required`, leave the item in `/vnext`. If Alice returns `rejected`, do not retry outside the `project` domain. Use Alice's undo, correct, or forget tools for repairs; never write directly to Postgres.

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
