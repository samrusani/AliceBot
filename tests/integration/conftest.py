from __future__ import annotations

from collections.abc import Iterator
import os
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from alembic import command
import psycopg
from psycopg import sql
import pytest

import apps.api.src.alicebot_api.main as main_module
from alicebot_api.migrations import make_alembic_config


DEFAULT_ADMIN_URL = "postgresql://alicebot_admin:alicebot_admin@localhost:5432/alicebot"
DEFAULT_APP_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"


def swap_database_name(database_url: str, database_name: str) -> str:
    parsed = urlsplit(database_url)
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database_name}", parsed.query, parsed.fragment))


@pytest.fixture
def database_urls() -> Iterator[dict[str, str]]:
    admin_root_url = os.getenv("DATABASE_ADMIN_URL", DEFAULT_ADMIN_URL)
    app_root_url = os.getenv("DATABASE_URL", DEFAULT_APP_URL)
    database_name = f"alicebot_test_{uuid4().hex[:12]}"
    admin_database_url = swap_database_name(admin_root_url, database_name)
    app_database_url = swap_database_name(app_root_url, database_name)

    with psycopg.connect(admin_root_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
            cur.execute(
                sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO alicebot_app").format(
                    sql.Identifier(database_name)
                )
            )

    yield {"admin": admin_database_url, "app": app_database_url}

    with psycopg.connect(admin_root_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(database_name))
            )


@pytest.fixture
def migrated_database_urls(database_urls: dict[str, str]) -> Iterator[dict[str, str]]:
    config = make_alembic_config(database_urls["admin"])
    command.upgrade(config, "head")
    yield database_urls


@pytest.fixture(autouse=True)
def reset_response_rate_limiter_between_tests() -> Iterator[None]:
    main_module.response_rate_limiter.reset()
    main_module.entrypoint_rate_limiter.reset()
    yield
    main_module.response_rate_limiter.reset()
    main_module.entrypoint_rate_limiter.reset()
