# Alice v0.12.0 Phase 3 Fix Matrix

**Structure only. Zero behavior change.**

| Increment | Mechanical move | Stable boundary | Fail-on-old / parity proof | Review |
|---|---|---|---|---|
| HTTP assembly | Split 296 handlers from `main.py` into domain routers and retain thin assembly/middleware. | `alicebot_api.main:app`, paths, operation IDs, dependencies, errors, and conditional mounting. | Exact 182 default / 231 gated / 49 delta OpenAPI closure; router split sentinels; import-path tests. | GO; no remaining P0-P3. |
| Response hygiene | Scan `main.py` plus `routers/`; replace the monolith-only count with a per-module manifest. | Same public error mapping and exactly 296 helper calls. | AST gate fails on unscanned or delayed exception-derived response patterns and count drift. | GO. |
| Coverage | Retarget the old `main.py` floor to the moved router surface. | No silent enforcement drop onto a 1,140-line facade. | Router aggregate 3,604/5,373 = 67.0761%, floor 45%. | GO. |
| vNext stores | Extract lifecycle, memory access, graph/open-loop, query, events/revisions, embedding CAS, columns, and primitives. | `vnext_store.py` facade, protocols, SQL text, ordering, and transactions. | SQL-shape and exact seam tests; PostgreSQL/SQLite paired layout. | GO. |
| SQLite parity | Land every vNext seam in the corresponding SQLite package in the same increment. | Same supported store semantics; backend-specific capability boundary unchanged. | Paired-module inventory plus complete SQLite unit/eval smokes. | GO. |
| Legacy store | Split only surviving `store.py` consumers into five domain carriers behind the facade. | Existing imports, methods, signatures, and behavior. | Definition/consumer and per-domain split sentinels. | GO. |
| Contracts C1-C9 | Move pure data contracts into nine `_contracts/` modules. | `contracts.py` facade, 875 names, order, annotations, and metadata. | One fail-on-old split test per domain plus exact facade manifest. | GO. |
| MCP | Move registry/dispatch and domain tools into `mcp/` behind `mcp_tools.py`. | 11 core / 65 legacy / 76 total, flags, agent-key suppression, aliases, errors, namespace. | Package-split, registry, error-contract, installed-artifact, and carrier-identity tests. | GO; no remaining P0-P3. |
| CLI | Move parser/dispatch and commands into `cli/` behind `cli/__init__.py`. | Parser topology, help, handlers, public namespace, annotations, monkeypatch compatibility, entrypoints, no-op module execution. | Exact base manifests, ForwardRef-module guard, package carrier/archive/install smokes. | GO; no remaining P0-P3. |
| Flag-off smoke | Require nonzero selected test execution. | Same runtime smoke; stronger CI truth only. | `--require-executed-tests` plus workflow/control tests fails on all-skipped old shape. | GO. |
| Protected paths | Extend guardrails to every moved structural carrier. | Existing upgrade-overview policy applies after relocation. | Categorization tests cover routers, legacy store, paired vNext stores, split contracts, MCP, and CLI. | Builder-verified. |
| Docs/control | Reconcile active truth, add pending v0.12.0 notes and handoff, preserve v0.11.1 publication baseline. | Governed versions stay 0.11.1; no immutable record edits or publication claim. | Control-doc truth plus Phase 3 handoff fail-on-old sentinel and exact CURRENT_STATE mirror. | Builder-verified; independent verdict owned by `REVIEW_REPORT.md`. |

## Structural acceptance totals

- Base oversized carriers: 12,856 / 9,202 / 8,174 / 7,431 / 7,019 /
  5,915 / 5,212 lines for `main.py`, legacy `store.py`, `vnext_store.py`,
  `mcp_tools.py`, `cli.py`, `contracts.py`, and `sqlite_store.py`.
- Final facades: 1,140 / 1,692 / 3,595 / 564 / 80 / 1,964 / 1,563
  lines respectively.
- Final largest production Python file: 3,803 lines.
- Production files over 4,000 lines: zero.

## Behavior-change rejection boundary

The split is accepted only because exact manifests and behavioral matrices
preserve routes, registries, signatures, annotations, namespace order, handler
routing, store protocols, SQL text, packaging, and entrypoints. Any discovered
logic or documentation-behavior defect was deferred instead of fixed mid-move.

The pre-existing `docs/alpha/mcp-tools.md` alias wording is one such deferred
item. External exact-SHA semantic and CodeQL readback are release gates that
cannot truthfully be completed on an uncommitted tree.

## Release boundary

The final `BUILD_REPORT.md` is authoritative for local matrix and receipt
evidence. Only the reviewer-authored `REVIEW_REPORT.md` can approve the final
carrier for release-engineer verification. Neither report predicts a future
release SHA or authorizes publication.
