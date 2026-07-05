"""Backend plumbing for the scale benchmark.

- SQLite: a real file store (not ``:memory:``) opened through the product's
  ``sqlite_user_connection`` bootstrap, so commits hit the disk with the
  same journal/fsync behavior the on-ramp sees.
- Postgres: a disposable ``pgvector/pgvector:pg16`` container on a
  non-default port with the same role separation as
  ``docker-compose.yml`` + ``infra/postgres/init/001_roles.sh``
  (``alicebot_admin`` migrates via the alembic head, ``alicebot_app``
  runs the benchmark under RLS with ``app.current_user_id`` set).

The harness owns commits: measured write operations call
``session.commit()`` inside the timed region so per-operation durability
cost is included, mirroring the CLI/MCP pattern of one transaction per
command invocation.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import Callable, Iterator
from uuid import UUID

BENCH_USER_ID = UUID("33333333-3333-4333-8333-333333333333")
BENCH_USER_EMAIL = "scale-bench@alice.local"
BENCH_USER_NAME = "Scale Benchmark"

PG_CONTAINER_NAME = "alicebot-scale-bench-pg"
PG_IMAGE = "pgvector/pgvector:pg16"
PG_DEFAULT_PORT = 55433
PG_ADMIN_USER = "alicebot_admin"
PG_ADMIN_PASSWORD = "alicebot_admin"
PG_APP_USER = "alicebot_app"
PG_APP_PASSWORD = "alicebot_app"
PG_READY_TIMEOUT_SECONDS = 120


@dataclass(slots=True)
class BackendSession:
    """A live store plus explicit commit/rollback hooks the harness can time."""

    backend: str
    store: object
    commit: Callable[[], None]
    rollback: Callable[[], None]
    raw_execute: Callable[[str], object] = lambda _sql: None


@contextmanager
def sqlite_session(db_path: str | Path) -> Iterator[BackendSession]:
    from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user, sqlite_user_connection

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite_user_connection(path, BENCH_USER_ID) as conn:
        ensure_sqlite_user(conn, BENCH_USER_ID, BENCH_USER_EMAIL, BENCH_USER_NAME)
        conn.commit()
        store = SQLiteVNextStore(conn, BENCH_USER_ID)
        yield BackendSession(backend="sqlite", store=store, commit=conn.commit, rollback=conn.rollback, raw_execute=conn.execute)


def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True, **kwargs)  # type: ignore[arg-type]


class PostgresContainer:
    """Lifecycle of the disposable benchmark Postgres container."""

    def __init__(self, *, port: int = PG_DEFAULT_PORT) -> None:
        self.port = port

    @property
    def admin_root_url(self) -> str:
        return f"postgresql://{PG_ADMIN_USER}:{PG_ADMIN_PASSWORD}@127.0.0.1:{self.port}/alicebot"

    def admin_url(self, database: str) -> str:
        return f"postgresql://{PG_ADMIN_USER}:{PG_ADMIN_PASSWORD}@127.0.0.1:{self.port}/{database}"

    def app_url(self, database: str) -> str:
        return f"postgresql://{PG_APP_USER}:{PG_APP_PASSWORD}@127.0.0.1:{self.port}/{database}"

    def start(self) -> None:
        subprocess.run(
            ["docker", "rm", "-f", "-v", PG_CONTAINER_NAME],
            capture_output=True, text=True, check=False,
        )
        _run(
            [
                "docker", "run", "-d",
                "--name", PG_CONTAINER_NAME,
                "-e", f"POSTGRES_USER={PG_ADMIN_USER}",
                "-e", f"POSTGRES_PASSWORD={PG_ADMIN_PASSWORD}",
                "-e", "POSTGRES_DB=alicebot",
                "-p", f"127.0.0.1:{self.port}:5432",
                PG_IMAGE,
            ]
        )
        self._wait_ready()
        self._ensure_app_role()

    def stop(self) -> None:
        subprocess.run(
            ["docker", "rm", "-f", "-v", PG_CONTAINER_NAME],
            capture_output=True, text=True, check=False,
        )

    def _wait_ready(self) -> None:
        import psycopg

        deadline = time.monotonic() + PG_READY_TIMEOUT_SECONDS
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with psycopg.connect(self.admin_root_url, connect_timeout=3) as conn:
                    conn.execute("SELECT 1")
                return
            except psycopg.Error as exc:  # container still starting
                last_error = exc
                time.sleep(1.0)
        raise RuntimeError(f"Postgres container did not become ready: {last_error}")

    def _ensure_app_role(self) -> None:
        """Mirror infra/postgres/init/001_roles.sh role separation."""
        import psycopg

        with psycopg.connect(self.admin_root_url, autocommit=True) as conn:
            row = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (PG_APP_USER,)).fetchone()
            if row is None:
                conn.execute(
                    f"CREATE ROLE {PG_APP_USER} LOGIN PASSWORD '{PG_APP_PASSWORD}' "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
                )
            conn.execute(f"GRANT CONNECT ON DATABASE alicebot TO {PG_APP_USER}")

    def create_migrated_database(self, database: str) -> None:
        """Fresh database migrated to alembic head with DATABASE_ADMIN_URL role."""
        from alembic import command
        import psycopg
        from psycopg import sql

        from alicebot_api.migrations import make_alembic_config

        with psycopg.connect(self.admin_root_url, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(database))
            )
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
            conn.execute(
                sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO alicebot_app").format(
                    sql.Identifier(database)
                )
            )
        admin_url = self.admin_url(database)
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        command.upgrade(make_alembic_config(admin_url), "head")
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO users (id, email, display_name) VALUES (%s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (str(BENCH_USER_ID), BENCH_USER_EMAIL, BENCH_USER_NAME),
            )


@contextmanager
def postgres_session(container: PostgresContainer, database: str) -> Iterator[BackendSession]:
    """App-role connection with a session-scoped RLS user context.

    ``alicebot_api.db.user_connection`` sets ``app.current_user_id``
    transaction-locally and wraps the whole CLI command in one transaction.
    The benchmark needs to COMMIT inside the timed region of write
    operations, so it sets the GUC session-wide (``set_config(..., false)``)
    instead; ``app.current_user_id()`` reads the same setting either way.
    """
    import psycopg
    from psycopg.rows import dict_row

    from alicebot_api.vnext_store import PostgresVNextStore

    with psycopg.connect(container.app_url(database), row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.current_user_id', %s, false)", (str(BENCH_USER_ID),))
        conn.commit()
        store = PostgresVNextStore(conn)
        yield BackendSession(backend="postgres", store=store, commit=conn.commit, rollback=conn.rollback, raw_execute=lambda sql: conn.execute(sql))
        conn.commit()


__all__ = [
    "BENCH_USER_EMAIL",
    "BENCH_USER_ID",
    "BackendSession",
    "PG_DEFAULT_PORT",
    "PG_IMAGE",
    "PostgresContainer",
    "postgres_session",
    "sqlite_session",
]
