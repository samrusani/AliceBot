from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

PING_DATABASE_SQL = "SELECT 1"
SET_CURRENT_USER_SQL = "SELECT set_config('app.current_user_id', %s, true)"
ConnectionRow = dict[str, object]
UserConnection = psycopg.Connection[ConnectionRow]


def ping_database(database_url: str, timeout_seconds: int) -> bool:
    try:
        with psycopg.connect(database_url, connect_timeout=timeout_seconds) as conn:
            with conn.cursor() as cur:
                cur.execute(PING_DATABASE_SQL)
                cur.fetchone()
        return True
    except psycopg.Error:
        return False


def set_current_user(conn: psycopg.Connection, user_id: UUID) -> None:
    with conn.cursor() as cur:
        cur.execute(SET_CURRENT_USER_SQL, (str(user_id),))


@contextmanager
def user_connection(database_url: str, user_id: UUID) -> Iterator[UserConnection]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            set_current_user(conn, user_id)
            yield conn
