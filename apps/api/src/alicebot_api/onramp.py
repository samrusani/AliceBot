"""``alice-memory``: the zero-infrastructure SQLite on-ramp for Alice.

Runs the stdio MCP server (the core tool surface) against a local SQLite
file instead of Postgres. No services, no migrations: the schema is
bootstrapped into ``~/.alice/memory.db`` (or ``--data-dir``/``--db``) on
startup and the default local user row is created.

Subcommands:
- ``mcp`` (default): serve MCP over stdio. stdout carries only the MCP
  protocol; human-facing notices go to stderr.
- ``export``: dump the memory graph as JSONL -- memories, sources, source
  chunks, entities, graph edges, memory revisions, provenance links, open
  loops, and the event log.
- ``import``: load an export JSONL file into a (new or existing) local
  database, preserving ids and timestamps so provenance references and
  the audit trail survive the round trip.
- ``--version``: print the package version.

Export/import round-trip contract ("you own the memory"):
- Every exported record keeps its original ``id`` and timestamps on
  import, so ``export -> import into a fresh file -> export`` produces
  equivalent records (event-log ordering aside).
- Import writes rows via direct INSERT rather than the store's
  ``create_*`` methods: those methods re-stamp ``created_at``/``updated_at``
  and append fresh ``*.created`` mutation events, which would corrupt the
  imported audit trail. Events go through ``SQLiteVNextStore.append_event``,
  which preserves a passed id/occurred_at/integrity_hash verbatim; the
  append-only triggers on ``event_log``/``memory_revisions`` only block
  UPDATE/DELETE, so inserting historical rows is allowed.
- Embedding vectors are NOT exported (they are provider-specific blobs);
  imported memories are searchable via FTS immediately and re-enter
  vector search once re-embedded (configure ``ALICE_EMBEDDINGS_*`` and
  touch or re-commit the memory).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import IO
from uuid import UUID

from alicebot_api import __version__
from alicebot_api.mcp_server import _DEFAULT_MCP_USER_ID, MCPServer
from alicebot_api.mcp_tools import MCPRuntimeContext
from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.sqlite_store import (
    ENTITY_COLUMNS,
    EVENT_LOG_COLUMNS,
    GRAPH_EDGE_COLUMNS,
    MEMORY_COLUMNS,
    OPEN_LOOP_COLUMNS,
    PROVENANCE_COLUMNS,
    REVISION_COLUMNS,
    SOURCE_CHUNK_COLUMNS,
    SOURCE_COLUMNS,
    SQLiteVNextStore,
    _JSON_COLUMNS,
    ensure_sqlite_user,
    sqlite_user_connection,
)
from alicebot_api.vnext_json import json_safe

DEFAULT_DATA_DIR = "~/.alice"
DEFAULT_DB_FILENAME = "memory.db"
DEFAULT_USER_EMAIL = "local@alice"
_KNOWN_COMMANDS = ("mcp", "export", "import")
# A very large LIMIT stands in for "no limit" on store list methods that
# require one; SQLite treats it as unbounded in practice.
_EXPORT_ROW_LIMIT = 1_000_000_000

# The full export/import record surface, in FK-safe insert order: sources
# before their chunks, memories before revisions and open loops, events
# last. record_type values are singular, matching the original export
# format ("memory", "source", "open_loop", "event"); imports of old files
# lacking the newer types work unchanged.
_RECORD_SPECS: dict[str, tuple[str, tuple[str, ...]]] = {
    "source": ("sources", SOURCE_COLUMNS),
    "source_chunk": ("source_chunks", SOURCE_CHUNK_COLUMNS),
    "memory": ("memories", MEMORY_COLUMNS),
    "entity": ("vnext_entities", ENTITY_COLUMNS),
    "graph_edge": ("graph_edges", GRAPH_EDGE_COLUMNS),
    "memory_revision": ("memory_revisions", REVISION_COLUMNS),
    "provenance_link": ("provenance_links", PROVENANCE_COLUMNS),
    "open_loop": ("open_loops", OPEN_LOOP_COLUMNS),
    "event": ("event_log", EVENT_LOG_COLUMNS),
}

_EMBEDDING_NOTE = (
    "imported without embeddings; configure ALICE_EMBEDDINGS_* and touch or "
    "re-commit them to restore vector search (FTS keyword recall works immediately)"
)


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID value: {value}") from exc


def resolve_db_path(*, data_dir: str, db: str | None) -> Path:
    """The database file path: ``--db`` wins, else ``<data-dir>/memory.db``."""
    if db is not None:
        return Path(db).expanduser().resolve()
    return Path(data_dir).expanduser().resolve() / DEFAULT_DB_FILENAME


def sqlite_url_for_path(path: Path) -> str:
    """A ``sqlite:///`` URL for an absolute database file path."""
    return path.resolve().as_uri().replace("file://", "sqlite://", 1)


def bootstrap_database(db_path: Path, *, user_id: UUID, user_email: str) -> None:
    """Create the data dir, schema, and local user row (idempotent)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        bootstrap_sqlite_schema(conn)
        display_name = user_email.split("@", 1)[0].replace(".", " ").title() or None
        ensure_sqlite_user(conn, user_id, user_email, display_name)
        conn.commit()
    finally:
        conn.close()


def _add_database_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        help=f"Directory holding {DEFAULT_DB_FILENAME}. Defaults to {DEFAULT_DATA_DIR}.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Explicit SQLite database file path. Overrides --data-dir.",
    )
    parser.add_argument(
        "--user-id",
        type=_parse_uuid,
        default=UUID(_DEFAULT_MCP_USER_ID),
        help=f"Acting local user UUID. Defaults to {_DEFAULT_MCP_USER_ID}.",
    )
    parser.add_argument(
        "--user-email",
        default=DEFAULT_USER_EMAIL,
        help=f"Email recorded for the local user row. Defaults to {DEFAULT_USER_EMAIL}.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alice-memory",
        description=(
            "Alice's local-first memory on SQLite: serve the core MCP tools over "
            "stdio with zero infrastructure. Running with no subcommand starts 'mcp'."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"alice-memory {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Serve the Alice MCP tools over stdio against a local SQLite file.",
    )
    _add_database_arguments(mcp_parser)

    export_parser = subparsers.add_parser(
        "export",
        help=(
            "Export the memory graph as JSONL: memories, sources, source chunks, "
            "entities, graph edges, memory revisions, provenance links, open "
            "loops, and events."
        ),
    )
    _add_database_arguments(export_parser)
    export_parser.add_argument(
        "--out",
        default=None,
        help="Output file path. Defaults to stdout.",
    )

    import_parser = subparsers.add_parser(
        "import",
        help=(
            "Import an export JSONL file into a local SQLite database, "
            "creating the database if needed. Ids and timestamps are preserved."
        ),
    )
    _add_database_arguments(import_parser)
    import_parser.add_argument(
        "--in",
        dest="in_path",
        required=True,
        help="Input JSONL file produced by 'alice-memory export'.",
    )
    import_parser.add_argument(
        "--mode",
        choices=("skip", "fail"),
        default="skip",
        help=(
            "Collision handling when a record id already exists: 'skip' keeps "
            "the existing row and counts the record as skipped (default); "
            "'fail' aborts the whole import on the first collision. Existing "
            "rows are never overwritten."
        ),
    )
    return parser


def _normalized_argv(argv: list[str]) -> list[str]:
    """Insert the default ``mcp`` subcommand when none is given."""
    if argv and argv[0] in _KNOWN_COMMANDS:
        return argv
    if argv and argv[0] in {"-h", "--help", "--version"}:
        return argv
    return ["mcp", *argv]


def _run_mcp(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(data_dir=args.data_dir, db=args.db)
    bootstrap_database(db_path, user_id=args.user_id, user_email=args.user_email)
    database_url = sqlite_url_for_path(db_path)
    # stdout is the MCP protocol channel; the startup notice goes to stderr.
    print(
        f"alice-memory: serving MCP over stdio (db: {db_path}, user: {args.user_id})",
        file=sys.stderr,
        flush=True,
    )
    context = MCPRuntimeContext(database_url=database_url, user_id=args.user_id)
    server = MCPServer(
        context=context,
        input_stream=sys.stdin.buffer,
        output_stream=sys.stdout.buffer,
    )
    return server.run()


# --- export ---------------------------------------------------------------------


def _export_line(record_type: str, row: object) -> str:
    payload = {"record_type": record_type, "record": json_safe(row)}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _decoded_rows(
    conn: sqlite3.Connection, query: str, params: tuple[object, ...]
) -> Iterator[dict[str, object]]:
    """Dict rows with JSON TEXT columns decoded, matching the store's shape."""
    cursor = conn.execute(query, params)
    columns = [description[0] for description in cursor.description]
    for raw in cursor.fetchall():
        row = dict(raw) if isinstance(raw, dict) else dict(zip(columns, raw))
        for key, value in row.items():
            if key in _JSON_COLUMNS and isinstance(value, str):
                row[key] = json.loads(value)
        yield row


def _export_rows(
    conn: sqlite3.Connection, store: SQLiteVNextStore, user_id: UUID
) -> Iterator[tuple[str, object]]:
    """Yield ``(record_type, row)`` for the whole memory graph.

    Soft-deleted rows stay out of the export, and so do rows that only
    reference soft-deleted rows (chunks of deleted sources, revisions of
    deleted memories, provenance links quoting deleted sources): the
    import target enforces foreign keys, so the exported set must be
    closed under its own references.
    """
    uid = str(user_id)
    # The store has no list_sources method (the core tools never need
    # one), so export reads the sources table directly with the same
    # user scoping and column order the store uses.
    yield from (
        ("source", row)
        for row in _decoded_rows(
            conn,
            f"""
            SELECT {", ".join(SOURCE_COLUMNS)}
            FROM sources
            WHERE user_id = ? AND deleted_at IS NULL
            ORDER BY captured_at DESC, id DESC
            """,
            (uid,),
        )
    )
    yield from (
        ("source_chunk", row)
        for row in _decoded_rows(
            conn,
            f"""
            SELECT {", ".join(f"c.{column}" for column in SOURCE_CHUNK_COLUMNS)}
            FROM source_chunks c
            JOIN sources s ON s.id = c.source_id AND s.user_id = c.user_id
            WHERE c.user_id = ? AND s.deleted_at IS NULL
            ORDER BY c.source_id ASC, c.chunk_index ASC, c.id ASC
            """,
            (uid,),
        )
    )
    yield from (("memory", memory) for memory in store.list_memories())
    yield from (
        ("entity", row)
        for row in _decoded_rows(
            conn,
            f"""
            SELECT {", ".join(ENTITY_COLUMNS)}
            FROM vnext_entities
            WHERE user_id = ? AND deleted_at IS NULL
            ORDER BY created_at ASC, id ASC
            """,
            (uid,),
        )
    )
    # All edges, including closed ones (valid_to set): the temporal
    # history is part of the graph. store.list_edges filters those out.
    yield from (
        ("graph_edge", row)
        for row in _decoded_rows(
            conn,
            f"""
            SELECT {", ".join(GRAPH_EDGE_COLUMNS)}
            FROM graph_edges
            WHERE user_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (uid,),
        )
    )
    yield from (
        ("memory_revision", row)
        for row in _decoded_rows(
            conn,
            f"""
            SELECT {", ".join(f"r.{column}" for column in REVISION_COLUMNS)}
            FROM memory_revisions r
            JOIN memories m ON m.id = r.memory_id AND m.user_id = r.user_id
            WHERE r.user_id = ? AND m.deleted_at IS NULL
            ORDER BY r.memory_id ASC, r.sequence_no ASC, r.id ASC
            """,
            (uid,),
        )
    )
    yield from (
        ("provenance_link", row)
        for row in _decoded_rows(
            conn,
            f"""
            SELECT {", ".join(f"p.{column}" for column in PROVENANCE_COLUMNS)}
            FROM provenance_links p
            WHERE p.user_id = ?
              AND (
                p.source_id IS NULL
                OR EXISTS (
                  SELECT 1 FROM sources s
                  WHERE s.id = p.source_id AND s.user_id = p.user_id
                    AND s.deleted_at IS NULL
                )
              )
              AND (
                p.source_chunk_id IS NULL
                OR EXISTS (
                  SELECT 1
                  FROM source_chunks c
                  JOIN sources s2 ON s2.id = c.source_id AND s2.user_id = c.user_id
                  WHERE c.id = p.source_chunk_id AND c.user_id = p.user_id
                    AND s2.deleted_at IS NULL
                )
              )
            ORDER BY p.created_at ASC, p.id ASC
            """,
            (uid,),
        )
    )
    yield from (
        ("open_loop", loop)
        for loop in store.list_open_loops(status=None, limit=_EXPORT_ROW_LIMIT)
    )
    yield from (("event", event) for event in store.list_events())


def _write_export(stream: IO[str], *, db_path: Path, user_id: UUID) -> int:
    written = 0
    with sqlite_user_connection(db_path, user_id) as conn:
        store = SQLiteVNextStore(conn, user_id)
        for record_type, row in _export_rows(conn, store, user_id):
            stream.write(_export_line(record_type, row) + "\n")
            written += 1
    return written


def _run_export(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(data_dir=args.data_dir, db=args.db)
    if not db_path.exists():
        print(f"error: database file does not exist: {db_path}", file=sys.stderr)
        return 1
    if args.out is not None:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as stream:
            written = _write_export(stream, db_path=db_path, user_id=args.user_id)
        print(f"alice-memory: exported {written} records to {out_path}", file=sys.stderr)
    else:
        written = _write_export(sys.stdout, db_path=db_path, user_id=args.user_id)
    return 0


# --- import ---------------------------------------------------------------------


class _ImportError(Exception):
    """A user-facing import failure; the message names the offending line."""


def _parse_import_file(path: Path) -> dict[str, list[tuple[int, dict[str, object]]]]:
    """Parse an export JSONL file into ``{record_type: [(line_no, record)]}``.

    The whole file is validated before anything touches the database, so
    a malformed line aborts the import with zero rows written. Blank
    lines are tolerated; anything else must be a ``{"record_type": ...,
    "record": {...}}`` object with a known record_type.
    """
    records: dict[str, list[tuple[int, dict[str, object]]]] = {}
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise _ImportError(f"line {line_no}: invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise _ImportError(f"line {line_no}: expected a JSON object, got {type(payload).__name__}")
            record_type = payload.get("record_type")
            record = payload.get("record")
            if not isinstance(record_type, str) or not isinstance(record, dict):
                raise _ImportError(
                    f"line {line_no}: expected {{\"record_type\": str, \"record\": object}}"
                )
            if record_type not in _RECORD_SPECS:
                known = ", ".join(_RECORD_SPECS)
                raise _ImportError(
                    f"line {line_no}: unknown record_type '{record_type}' (known: {known})"
                )
            if not str(record.get("id") or "").strip():
                raise _ImportError(f"line {line_no}: {record_type} record is missing an 'id'")
            records.setdefault(record_type, []).append((line_no, record))
    return records


def _encode_column_value(column: str, value: object) -> object:
    """TEXT-encode JSON columns the way the store writes them; pass the rest."""
    if column in _JSON_COLUMNS and value is not None and not isinstance(value, str):
        return json.dumps(json_safe(value), ensure_ascii=False, separators=(",", ":"))
    return value


def _import_records(
    conn: sqlite3.Connection,
    store: SQLiteVNextStore,
    records: dict[str, list[tuple[int, dict[str, object]]]],
    *,
    mode: str,
) -> dict[str, dict[str, int]]:
    """Insert parsed records in FK-safe order; returns per-type counts.

    Direct INSERT (not the store ``create_*`` methods) so ids and
    timestamps land exactly as exported and no fresh mutation events are
    appended. Events go through ``append_event``, which preserves the
    passed id/occurred_at/integrity_hash. ``user_id`` is rebound to the
    importing user. Raises ``_ImportError`` on the first collision in
    ``fail`` mode and on any constraint violation; the caller's
    transaction rolls back, so a failed import writes nothing.
    """
    counts: dict[str, dict[str, int]] = {}
    for record_type, (table, columns) in _RECORD_SPECS.items():
        for line_no, record in records.get(record_type, []):
            tally = counts.setdefault(record_type, {"imported": 0, "skipped": 0})
            row_id = str(record["id"])
            exists = conn.execute(
                f"SELECT 1 FROM {table} WHERE id = ?", (row_id,)
            ).fetchone()
            if exists is not None:
                if mode == "fail":
                    raise _ImportError(
                        f"line {line_no}: {record_type} id {row_id} already exists; "
                        "aborting (--mode fail). Rerun with --mode skip to keep "
                        "existing rows and import only new records."
                    )
                tally["skipped"] += 1
                continue
            try:
                if record_type == "event":
                    store.append_event(record)
                else:
                    values = tuple(
                        store.user_id
                        if column == "user_id"
                        else _encode_column_value(column, record.get(column))
                        for column in columns
                    )
                    conn.execute(
                        f"""
                        INSERT INTO {table} ({", ".join(columns)})
                        VALUES ({", ".join("?" for _ in columns)})
                        """,
                        values,
                    )
            except (sqlite3.Error, ContinuityStoreInvariantError, KeyError, TypeError, ValueError) as exc:
                raise _ImportError(
                    f"line {line_no}: {record_type} {row_id} could not be imported: {exc}"
                ) from exc
            tally["imported"] += 1
    return counts


def _print_import_summary(
    counts: dict[str, dict[str, int]], *, in_path: Path, db_path: Path
) -> None:
    imported_total = sum(tally["imported"] for tally in counts.values())
    skipped_total = sum(tally["skipped"] for tally in counts.values())
    print(
        f"alice-memory: imported {imported_total} records from {in_path} "
        f"into {db_path} ({skipped_total} skipped)"
    )
    for record_type in _RECORD_SPECS:
        tally = counts.get(record_type)
        if tally is None:
            continue
        print(f"  {record_type}: {tally['imported']} imported, {tally['skipped']} skipped")
    memories_imported = counts.get("memory", {}).get("imported", 0)
    if memories_imported:
        plural = "memory" if memories_imported == 1 else "memories"
        print(f"note: {memories_imported} {plural} {_EMBEDDING_NOTE}")


def _run_import(args: argparse.Namespace) -> int:
    in_path = Path(args.in_path).expanduser()
    if not in_path.exists():
        print(f"error: import file does not exist: {in_path}", file=sys.stderr)
        return 1
    try:
        records = _parse_import_file(in_path)
    except _ImportError as exc:
        print(f"error: {in_path}: {exc}", file=sys.stderr)
        return 1
    db_path = resolve_db_path(data_dir=args.data_dir, db=args.db)
    bootstrap_database(db_path, user_id=args.user_id, user_email=args.user_email)
    try:
        with sqlite_user_connection(db_path, args.user_id) as conn:
            store = SQLiteVNextStore(conn, args.user_id)
            counts = _import_records(conn, store, records, mode=args.mode)
    except _ImportError as exc:
        print(f"error: {in_path}: {exc}", file=sys.stderr)
        print("error: import aborted; no records were written", file=sys.stderr)
        return 1
    _print_import_summary(counts, in_path=in_path, db_path=db_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(_normalized_argv(raw_argv))
    if args.command == "export":
        return _run_export(args)
    if args.command == "import":
        return _run_import(args)
    return _run_mcp(args)


__all__ = [
    "bootstrap_database",
    "build_parser",
    "main",
    "resolve_db_path",
    "sqlite_url_for_path",
]


if __name__ == "__main__":
    raise SystemExit(main())
