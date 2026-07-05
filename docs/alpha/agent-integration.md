# Agent Integration Pack

Agents should use Alice as a durable, private, provenance-aware, reviewable memory layer.

## Connect your agent in 5 minutes

1. Point your MCP-capable agent at the Alice MCP server:

```json
{
  "mcpServers": {
    "alice": {
      "command": "/ABSOLUTE/PATH/TO/AliceBot/.venv/bin/python",
      "args": ["-m", "alicebot_api.mcp_server"],
      "cwd": "/ABSOLUTE/PATH/TO/AliceBot",
      "env": {
        "DATABASE_URL": "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot",
        "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001"
      }
    }
  }
}
```

   No Postgres yet? `alice-memory mcp --data-dir ~/.alice` serves the same
   eleven core tools against a local SQLite file — no `DATABASE_URL` needed.

2. (Recommended) Bind the server to an agent identity: create a key with
   `alicebot agent keys create` and set `ALICE_AGENT_API_KEY` in the MCP
   server env (details under [Authentication](#authentication)).
3. Drop one of the skill blocks into your agent's instructions:
   [hermes-skill.md](hermes-skill.md) for personal assistants,
   [openclaw-skill.md](openclaw-skill.md) for coding agents.
4. Ask the agent something it should need memory for. Its first tool call
   should be `alice_context_pack`.

## The default loop

One first call, then act, then write back:

1. **`alice_context_pack`** — ONE scoped call before planning or acting.
   The pack carries relevant memories, open loops, sources, supporting
   evidence, contradictions, and honest gaps (`missing_information`,
   `warnings`) — do not stitch together raw searches first.
2. **Act** — perform the task with the pack as ground truth. Treat
   `staleness` notes and `contradicting_evidence` as caution signals.
3. **Write back through Alice** — `alice_memory_commit` for explicit
   "remember/save/add to memory" instructions; `alice_capture` for
   inferred, external, generated, ambiguous, or lower-confidence facts
   (source-backed, review-gated).
4. **Close the loop** — `alice_memory_manage` for `confirm`/`undo`/`forget`
   follow-ups, and `alice_open_loops` to create or close open loops for
   unresolved work.

Respect domain and sensitivity policy on every call, and use `/vnext` for
review, audit, undo, correction, forget, and troubleshooting.

### Which context depth to request

The context-pack request accepts `context_depth` (default `low`). Every
tier is deterministic retrieval and packing — no tier performs LLM
synthesis or summarization. Pick the cheapest tier that answers the
question class:

| `context_depth` | Question class | What runs |
| --- | --- | --- |
| `minimal` | Single-fact lookups, quick pre-flight checks, "do I know X at all?" | Full-text stage only (no vector, no graph hop), at most 4 memories, no sources, no contradictions, no typed sections, no recent changes. The cheapest useful call. |
| `low` (default) | Normal task context before acting | Hybrid full-text + vector + entity-graph retrieval, sources, open loops, supporting evidence; contradiction check only for strategic query shapes (status, synthesis, contradiction, agent-context queries). |
| `medium` | Reviews, plans, status reports, anything you will assert to the user | Everything `low` does, plus the contradiction check forced on for every query type. That contradictions default is the only difference between `low` and `medium`. |
| `high` | Audits, conflicting-history questions, resuming long-running work | Everything `medium` does, plus compact supersession chain notes (`supersession_context`) for packed memories that supersede or are superseded by other revisions, and the resolved `entities` list whenever the query matched entities. |

Explicit `include_sources` / `include_contradictions` flags always override
the tier default — the caller wins (e.g. `minimal` plus
`include_sources: true` returns sources). The tier is echoed back as
`context_depth` on the pack and in the retrieval trace, and skipped stages
report honest statuses such as `disabled: context_depth=minimal`.

### Budget strategies and the allocation report

When the request sets `max_tokens`, a greedy packer drops lowest-priority
items to fit. `budget_strategy` (default `balanced`) controls the packing
order — never what was retrieved or ranked:

| `budget_strategy` | Packs first | Reach for it when |
| --- | --- | --- |
| `balanced` (default) | memories, then open loops, sources, evidence quotes, contradictions | General use. |
| `facts_first` | Same section order; `semantic`/`decision`/`preference` memories boosted to the front of the memories list | Durable facts and decisions matter more than narrative under a tight budget. |
| `recent_first` | Same section order; memories ordered newest-first before fused rank | "What changed" and freshness-sensitive tasks. |
| `contradictions_first` | Contradiction records before everything else | Verification and consistency checks — contradictions survive even when the memories themselves get dropped. |
| `sources_first` | Sources before memories | Citation-heavy, evidence-first workflows. |

The pack's `budget` report shows where the budget went:
`{token_budget, token_estimate, truncated, dropped_item_count, strategy,
allocation}`, where `allocation` is per-section token estimates
(`relevant_memories`, `open_loops`, `sources`, `supporting_evidence`,
`contradicting_evidence`) that always sum to `token_estimate`.

`context_depth` and `budget_strategy` are fields on the context-pack
request across the service surfaces; the matching `alice_context_pack` MCP
tool arguments land in the same release — check the server's `tools/list`
response (the source of truth for input schemas) before passing them, and
keep tool payloads generic otherwise.

The full verb contract — remember, recall, correct, confirm, undo, forget,
audit — with outcomes and audit guarantees per verb is documented in the
[Memory Operations Protocol](../memory-operations-protocol.md).

## Agent Identity Fields

```json
{
  "agent_id": "openclaw",
  "agent_type": "coding_agent",
  "agent_run_id": "run-2026-05-12-001",
  "task_id": "alice-public-alpha",
  "project_scope": ["Alice"],
  "permission_profile": "project_scoped_agent"
}
```

Permission profiles:

- `read_only_agent`: context lookup only
- `project_scoped_agent`: project context, project outputs, explicit project-domain memory commits, and review-only proposals
- `trusted_local_agent`: broader local assistant context, still policy-filtered
- `memory_proposal_agent`: proposal-focused agent
- `admin_agent`: scheduler and administrative actions

## Authentication

Custom agents calling the HTTP API authenticate with per-agent API keys. Create one per agent:

```bash
alicebot agent keys create --agent-id openclaw --profile project_scoped_agent --label "OpenClaw laptop"
```

The raw key (`alice_sk_...`) is printed exactly once; only its sha256 hash is stored. Export it and pass it on every agent HTTP call — never paste raw keys into scripts or docs:

```bash
export ALICE_AGENT_API_KEY="<paste the key printed by 'agent keys create'>"

curl -X POST http://127.0.0.1:8000/v0/vnext/memories/commit \
  -H "Authorization: Bearer $ALICE_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "...", "title": "...", "text": "..."}'
```

Rules:

- With a valid key, `agent_id` and `permission_profile` come from the key record, not the payload. A payload may claim a lower profile (downgrade), but claiming a different `agent_id` or a higher profile is rejected with `403` and logged as `agent.key_escalation_rejected`.
- Fresh local installs keep working without keys: while a user has no active keys, keyless agent calls fall back to the self-asserted identity and are audited with `auth: "unauthenticated_local"`.
- The moment at least one active key exists, keyless agent calls are rejected with `401` until the key is passed as `Authorization: Bearer alice_sk_...`.
- Manage keys with `alicebot agent keys list` (prefixes only, never hashes) and `alicebot agent keys revoke <key-prefix-or-id>`.
- MCP servers bind a key the same way: set `ALICE_AGENT_API_KEY` in the MCP server env.

## Scopes

Memories carry four scopes. `user_id` is the hard tenancy boundary (RLS);
the rest are first-class columns filled by the agentic write path and
filterable on the read path:

- **`project_id`** — set on commit when the effective project scope is
  singular (from the request's `project_scope`, falling back to the
  identity's). `alice_recall` and `alice_context_pack` filter on it via
  `projects`; the read path also falls back to legacy
  `metadata_json.project_id` during the transition.
- **`created_by_agent_id`** — the *authenticated* agent that wrote the
  memory. Filter with the optional `created_by_agents` array on
  `alice_recall` / `alice_context_pack` (e.g. `["openclaw"]`).
- **`run_id`** — the writing agent's `agent_run_id`. Deliberately
  metadata-plus-filter only: there is no session entity or foreign key
  behind it, so runs cost nothing to mint and old runs need no cleanup.
  Store-level searches accept an optional `run_id` filter.

Project binding closes the trust gap between a key and the payload's
self-asserted `project_scope`:

```bash
alicebot agent keys create --agent-id openclaw --profile project_scoped_agent \
  --project-scope Alice
```

When a key carries `--project-scope`, the resolved identity's project scope
comes from the key record. A payload may narrow the scope to a subset but
never widen it — widening is rejected with `403` and audited as
`agent.key_escalation_rejected` (reason `project_scope_escalation`), the
same pattern as permission-profile escalation. Write actions that carry a
`project_id` outside the bound scope are blocked by policy with reason
`project_scope_binding_violation`. Keys issued without `--project-scope`
keep the previous behavior: the payload's `project_scope` is honored as-is.

## Explicit Memory Commits

When the user says "remember this", commit it through `alice_memory_commit`
on the core MCP surface (or `POST /v0/vnext/memories/commit` over HTTP,
`alicebot vnext memories commit` on the CLI). The commit is policy-checked
and returns one of four outcomes — `committed`, `confirmation_required`
(finish with `alice_memory_manage` action `confirm`), `review_required`, or
`rejected` — never a silent write. Follow-up lifecycle verbs (`confirm`,
`undo`, `forget`) live on `alice_memory_manage`.

Identity requirements:

- Commits without an agent identity are rejected with
  `agent_identity_required`. Pass the identity fields above, or bind a key.
- Only `trusted_local_agent` and `admin_agent` profiles can commit outside
  the `project` domain; `project_scoped_agent` commits are limited to
  project-domain memories within their project scope;
  `memory_proposal_agent` and `read_only_agent` callers are routed to
  review or rejected.
- On HTTP, once any agent API key exists for the user, keyless commits are
  rejected with `401`; callers must send `Authorization: Bearer
  alice_sk_...`.
- On MCP, set `ALICE_AGENT_API_KEY` in the server environment to bind the
  server to a key; without it the MCP server runs as local operator
  tooling and payload identity is honored (audited as
  `unauthenticated_local`).
- When a key is in play, the key record — not the payload — determines
  `agent_id` and `permission_profile`; claiming a different agent or a
  higher profile is rejected and logged. Key enforcement works in SQLite
  on-ramp mode too.

## CLI Example

```bash
alicebot context-pack "Alice public preview sprint context" --domain project --project Alice

alicebot vnext agents ingest-output \
  --agent-id openclaw \
  --agent-type coding_agent \
  --agent-run-id run-2026-05-12-001 \
  --project-scope Alice \
  --permission-profile project_scoped_agent \
  --title "OpenClaw sprint summary" \
  --output-type sprint_summary \
  --domain project \
  --sensitivity private \
  --propose-memory \
  "Decision: Alice public preview agents use scoped context packs and review-only memory proposals."

alicebot vnext memories commit \
  --agent-id openclaw \
  --agent-type coding_agent \
  --agent-run-id run-2026-05-12-001 \
  --project-scope Alice \
  --permission-profile project_scoped_agent \
  --title "Release gate decision" \
  --text "Alice public preview release gates require doctor, smokes, evals, and git diff checks before merge." \
  --domain project \
  --sensitivity private \
  --confidence 0.94
```

## Smoke

```bash
alicebot vnext smoke agent-integration-pack
alicebot vnext smoke agentic-memory-commit
```

The smokes verify scoped context, output ingestion, explicit trusted memory commits, inline confirmation, review gating, undo/correction/forget, no direct database mutation, event logging, restricted-domain policy blocking, and `/vnext` agent activity visibility.
