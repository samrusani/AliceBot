# Upgrade v0.12.0 To Current

This is the supported evidence path from published Alice v0.12.0 to the
current source candidate. Rehearse it on a restored copy before touching the
live store.

The immutable baseline is tag `v0.12.0`, commit
`692c28ae60072b1eac4a437676b3ecf68e8bc026`. The repository drill verifies that
exact mapping and uses `git archive`; it never switches or mutates the current
checkout.

## Contract

- Back up and restore-test the old store first.
- Migrations are forward-only during the cutover; rollback means returning to
  the untouched pre-upgrade store and old Alice artifact.
- Run migrations with the admin URL. Run Alice with the role-separated
  application URL.
- Determine the current Alembic head from the deployed artifact rather than
  copying a stale revision from this page.
- SQLite bootstrap is additive and idempotent. It must preserve data, FTS
  recall, and signed vectors while adding exactly one nonempty
  `embedding_stamp` row.

## Automated rehearsal

SQLite-only rehearsal needs no PostgreSQL tools:

```bash
./.venv/bin/python scripts/run_phase5_ops_evidence.py \
  --backend sqlite \
  --output artifacts/phase5/sqlite-upgrade-evidence.json
```

The full role-separated rehearsal additionally needs `pg_dump`, `pg_restore`,
`DATABASE_ADMIN_URL`, `DATABASE_URL`, and a reachable disposable PostgreSQL 16
server with pgvector 0.8 or newer:

```bash
./.venv/bin/python scripts/run_phase5_ops_evidence.py --backend all \
  --output artifacts/phase5/ops-evidence.json
```

The script extracts v0.12.0, runs the v0.12.0 code and migration head, seeds a
known memory plus a signed vector, upgrades in place with the current code, and
verifies integrity, counts, FTS recall, signature compatibility, and new
schema. Raw stores are private temporary data and are removed; the JSON report
contains no paths, DSNs, credentials, or memory content.

For an uncommitted release carrier, use the receipt's
`carrier_snapshot_sha256` as its content identity. `source_head_commit` and
`source_head_tree` identify the immutable base only; `carrier_state: dirty`
makes explicit that the carrier includes changes not present in that commit.
The digest covers tracked modifications/deletions and non-ignored untracked
files while safely hashing symlink targets instead of following them.

## PostgreSQL migration proof

Published v0.12.0 ends at `20260716_0092`. On this Phase 5 carrier, the
following migrations are specifically exercised:

- `20260721_0093`: duplicate non-null `(artifact_id, reviewer_id)` ratings are
  reduced to the newest `created_at DESC, id DESC` survivor, then
  `artifact_quality_ratings_artifact_reviewer_key` enforces uniqueness. The
  drill seeds old/new duplicates, asserts the newer row survives, and proves a
  duplicate insert fails.
- `20260721_0094`: `browser_clip_capabilities` exists after migration. The
  drill also requires the database `alembic_version` to equal the migration
  graph's dynamically discovered single head, so a later additive head cannot
  silently be skipped.

For a manual rehearsal:

```bash
export DATABASE_ADMIN_URL='from-your-secret-manager'
python -m alembic -c apps/api/alembic.ini current
python -m alembic -c apps/api/alembic.ini heads
python -m alembic -c apps/api/alembic.ini upgrade head
```

Do not paste a credentialed URL into a transcript or command line. The examples
show an environment placeholder; inject the real value through the deployment
secret mechanism.

## SQLite proof

Stop all writers, make a physical backup, then start the new `alice-memory`
runtime against a restored copy. Bootstrap installs current tables and indexes.
Verify:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SELECT id, length(token) FROM embedding_stamp;
SELECT count(*) FROM memories;
```

The stamp query must return exactly one row with `id = 1` and a nonempty token.
Opening/bootstraping the same unchanged store again must preserve that token.
Run a representative recall and confirm a previously signed vector remains
present and content-compatible.

Portable JSONL is a separate contract: it omits embedding vectors, so a JSONL
restore must run `alice-memory reindex-embeddings` after the intended provider
is configured. Do not use portable round-trip results as proof that physical
vector state survived.

## Cutover and rollback

1. Record old/new source commits and dynamic migration heads.
2. Quiesce writers and take a final backup with a SHA-256 digest.
3. Upgrade the already verified restore candidate.
4. Require integrity, counts, recall, embedding-signature, application-role,
   RLS, `/healthz`, doctor, and scheduler checks to pass.
5. Cut over once. Keep the old store read-only.
6. If any check fails, restore the old artifact and point it at the untouched
   old store. Do not downgrade the partially migrated database in place.
