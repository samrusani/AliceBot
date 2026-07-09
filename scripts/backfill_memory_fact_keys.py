#!/usr/bin/env python3
"""One-shot backfill: derive ``memories.fact_keys`` for pre-existing rows.

New memories get fact keys at commit time (``attach_memory_fact_keys`` in
``alicebot_api.vnext_memory_commit``); rows written before migration
``20260707_0082`` / the sqlite_schema fact_keys column shipped have
``fact_keys IS NULL`` and stay invisible to category-phrased lexical
queries until this pass runs. Safe to re-run: processed rows (including
"derived, nothing to add" rows, stored as ``''``) are skipped.

Usage:

    python scripts/backfill_memory_fact_keys.py \
        --database-url sqlite:////absolute/path/to/alice.db \
        --user-id 3f2a...          # any user's UUID in that database

    python scripts/backfill_memory_fact_keys.py \
        --database-url postgresql://alicebot_app:...@localhost:5432/alicebot \
        --user-id 3f2a...

The optional model tier engages only when ``ALICE_FACT_KEYS_BASE_URL``
and ``ALICE_FACT_KEYS_MODEL`` are set (``--deterministic-only`` forces it
off); otherwise the backfill is fully offline and deterministic.
Multi-user databases: run once per user id (rows are user-scoped).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
_VENV_REEXEC_ENV = "ALICEBOT_FACT_KEYS_BACKFILL_REEXEC"


def _maybe_reexec_into_repo_venv() -> None:
    if os.getenv(_VENV_REEXEC_ENV) == "1":
        return

    venv_python = (REPO_ROOT / ".venv" / "bin" / "python").resolve()
    if not venv_python.exists():
        return

    current_python = Path(sys.executable).expanduser().resolve()
    if current_python == venv_python:
        return

    os.environ[_VENV_REEXEC_ENV] = "1"
    os.execv(
        str(venv_python),
        [
            str(venv_python),
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ],
    )


_maybe_reexec_into_repo_venv()

API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from alicebot_api.vnext_fact_keys import backfill_memory_fact_keys  # noqa: E402


SQLITE_URL_PREFIX = "sqlite:///"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("ALICEBOT_DATABASE_URL") or os.environ.get("DATABASE_URL") or "",
        help="sqlite:///<path> or postgresql:// URL (default: $ALICEBOT_DATABASE_URL, then $DATABASE_URL)",
    )
    parser.add_argument("--user-id", required=True, help="user UUID whose memories to backfill")
    parser.add_argument("--batch-size", type=int, default=200, help="rows per page (default: 200)")
    parser.add_argument(
        "--deterministic-only",
        action="store_true",
        help="ignore ALICE_FACT_KEYS_* env and run tier (a) only",
    )
    return parser.parse_args(argv)


def _sqlite_path(database_url: str) -> str:
    # Accept sqlite:///relative, sqlite:////absolute, and sqlite:///:memory:.
    remainder = database_url[len(SQLITE_URL_PREFIX) :]
    if remainder == "":
        raise ValueError(f"missing database path in sqlite URL: {database_url}")
    return remainder


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    database_url = args.database_url.strip()
    if database_url == "":
        print("error: --database-url (or $ALICEBOT_DATABASE_URL / $DATABASE_URL) is required", file=sys.stderr)
        return 2
    use_env_provider = not args.deterministic_only

    if database_url.startswith("sqlite:"):
        if not database_url.startswith(SQLITE_URL_PREFIX):
            print(f"error: unsupported sqlite URL (expected sqlite:///<path>): {database_url}", file=sys.stderr)
            return 2
        from alicebot_api.sqlite_store import SQLiteVNextStore, sqlite_user_connection

        with sqlite_user_connection(_sqlite_path(database_url), args.user_id) as conn:
            store = SQLiteVNextStore(conn, args.user_id)
            summary = backfill_memory_fact_keys(
                store, batch_size=args.batch_size, use_env_provider=use_env_provider
            )
    else:
        from alicebot_api.db import user_connection
        from alicebot_api.vnext_store import PostgresVNextStore

        with user_connection(database_url, args.user_id) as conn:
            store = PostgresVNextStore(conn)
            summary = backfill_memory_fact_keys(
                store, batch_size=args.batch_size, use_env_provider=use_env_provider
            )

    print(json.dumps({"user_id": args.user_id, **summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
