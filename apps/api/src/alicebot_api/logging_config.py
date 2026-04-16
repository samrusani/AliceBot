from __future__ import annotations

from pathlib import Path
from typing import Any

from alicebot_api.config import Settings


def build_uvicorn_log_config(settings: Settings) -> dict[str, Any]:
    handlers: dict[str, dict[str, Any]] = {
        "null": {
            "class": "logging.NullHandler",
        }
    }
    formatters: dict[str, dict[str, Any]] = {}
    primary_handler = "stdout"

    if settings.app_log_mode == "file":
        log_path = Path(settings.app_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_path),
            "maxBytes": settings.app_log_max_bytes,
            "backupCount": settings.app_log_backup_count,
            "encoding": "utf-8",
            "formatter": "file",
        }
        formatters["file"] = {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        }
        primary_handler = "file"
    else:
        handlers["stdout"] = {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default",
        }
        handlers["access"] = {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "access",
        }
        formatters["default"] = {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": False,
        }
        formatters["access"] = {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "use_colors": False,
        }

    access_handler = "null"
    if settings.app_access_log:
        access_handler = "access" if settings.app_log_mode == "stdout" else primary_handler

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            "uvicorn": {
                "handlers": [primary_handler],
                "level": settings.app_log_level,
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": [primary_handler],
                "level": settings.app_log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": [access_handler],
                "level": settings.app_log_level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": [primary_handler],
            "level": settings.app_log_level,
        },
    }
