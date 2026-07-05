# MCP Tools

Alice exposes eleven core MCP tools by default. Every parameter carries a
description, so MCP-capable agents can use the surface without reading this
page — this page exists for humans wiring things up. For the full verb
contract — outcomes, audit guarantees, and honest boundaries — see the
[Memory Operations Protocol](../memory-operations-protocol.md).

## Start the server

```bash
alicebot-mcp
# or, from an editable install:
./.venv/bin/python -m alicebot_api.mcp_server
```

Claude Desktop / IDE config:

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

> **No Postgres yet?** `alice-memory mcp --data-dir ~/.alice` serves the
> same eleven core tools against a local SQLite file — no `DATABASE_URL`
> needed. Works from a repo checkout today (`pip install -e .`);
> `uvx alice-memory` once the package is published. SQLite-mode boundaries
> are listed in [known limitations](known-limitations.md).

## The eleven core tools

**Write and review**

- `alice_capture` — submit new information as source-backed, reviewable
  memory. Text is stored verbatim with provenance and becomes trusted
  memory only after review.
- `alice_memory_commit` — write one explicit memory on the user's
  instruction ("remember this"). Policy-checked, never blind: the outcome
  is `committed`, `confirmation_required`, `review_required`, or
  `rejected`, always with provenance, a revision, and an audit event.
- `alice_memory_review` — inspect the review queue, or one item in detail.
- `alice_memory_correct` — act on a memory: approve, edit-and-approve,
  reject, or supersede with a replacement. Every change is audited.
- `alice_memory_manage` — lifecycle verbs for committed memories: `confirm`
  a pending confirmation, `undo` a commit, `forget` a memory, `expire` /
  `unexpire` its validity window, `accept_consolidation` for a
  consolidation candidate, or `redact` its content. Undo, forget, and
  expire hide the memory from recall but keep its revisions and events;
  redact permanently expunges the content from the row, revisions, and
  event payloads while keeping the audit skeleton. Redact and
  accept_consolidation require a human operator or an admin agent, and
  expire/unexpire/accept_consolidation/redact all require a `reason`.

**Read**

- `alice_recall` — search memory. Full-text plus semantic vector search,
  merged with reciprocal-rank fusion. Falls back to full-text only (and
  says so) when no embedding endpoint is configured. Accepts optional
  `memory_types` (typed filter, e.g. only `decision` or `procedure`
  memories) and `projects` (project-scope filter) arrays, plus
  `context_depth` (`minimal` runs full-text only and caps results at 4;
  `low` is the default hybrid behavior) and `budget_strategy`
  (`facts_first` / `recent_first` reorder results; `balanced` is the
  default).
- `alice_context_pack` — a scoped context bundle for a task: relevant
  memories, open loops, and sources with supporting evidence. Accepts the
  same `memory_types` filter, and `max_tokens` is enforced: lowest-ranked
  items are dropped to fit the budget and the response carries a
  `token_report` (`token_budget`, `token_estimate`, `truncated`,
  `dropped_item_count`). `context_depth` picks the cost/coverage tier
  (`minimal` | `low` | `medium` | `high`) and `budget_strategy` decides how
  a tight token budget is spent (`balanced` | `facts_first` |
  `recent_first` | `contradictions_first` | `sources_first`). The
  `include_sources`/`include_contradictions` flags are tri-state: omit them
  to let the `context_depth` tier decide; an explicit true/false always
  wins.
- `alice_resume` — a pick-work-back-up brief: last decision, suggested next
  action, open loops, recent changes; scopable to a project, person, or
  thread.
- `alice_recent_decisions` — recent decisions, newest first.
- `alice_open_loops` — list open loops, or close/snooze/edit/reopen one.
- `alice_explain` — where a memory came from and why it can be trusted:
  sources, revisions, corroboration, contradiction signals.

Exact input schemas (types, enums, defaults) are in the `tools/list`
response; they are the source of truth.

To run the MCP server under a specific agent identity, set
`ALICE_AGENT_API_KEY` in the server env to a key created with
`alicebot agent keys create` (see
[agent-integration.md](agent-integration.md)). Without it, the server runs
as local operator tooling.

## The debug flag

`alice_recall`, `alice_context_pack`, and `alice_resume` accept
`"debug": true`. Responses are compact by default; the debug flag attaches
the retrieval trace — which stages ran, candidate counts, and whether
vector search was active or degraded to full-text (and why).

## Embeddings

Semantic search activates when an OpenAI-compatible embeddings endpoint is
configured (Ollama, LM Studio, OpenAI):

```bash
ALICE_EMBEDDINGS_BASE_URL=http://localhost:11434/v1
ALICE_EMBEDDINGS_MODEL=nomic-embed-text
ALICE_EMBEDDINGS_API_KEY=   # only if the endpoint requires one
```

Without these, `alice_recall` and `alice_context_pack` still work on
full-text search alone.

## Explicit memory commits

Trusted agents write explicit "remember this" instructions through
`alice_memory_commit`. Alice decides the outcome, never the agent:

- `committed` — direct active memory with provenance, event log, revision.
- `confirmation_required` — sensitive or ambiguous memory waits for
  `alice_memory_manage` with `action: "confirm"`.
- `review_required` — external, generated, or low-confidence memory waits
  for human review in the console.
- `rejected` — out-of-scope, unsafe, or policy-bypass attempts are blocked.

Use canonical schema values for persisted labels: `memory_type=semantic`
for quote saves, `memory_type=procedure` for repeatable playbooks. Avoid
invented values like `memory_type=quote` or `sensitivity=sensitive` (the
schema enums in `tools/list` are the source of truth).

Normal chat is not guaranteed to become trusted memory; agents should call
an explicit commit for user-directed memory instructions. For first-run
expectations and worked examples, see [first-memory.md](first-memory.md);
for the full verb contract see the
[Memory Operations Protocol](../memory-operations-protocol.md).

## Legacy tool surface

Earlier releases exposed a 74-tool surface. The long tail remains available
behind an environment flag for integrations that depend on it:

```bash
ALICE_MCP_LEGACY_TOOLS=1
```

With the flag set, `tools/list` includes the full long tail — for example
`alice_vnext_ingest_agent_output` for structured agent-output ingestion,
`alice_recall_debug` for the legacy continuity recall view, and the
granular queue/graph/belief tools. `alice_vnext_commit_memory`,
`alice_vnext_confirm_memory`, `alice_vnext_undo_memory`, and
`alice_vnext_forget_memory` remain as aliases of the same handlers that now
power `alice_memory_commit` and `alice_memory_manage` on the core surface.
Calling a legacy tool without the flag returns an error naming the flag.
New integrations should stay on the eleven core tools; the legacy surface
is frozen and will not gain new capabilities.

## Trust boundary

- MCP tools create reviewable sources, artifacts, open loops, and memory
  proposals; trusted writes go through the memory commit policy engine,
  never direct database mutation.
- Blocked calls return explicit policy reasons (for example
  `all_requested_domains_restricted`); agents should narrow scope or ask
  the user instead of retrying broadly.
