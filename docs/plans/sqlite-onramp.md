# Plan: Zero-Infrastructure On-Ramp (`uvx alice-mcp`)

Status: planned, not implemented. This documents the scoped path to a
no-Docker, no-Postgres trial experience — the single highest-leverage
adoption artifact after the retrieval rebuild.

## Goal

An agent developer should get from nothing to a working Alice MCP server in
under two minutes, with no services to run:

```bash
uvx alice-memory mcp --data-dir ~/.alice
```

That command starts the MCP server against a local SQLite file, exposes the
nine core tools, and requires zero configuration. Postgres remains the
recommended path for real deployments; SQLite is the trial and
single-agent-laptop path.

## Why not just port the store?

`vnext_store.py` is raw Postgres SQL (~3,000 lines) and depends on:

- `pgvector` for vector KNN (`<=>` operator, HNSW index)
- `tsvector`/`websearch_to_tsquery` full-text search
- `jsonb` operators in several read paths

A full port would fork every query. The scoped approach below avoids that.

## Scoped approach

1. **Store protocol extraction (prerequisite, ~small).** The vnext
   repositories already define protocols (`vnext_repositories.py`). Tighten
   the retrieval-facing surface to the minimal set the nine core tools use:
   memory CRUD, source CRUD, FTS search, vector search, open loops,
   review actions, provenance lookups, event append.
2. **SQLite backend implementing only that surface (~medium).**
   - Full-text: SQLite FTS5 (`MATCH` + `bm25()`), contentless table synced
     by trigger.
   - Vectors: `sqlite-vec` extension when available; NumPy brute-force
     cosine fallback below ~50k memories (measured: acceptable latency for
     trial corpora).
   - JSON: SQLite `json_extract` covers the jsonb usage in the scoped
     surface.
3. **Single-file runtime profile.** `alice-memory mcp` entrypoint: creates
   the SQLite file, runs SQLite-dialect schema bootstrap (a dedicated
   schema module, not Alembic), starts the MCP server with the nine core
   tools. Review actions run through `alice_memory_review` rather than the
   web console, so Node/pnpm are not required on this path.
4. **Packaging.** Publish `alice-memory` to PyPI (name reserved in
   pyproject; `alice-core` on PyPI is unrelated software). Optional extra
   `alice-memory[postgres]` pulls psycopg; base install stays light for
   `uvx`.

## Explicit non-goals

- No SQLite support for the legacy continuity surfaces, importers, hosted
  layer, scheduler daemon, or web console.
- No automatic migration between SQLite and Postgres in v1 of this path
  (provide an export/import command instead).

## Acceptance

- `uvx alice-memory mcp` works on a clean machine with only Python 3.12+.
- The nine core tools pass an integration smoke against the SQLite backend.
- Retrieval evals (recall@k on the seeded corpus) run against both backends
  and report both numbers side by side.
