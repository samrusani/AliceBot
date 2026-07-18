# Alice v0.12.0 Phase 3 Surface Inventory

**Structure only. Zero behavior change.**

- Scope: Phase 3 structural moves only
- Base commit: `f342d45dabe127acca6231f29830ff11d98a340e`
- Base tree: `1d84e26597aecfcd9ad894c6d0b86fbe9a66dfd6`
- Branch: `codex/v0120-phase3-structural-refactor`
- Target: `v0.12.0`
- Governed source versions: `0.11.1` until the release-engineer cut

## Base-to-carrier size inventory

| Base carrier | Base lines | Final facade | Final lines | Extracted shape |
|---|---:|---|---:|---|
| `main.py` | 12,856 | `main.py` | 1,140 | domain routers; largest router 2,440 |
| `store.py` | 9,202 | `store.py` | 1,692 | five surviving-domain legacy modules; largest 2,699 |
| `vnext_store.py` | 8,174 | `vnext_store.py` | 3,595 | paired PostgreSQL/SQLite seam modules; largest 1,305 |
| `mcp_tools.py` | 7,431 | `mcp_tools.py` | 564 | registry plus per-domain MCP modules; largest 1,926 |
| `cli.py` | 7,019 | `cli/__init__.py` | 80 | parser plus per-domain command modules; largest 1,909 |
| `contracts.py` | 5,915 | `contracts.py` | 1,964 | nine domain contract modules; largest 2,161 |
| `sqlite_store.py` | 5,212 | `sqlite_store.py` | 1,563 | SQLite counterparts to vNext seams; largest 1,158 |

The largest final production Python file is the unchanged
`vnext_retrieval.py` at 3,803 lines. No production Python file exceeds 4,000
lines.

## HTTP routers

| Module | Lines | Boundary |
|---|---:|---|
| `routers/providers.py` | 2,440 | provider/runtime/configuration handlers |
| `routers/memories_legacy.py` | 1,854 | default-compatible legacy memory endpoints |
| `routers/legacy_gated.py` | 1,760 | conditionally mounted legacy surface |
| `routers/vnext_memories.py` | 1,644 | vNext capture/review/lifecycle memory endpoints |
| `routers/continuity.py` | 1,569 | continuity and synthesis endpoints |
| `routers/vnext_review.py` | 1,000 | artifacts, queue, and project-update review |
| `routers/vnext_projects.py` | 607 | vNext project endpoints |
| `routers/workspaces.py` | 336 | workspace/bootstrap endpoints |
| `routers/vnext_retrieval.py` | 329 | recall/resume/context-pack endpoints |

Shared router helpers remain subordinate carriers. The stable production import
is `alicebot_api.main:app`. Conditional mounting stays import-time and preserves
the existing legacy flag behavior.

Exact closure proof:

- 182 default OpenAPI operations;
- 231 gated operations;
- delta 49;
- unchanged paths, operation IDs, dependencies, response contracts, and error
  behavior;
- 296 `public_exception_response` calls pinned by a per-module manifest;
- router aggregate coverage 3,604/5,373 statements, 67.0761%, above 45%.

## Store correspondence

The `vnext_stores/postgres/` and `vnext_stores/sqlite/` packages correspond at
the lifecycle, memory access, graph/open-loop, query-predicate,
event/revision, embedding-CAS, column, and primitive seams. Shared pure helpers
live at the package root. `vnext_store.py` and `sqlite_store.py` preserve their
public protocols. SQL-shape tests pin generated SQL text, so relocation cannot
silently rewrite it.

The live legacy store was split into:

- `legacy_store/continuity.py` — 2,699 lines;
- `legacy_store/conversation_memory.py` — 1,797 lines;
- `legacy_store/task_execution.py` — 1,527 lines;
- `legacy_store/governance_integrations.py` — 1,290 lines;
- `legacy_store/providers_knowledge.py` — 1,267 lines.

The facade preserves imports and consumer behavior. No migration, schema, SQL,
ordering, filtering, or transaction change belongs to this move.

## Contract registry

`contracts.py` remains the stable facade over nine `_contracts/` domain
modules: common, continuity, execution, governance, integrations, knowledge,
retrieval, runtime, and tasks. The exact 875-name facade namespace, definition
order, annotations, and metadata are guarded against the base carrier.

## MCP registry

`mcp_tools.py` remains the stable facade over the `mcp/` package. Exact
invariants are:

- 11 core tools;
- 65 legacy tools;
- 76 total tools;
- unchanged legacy gating and agent-key suppression;
- unchanged dispatcher/error contracts;
- unchanged compatibility aliases and public/private facade namespace.

The MCP increment's 28-path freeze aggregate was
`724c81686afac1a4498195a4f38af2e75d345d0761937bcf559fedba17b50763`.
This is an increment receipt, not the final carrier receipt.

## CLI registry

The former `cli.py` is replaced by the `cli/` package. `cli/__init__.py`
preserves `build_parser`, `main`, logger identity, public compatibility names,
annotations, and monkeypatch forwarding. `python -m alicebot_api.cli` retains
the old silent no-op behavior.

Console scripts remain:

- `alice = alicebot_api.cli:main`;
- `alicebot = alicebot_api.cli:main`;
- `alice-memory = alicebot_api.onramp:main`.

Parser topology, help, defaults, handler routes, and command ordering are exact
against the base. The CLI increment's 27-path replacement freeze aggregate was
`e592d607ee265508810de5327f9605f1d6409b8f95de4fb2762ce0c28fee2fcb`.
This is an increment receipt, not the final carrier receipt.

## Gate migrations

- Response hygiene scans `main.py` plus all router modules and pins a per-file
  count whose sum remains 296.
- Coverage enforcement uses the router aggregate rather than an artificially
  small assembly facade.
- Default-surface PostgreSQL smoke invokes pytest with
  `--require-executed-tests`, so an all-skipped selection fails.
- Protected-path controls cover routers, legacy stores, paired vNext stores,
  split contracts, MCP, and CLI modules.
- Packaging and installed-artifact smokes require split-module carriers in both
  wheel and sdist.

## Scope exclusions

No behavior, logic, signature, SQL-text, migration, dependency, performance,
Phase 4, or security work is included. Published v0.10.x/v0.11.x records are
immutable. The pre-existing MCP alias-doc wording identified during review is
deferred rather than rewritten inside this structural carrier.
