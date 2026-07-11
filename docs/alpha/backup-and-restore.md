# Backup And Restore

Back up Alice before upgrading, changing embedding providers, or performing
bulk lifecycle work. Test a restore before treating any file as a backup.

## SQLite on-ramp

Use the packaged export command with `--out`. It verifies and copies a stable
read-only replica of the source database and active WAL into a private
temporary directory, then takes a consistent SQLite online-backup snapshot
from that replica. Any compatible bootstrap upgrade applies only to the
private snapshot. Export does not bootstrap, upgrade, chmod, or open the live
source through SQLite, and it does not change source schema, logical content,
file bytes (including the volatile `-shm` file), or permissions. Ordinary
filesystem reads may still update access-time metadata. A source that stays
busy through the bounded snapshot retries fails clearly so you can quiesce
writers and retry. An unknown
`--user-id`, unsupported newer schema, or corrupt source fails before any
JSONL is published.

The versioned JSONL is written through a `0600` sibling temporary file,
`fsync`, and atomic replacement:

```bash
alice-memory export \
  --data-dir ~/.alice \
  --out ~/alice-backups/alice-$(date +%Y%m%d-%H%M%S).jsonl
```

The JSONL contains sensitive plaintext. `0600` limits local file access but
does not encrypt the backup; use encrypted storage and protect off-machine
copies according to your threat model.

Always use `--out` for a durable backup. Shell-created files inherit the
shell's permissions and are not atomically replaced. More importantly,
**never redirect stdout to the SQLite database or its `-wal`, `-shm`, or
`-journal` sidecars**: the shell truncates its destination before
`alice-memory` starts, so no in-process alias check can prevent data loss.

A v2 backup contains a schema version and fingerprint, per-record counts, and
a SHA-256 footer over the canonical portable data records. That digest is
stable across export, fresh import, and re-export when the records are
unchanged; volatile manifest fields such as `exported_at` are not part of the
digest. Import validates the complete envelope before staging a restore.
Restore into a new path first:

```bash
alice-memory import \
  --db ~/alice-restore-test/memory.db \
  --in ~/alice-backups/alice-20260711-120000.jsonl

alice-memory mcp --db ~/alice-restore-test/memory.db
```

Export output and import input paths are rejected if they lexically name, or
resolve/link to, the database itself or its `-wal`, `-shm`, or `-journal`
sidecars.

Every restore is built and schema-upgraded in a private staged database.
New-target restore uses atomic no-clobber publication and will not replace a
target that appears concurrently. Existing-target restore publishes staged
schema and data together through SQLite's backup write transaction; an error
leaves the original target's data and schema intact. Quiesce writers while
restoring an existing target, because restore semantics intentionally publish
the staged snapshot as the new database state. `--mode skip` skips only
field-for-field identical IDs; different content with the same ID aborts
instead of merging incompatible snapshots. `--mode fail` aborts on every
collision. Exit `0` means restore and post-commit reporting/hardening
completed; exit `1` means publication did not occur. Exit `2` means the
publication committed but a post-commit condition or reporting step failed.
The records are present: inspect stderr and the target path, and do not
blindly retry.

Portable backups include active sources and chunks, memories and fact keys,
revisions, provenance, entities, graph edges, entity relationship events,
open loops, and the event log. They intentionally omit users, agent API keys,
embedding vectors, and soft-deleted content. References from retained rows to
omitted soft-deleted parents are nulled where nullable; graph edges whose
known endpoints were omitted are excluded. Historical event ids, timestamps,
and integrity hashes are inserted verbatim. The restored rows are rebound to
the importing local user. Configure the intended embedding endpoint and run:

```bash
alice-memory reindex-embeddings --db /path/to/restored-memory.db
```

For PostgreSQL upgrades or model changes, use
`alicebot vnext memories backfill-embeddings`; it rebuilds missing, unsigned,
and provider/model-incompatible vectors.

Legacy headerless exports remain importable but cannot prove that a
syntactically complete file was not truncated.

## PostgreSQL

The SQLite JSONL command is not a PostgreSQL disaster-recovery tool. Use the
PostgreSQL utilities against the admin connection and protect the resulting
file as sensitive plaintext:

```bash
pg_dump --format=custom --file=alice.dump "$DATABASE_ADMIN_URL"
pg_restore --list alice.dump
```

Restore into a new database, apply the same Alice release's migrations, then
run integration and application smoke tests before cutover. Database roles,
extensions, and grants are deployment concerns; record them alongside the
backup without committing credentials. For a production deployment, add
scheduled backups, retention, off-machine encrypted copies, and periodic
restore drills appropriate to the operator's recovery objectives.

## Upgrade checkpoint

Before `make migrate` on an existing installation:

1. record the running Alice version and source SHA;
2. create and hash a backup;
3. restore it into a disposable target and read representative memories;
4. run the upgrade on that restored copy;
5. verify capture, review/correction, recall, and export before upgrading the
   live database.
