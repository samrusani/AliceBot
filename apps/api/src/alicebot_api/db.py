from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

PING_DATABASE_SQL = "SELECT 1"
SET_CURRENT_USER_SQL = "SELECT set_config('app.current_user_id', %s, true)"
SET_CURRENT_USER_ACCOUNT_SQL = "SELECT set_config('app.current_user_account_id', %s, true)"
SET_HOSTED_ADMIN_BYPASS_SQL = "SELECT set_config('app.hosted_admin_bypass', %s, true)"
SET_HOSTED_SERVICE_BYPASS_SQL = "SELECT set_config('app.hosted_service_bypass', %s, true)"
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


def set_current_user_account(conn: psycopg.Connection, user_account_id: UUID) -> None:
    with conn.cursor() as cur:
        cur.execute(SET_CURRENT_USER_ACCOUNT_SQL, (str(user_account_id),))


def set_hosted_admin_bypass(conn: psycopg.Connection, enabled: bool) -> None:
    with conn.cursor() as cur:
        cur.execute(SET_HOSTED_ADMIN_BYPASS_SQL, ("true" if enabled else "false",))


def set_hosted_service_bypass(conn: psycopg.Connection, enabled: bool) -> None:
    with conn.cursor() as cur:
        cur.execute(SET_HOSTED_SERVICE_BYPASS_SQL, ("true" if enabled else "false",))


@contextmanager
def user_connection(database_url: str, user_id: UUID) -> Iterator[UserConnection]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            set_current_user(conn, user_id)
            yield conn
