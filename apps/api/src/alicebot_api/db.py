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
ENABLED_SESSION_FLAG = "true"
DISABLED_SESSION_FLAG = "false"
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


def _set_connection_context(conn: psycopg.Connection, sql: str, value: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql, (value,))


def _session_flag(enabled: bool) -> str:
    return ENABLED_SESSION_FLAG if enabled else DISABLED_SESSION_FLAG


def set_current_user(conn: psycopg.Connection, user_id: UUID) -> None:
    _set_connection_context(conn, SET_CURRENT_USER_SQL, str(user_id))


def set_current_user_account(conn: psycopg.Connection, user_account_id: UUID) -> None:
    _set_connection_context(conn, SET_CURRENT_USER_ACCOUNT_SQL, str(user_account_id))


def set_hosted_admin_bypass(conn: psycopg.Connection, enabled: bool) -> None:
    _set_connection_context(conn, SET_HOSTED_ADMIN_BYPASS_SQL, _session_flag(enabled))


def set_hosted_service_bypass(conn: psycopg.Connection, enabled: bool) -> None:
    _set_connection_context(conn, SET_HOSTED_SERVICE_BYPASS_SQL, _session_flag(enabled))


@contextmanager
def user_connection(database_url: str, user_id: UUID) -> Iterator[UserConnection]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            set_current_user(conn, user_id)
            yield conn
