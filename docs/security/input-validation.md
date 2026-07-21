# Input Validation And Injection Evidence

## HTTP And Structured Data

vNext request bodies inherit the shared Pydantic model configured with
`extra="forbid"`; typed fields, literals, UUIDs, length bounds, and route-specific
validators reject malformed values before persistence. New raw transports must
size-bound bytes before decoding, reject non-object JSON and unknown fields, and
then validate through the same model contract.

Metadata is treated as JSON data. Store calls serialize values through database
drivers rather than interpolating them into SQL expressions. Any operation that
selects a JSON field or ordering mode must choose from a code-owned allowlist.

## SQL Construction

The Postgres and SQLite stores bind caller values as parameters. The limited SQL
fragments assembled dynamically are code-owned column lists, fixed predicates,
or allowlisted sort/query modes; callers do not supply identifiers or SQL
syntax. SQL-shape tests pin security-sensitive predicates and generated text so
a refactor cannot silently drop user, project, lifecycle, or signature filters.

The Stage A source sweep found no confirmed SQL or JSON-path injection in the
reviewed current store paths. That is a bounded review result, not a claim that
future dynamic SQL is safe by construction.

## Full-Text Search

- PostgreSQL passes the strict query to `websearch_to_tsquery` as a bound value.
  Its match-any fallback constructs an OR expression from normalized literal
  lexemes and still binds the resulting query value.
- SQLite FTS5 query builders quote normalized tokens rather than accepting raw
  FTS syntax. Unit tests exercise quotes, operators, punctuation, and FTS5
  metacharacters for memory and source-chunk search.

SQLite adversarial FTS coverage is currently broader. Stage B should include
hostile PostgreSQL strings across strict, match-any, source, and scoped paths,
including empty/stop-word-only inputs and Unicode boundary cases.

## File And Import Paths

The SQLite portable export/import path has extensive alias, inode, symlink,
sidecar-name, immutable-snapshot, integrity-digest, unknown-schema, and atomic
publication tests. Those controls do **not** close a separate gap in the
content-directory importers:

- Markdown recursively discovers `*.md` files;
- ChatGPT recursively discovers `*.json` files;
- OpenClaw reads named JSON files or direct-directory JSON fallbacks.

Those importers can currently include a symlinked member outside the selected
root, and the archive step and parser can read the source at different times.
The recorded archive checksum can therefore describe different bytes than the
parsed memory, or a local attacker can substitute content between reads. This
finding is deferred from the Phase 5.1 carrier.

Until remediation, import only from a private staging directory owned by the
Alice operator, reject/remove symlinks before import, and ensure no other
process can mutate the directory during the run. A later fix should open files
once without following symlinks, enforce root containment on the opened object,
and feed the same immutable bytes to both archiving and parsing.

## Focused Evidence

```bash
./.venv/bin/pytest -q \
  tests/unit/test_importers.py \
  tests/unit/test_sqlite_onramp.py \
  tests/unit/test_vnext_store.py \
  tests/unit/test_sqlite_store.py \
  tests/integration/test_source_content_retrieval_postgres.py \
  tests/integration/test_vnext_fts_fallback_postgres.py
```

Run role-separated PostgreSQL tests against the supported database/pgvector
version. Do not treat a skipped integration suite as proof.
