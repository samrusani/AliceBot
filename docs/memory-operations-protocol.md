# The Memory Operations Protocol

Agent memory is only trustworthy if every write can be traced, checked, and
taken back. Alice exposes memory as a small set of verbs — the same verbs on
MCP, HTTP, and the CLI — and every one of them runs through the same policy
engine and lands in the same audit trail. Agents request; Alice decides.

Eight verbs cover the lifecycle of a memory:

| Verb | What it does | Status |
|---|---|---|
| [remember](#remember) | Write a memory — explicit commit or source-backed capture | Shipped |
| [recall](#recall) | Search memory with hybrid full-text + vector retrieval | Shipped |
| [correct](#correct) | Fix an existing memory, keeping the old version | Shipped |
| [confirm](#confirm) | Complete a write that policy held for confirmation | Shipped |
| [undo](#undo) | Reverse a commit without erasing its history | Shipped |
| [forget](#forget) | Retire a memory from recall on request | Shipped |
| [audit](#audit) | Explain a memory: sources, revisions, events | Shipped |
| [merge / expire](#merge--expire-planned) | Consolidate duplicates; age out stale facts | Planned |

All shipped verbs are on the default (core) MCP surface — no
`ALICE_MCP_LEGACY_TOOLS` flag needed — and all of them work in SQLite
on-ramp mode as well as against Postgres.

## The outcome vocabulary

A write is never a silent success or a silent drop. Every `remember` returns
one of four outcomes, decided by the memory commit policy engine:

| Outcome (`status`) | Write mode | Meaning |
|---|---|---|
| `committed` | `commit` | Written as active, trusted memory immediately |
| `confirmation_required` | `confirm_inline` | Held for an inline yes/no — finish with [confirm](#confirm) |
| `review_required` | `propose_review` | Parked as a candidate for human review |
| `rejected` | `reject` | Blocked, with machine-readable `reasons` |

What routes where (from `evaluate_memory_commit_policy`):

- No agent identity, blocked policy, or secret-looking content (API keys,
  tokens, passwords) → `rejected`.
- Confidence below 0.5, external source types (email, web pages, generated
  artifacts), non-explicit intent, or bulk source references → `review_required`.
- Confidence between 0.5 and 0.85, sensitive domains (health, family,
  financial, legal, spiritual), sensitivity above `private`, or declared
  contradictions → `confirmation_required`.
- Everything else from a trusted or project-scoped agent → `committed`.

## Audit guarantees

Every verb below appends to two append-only stores:

- **Revisions** (`memory_revisions`): each state change records the previous
  and new value, the text before and after, a typed `revision_type`
  (`created`, `corrected`, `promoted`, `rejected`, `superseded`, `archived`,
  …), the reason, and the actor.
- **Events** (`event_log`): each verb emits a typed event
  (`agent.memory_committed`, `agent.memory_confirmed`,
  `agent.memory_corrected`, `agent.memory_undone`, `agent.memory_forgotten`,
  plus the policy decision events), correlated by `trace_id` and the agent's
  `run_id`.

Committed memories also carry **provenance links** to their source
references, so [audit](#audit) can answer "where did this come from?".

## Identity and authentication

Every write verb accepts agent identity fields (`agent_id`, `agent_type`,
`agent_run_id`, `task_id`, `project_scope`, `permission_profile`). Writes
without an identity are rejected. When per-agent API keys exist,
identity is resolved and enforced from the key record — on HTTP via
`Authorization: Bearer alice_sk_...`, on MCP via `ALICE_AGENT_API_KEY` in
the server environment. Claiming another agent's id or a higher permission
profile is refused and logged. See
[agent-integration.md](alpha/agent-integration.md).

---

## remember

Two paths, one trust boundary:

- **Explicit commit** — the user said "remember this" and the agent writes
  it through policy:
  - MCP: `alice_memory_commit`
  - HTTP: `POST /v0/vnext/memories/commit`
  - CLI: `alicebot vnext memories commit --title ... --text ...`
- **Source-backed capture** — documents, notes, and evidence that become
  trusted memory only after review:
  - MCP: `alice_capture`
  - HTTP: `POST /v0/vnext/sources`
  - CLI: `alicebot vnext agents ingest-output ...` (for agent outputs)

Outcomes: the four-outcome vocabulary above for commits; captures return
`imported` with candidate memories that wait in the review queue.

Audit: a `created` revision, provenance links for `source_refs`, and an
`agent.memory_committed` / `agent.memory_confirmation_required` /
`agent.memory_review_required` / `agent.memory_commit_rejected` event.
Commits accept an `idempotency_key`; retries replay the original result
instead of double-writing.

## recall

Hybrid retrieval: full-text and semantic vector search fused with
reciprocal-rank fusion, filtered by domain, sensitivity, memory type, and
project scope.

- MCP: `alice_recall` (single query) and `alice_context_pack` (task-scoped
  bundle with a `max_tokens` budget and a `token_report` of what was dropped)
- HTTP: `POST /v0/vnext/context-packs`
- CLI: `alicebot context-pack "query" ...`

Only searchable statuses (`active`, `accepted`) are returned: candidates,
rejected, superseded, and forgotten memories never leak into results.

## correct

Two correction surfaces, both audited:

- **Review-queue correction** — act on a memory awaiting review:
  - MCP: `alice_memory_correct` with `action` of `approve`,
    `edit-and-approve`, `reject`, or `supersede-existing`
  - HTTP: `POST /v0/vnext/memories/{memory_id}/review` (actions `accept`,
    `edit`, `reject`, `private`, `assign_project`, `promote`)
  - Console: the `/vnext` review queue drives the same endpoint
- **Agentic correction** — rewrite the text of a committed memory:
  - HTTP: `POST /v0/vnext/memories/correct`
  - CLI: `alicebot vnext memories correct <memory_id> --text ...`

Outcome: `committed` with the corrected text active. Audit: a `corrected`
revision storing the text before and after, and an
`agent.memory_corrected` event. The pre-correction text is preserved in the
revision history, and correction history accumulates on the memory record.

## confirm

Completes a write that policy held as `confirmation_required` (the pending
memory is not searchable until confirmed).

- MCP: `alice_memory_manage` with `action: "confirm"` and the
  `confirmation_id` from the commit response; pass `canonical_text` to
  confirm with a correction
- HTTP: `POST /v0/vnext/memories/confirm`
- CLI: `alicebot vnext memories confirm <confirmation_id> [--action confirm|reject|edit]`

Outcomes: `committed` (memory becomes active) or `rejected`. Confirmations
expire after 24 hours; an expired confirmation resolves to `rejected` with
reason `confirmation_expired`. Audit: a `promoted` (or `corrected`, when
text was edited) revision and an `agent.memory_confirmed` or
`agent.memory_confirmation_rejected` event.

## undo

Reverses a commit. The memory leaves recall; its history stays.

- MCP: `alice_memory_manage` with `action: "undo"` (`memory_id` optional —
  defaults to the calling agent's most recent commit)
- HTTP: `POST /v0/vnext/memories/undo`
- CLI: `alicebot vnext memories undo [--memory-id ...]`

Outcome: `undone`; the memory's status becomes `superseded`. Audit: a
`superseded` revision and an `agent.memory_undone` event.

## forget

Retires a memory on request — "stop using this."

- MCP: `alice_memory_manage` with `action: "forget"` and `memory_id`
- HTTP: `POST /v0/vnext/memories/forget`
- CLI: `alicebot vnext memories forget <memory_id> [--reason ...]`

Outcome: `forgotten`; the memory's status becomes `superseded`. Audit: an
`archived` revision and an `agent.memory_forgotten` event.

**The honest boundary:** forget is a soft delete plus exclusion. The memory
disappears from recall, context packs, and resume briefs, but its content
remains in the revision history and event log — that is what makes forget
reversible and auditable. True content redaction (scrubbing revisions and
events) is a planned feature; until it ships, do not treat forget as
cryptographic erasure.

## audit

Explains a memory end to end: the row itself, every revision, every event,
and its provenance links back to sources.

- MCP: `alice_explain` with `memory_id` (also accepts `continuity_object_id`
  or `entity_id` on the Postgres backend)
- HTTP: `GET /v0/vnext/memories/{memory_id}/audit`
- CLI: `alicebot vnext memories audit <memory_id>`

Recent write activity is listable via `GET /v0/vnext/memories/recent-commits`
and `alicebot vnext memories recent`.

## merge / expire (planned)

- **merge** — consolidating near-duplicate memories into one, behind the
  existing candidate/review gate: planned; see the consolidation milestone
  in [docs/plans/memory-frontier.md](plans/memory-frontier.md).
- **expire** — aging out time-bounded facts: memories whose validity window
  has closed (`valid_to` in the past) are already excluded from search; the
  `stale` status and scheduled expiry sweep are landing next — see
  staleness v1 in [docs/plans/memory-frontier.md](plans/memory-frontier.md).

---

For the full MCP tool schemas see [docs/alpha/mcp-tools.md](alpha/mcp-tools.md);
for identity, keys, and worked agent examples see
[docs/alpha/agent-integration.md](alpha/agent-integration.md).
