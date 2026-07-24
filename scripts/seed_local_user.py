#!/usr/bin/env python3
"""Seed the configured local Alice user through the migration role."""

from __future__ import annotations

from collections.abc import Mapping
import os
from uuid import UUID

import psycopg

from alicebot_api.db import set_current_user


SEED_LOCAL_USER_SQL = """
    INSERT INTO users (id, email, display_name)
    VALUES (%s, %s, %s)
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email,
        display_name = EXCLUDED.display_name
    """


def seed_local_user(*, database_admin_url: str, user_id: UUID) -> None:
    """Upsert the local user while satisfying the forced-RLS owner policy."""

    email = f"local-alpha-{user_id}@alicebot.local"
    with psycopg.connect(database_admin_url) as conn:
        with conn.transaction():
            set_current_user(conn, user_id)
            with conn.cursor() as cur:
                cur.execute(
                    SEED_LOCAL_USER_SQL,
                    (user_id, email, "Local Alpha User"),
                )


def main(environment: Mapping[str, str] | None = None) -> int:
    current_env = os.environ if environment is None else environment
    user_id_raw = current_env.get("ALICEBOT_AUTH_USER_ID", "").strip()
    if user_id_raw == "":
        raise SystemExit("ALICEBOT_AUTH_USER_ID is required before seeding the local Alice user")
    try:
        user_id = UUID(user_id_raw)
    except ValueError as exc:
        raise SystemExit("ALICEBOT_AUTH_USER_ID must be a valid UUID") from exc

    database_admin_url = current_env.get("DATABASE_ADMIN_URL", "").strip()
    if database_admin_url == "":
        raise SystemExit("DATABASE_ADMIN_URL is required before seeding the local Alice user")

    try:
        seed_local_user(database_admin_url=database_admin_url, user_id=user_id)
    except psycopg.Error as exc:
        failure_code = exc.sqlstate or "database_error"
        raise SystemExit(f"local user seed failed ({failure_code})") from None
    print("local_user_seed=ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
