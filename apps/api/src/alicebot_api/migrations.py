from __future__ import annotations

from importlib.resources import files as package_files
from pathlib import Path

from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _resolve_alembic_paths() -> tuple[Path, Path]:
    repo_ini = PROJECT_ROOT / "apps" / "api" / "alembic.ini"
    repo_scripts = PROJECT_ROOT / "apps" / "api" / "alembic"
    if repo_ini.is_file() and repo_scripts.is_dir():
        return repo_ini, repo_scripts

    resource_root = package_files("alicebot_api").joinpath("_resources")
    packaged_ini = Path(str(resource_root.joinpath("alembic.ini")))
    packaged_scripts = Path(str(resource_root.joinpath("alembic")))
    if not packaged_ini.is_file() or not packaged_scripts.is_dir():
        raise FileNotFoundError(
            "Alembic resources are missing from both the checkout and installed package"
        )
    return packaged_ini, packaged_scripts


ALEMBIC_INI_PATH, ALEMBIC_SCRIPT_PATH = _resolve_alembic_paths()


def make_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    # The checked-in ini uses a repo-relative script path. Override it with an
    # absolute path so migrations also work from an installed wheel or sdist
    # and when the command is launched outside the repository root.
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_PATH))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
        # An explicitly passed URL must win over DATABASE_ADMIN_URL/DATABASE_URL
        # env vars in env.py; otherwise per-test databases created by callers
        # are never the ones migrated when those env vars are set.
        config.attributes["explicit_database_url"] = database_url
    return config
