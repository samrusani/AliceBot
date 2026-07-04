from __future__ import annotations

from pathlib import Path

from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ALEMBIC_INI_PATH = PROJECT_ROOT / "apps" / "api" / "alembic.ini"


def make_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
        # An explicitly passed URL must win over DATABASE_ADMIN_URL/DATABASE_URL
        # env vars in env.py; otherwise per-test databases created by callers
        # are never the ones migrated when those env vars are set.
        config.attributes["explicit_database_url"] = database_url
    return config

