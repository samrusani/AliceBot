"""``alice-memory``: the zero-infrastructure SQLite on-ramp for Alice.

Runs the stdio MCP server (the nine core tools) against a local SQLite
file instead of Postgres. No services, no migrations: the schema is
bootstrapped into ``~/.alice/memory.db`` (or ``--data-dir``/``--db``) on
startup and the default local user row is created.

Subcommands:
- ``mcp`` (default): serve MCP over stdio. stdout carries only the MCP
  protocol; human-facing notices go to stderr.
- ``export``: dump memories, sources, open loops, and events as JSONL.
- ``--version``: print the package version.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import IO
from uuid import UUID

from alicebot_api import __version__
from alicebot_api.mcp_server import _DEFAULT_MCP_USER_ID, MCPServer
from alicebot_api.mcp_tools import MCPRuntimeContext
from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import (
    SOURCE_COLUMNS,
    SQLiteVNextStore,
    ensure_sqlite_user,
    sqlite_user_connection,
)
from alicebot_api.vnext_json import json_safe

DEFAULT_DATA_DIR = "~/.alice"
DEFAULT_DB_FILENAME = "memory.db"
DEFAULT_USER_EMAIL = "local@alice"
_KNOWN_COMMANDS = ("mcp", "export")
# A very large LIMIT stands in for "no limit" on store list methods that
# require one; SQLite treats it as unbounded in practice.
_EXPORT_ROW_LIMIT = 1_000_000_000


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
            "Alice's local-first memory on SQLite: serve the nine core MCP tools over "
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
        help="Export memories, sources, open loops, and events as JSONL.",
    )
    _add_database_arguments(export_parser)
    export_parser.add_argument(
        "--out",
        default=None,
        help="Output file path. Defaults to stdout.",
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


def _export_line(record_type: str, row: object) -> str:
    payload = {"record_type": record_type, "record": json_safe(row)}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _write_export(stream: IO[str], *, db_path: Path, user_id: UUID) -> int:
    written = 0
    with sqlite_user_connection(db_path, user_id) as conn:
        store = SQLiteVNextStore(conn, user_id)
        for memory in store.list_memories():
            stream.write(_export_line("memory", memory) + "\n")
            written += 1
        # The store has no list_sources method (the core tools never need
        # one), so export reads the sources table directly with the same
        # user scoping and column order the store uses.
        cursor = conn.execute(
            f"""
            SELECT {", ".join(SOURCE_COLUMNS)}
            FROM sources
            WHERE user_id = ? AND deleted_at IS NULL
            ORDER BY captured_at DESC, id DESC
            """,
            (str(user_id),),
        )
        columns = [description[0] for description in cursor.description]
        for raw in cursor.fetchall():
            row = raw if isinstance(raw, dict) else dict(zip(columns, raw))
            metadata = row.get("metadata_json")
            if isinstance(metadata, str):
                row["metadata_json"] = json.loads(metadata)
            stream.write(_export_line("source", row) + "\n")
            written += 1
        for loop in store.list_open_loops(status=None, limit=_EXPORT_ROW_LIMIT):
            stream.write(_export_line("open_loop", loop) + "\n")
            written += 1
        for event in store.list_events():
            stream.write(_export_line("event", event) + "\n")
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


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(_normalized_argv(raw_argv))
    if args.command == "export":
        return _run_export(args)
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
