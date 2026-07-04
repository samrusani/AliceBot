# Plan: Zero-Infrastructure On-Ramp (`uvx alice-mcp`)

Status: implemented on this branch (`sqlite-onramp`). This page is kept as
the plan of record plus the delta between what was planned and what
shipped. The original goal — a no-Docker, no-Postgres trial experience —
is the single highest-leverage adoption artifact after the retrieval
rebuild.

## What shipped vs. plan

- **Unified dependencies instead of a dependency split.** The planned
  `alice-memory[postgres]` extra was not needed: `numpy` joined the base
  dependencies for the vector fallback, and `psycopg` stays in the base
  install. `sqlite-vec` was not adopted — numpy brute-force cosine covers
  trial-scale corpora, per the plan's own fallback.
- **Store and schema shipped as planned.** `sqlite_schema.py` (dedicated
  SQLite-dialect bootstrap, not Alembic) and `sqlite_store.py`
  (`SQLiteVNextStore`: FTS5 with a porter tokenizer and
  stopword-filtered MATCH translation, trigger-synced external-content
  index, numpy cosine vector search, per-statement `user_id` scoping in
  place of RLS).
- **Four legacy-backed tools serve vNext-native SQLite implementations**
  rather than porting the legacy continuity surfaces; the other five core
  tools run their existing vNext paths against the SQLite store.
- **Export command.** `alice-memory export` covers the "no automatic
  migration, provide export/import instead" non-goal.
- **Evals run against both backends.** `ALICEBOT_EVAL_DATABASE_URL`
  accepts `sqlite:///<path>` / `sqlite:///:memory:`; the
  `retrieval_quality` suite seeds and queries through `SQLiteVNextStore`
  inside a rolled-back transaction and the report labels the backend
  (`metrics.backend`), so side-by-side numbers are two runs with two URLs.
  This also made the live eval path CI-runnable with no services.

Acceptance status:

- `uvx alice-memory mcp` on a clean machine — **pending PyPI publish**;
  works from a repo checkout today (`pip install -e .` then
  `alice-memory mcp --data-dir ~/.alice`).
- Nine core tools against the SQLite backend — **shipped** (unit and
  integration coverage on this branch).
- Retrieval evals on both backends with side-by-side numbers — **shipped**
  (see `eval/README.md`, "Comparing backends").

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
