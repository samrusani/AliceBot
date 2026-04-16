from __future__ import annotations

import os

import uvicorn

from alicebot_api.config import get_settings
from alicebot_api.logging_config import build_uvicorn_log_config


def _env_flag(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    settings = get_settings()
    uvicorn.run(
        "alicebot_api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=_env_flag("APP_RELOAD", default=True),
        access_log=settings.app_access_log,
        log_config=build_uvicorn_log_config(settings),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
