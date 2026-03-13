from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
import os

DEFAULT_APP_ENV = "development"
DEFAULT_APP_HOST = "127.0.0.1"
DEFAULT_APP_PORT = 8000
DEFAULT_DATABASE_NAME = "alicebot"
DEFAULT_DATABASE_HOST = "localhost"
DEFAULT_DATABASE_PORT = 5432
DEFAULT_DATABASE_URL = (
    f"postgresql://alicebot_app:alicebot_app@{DEFAULT_DATABASE_HOST}:"
    f"{DEFAULT_DATABASE_PORT}/{DEFAULT_DATABASE_NAME}"
)
DEFAULT_DATABASE_ADMIN_URL = (
    f"postgresql://alicebot_admin:alicebot_admin@{DEFAULT_DATABASE_HOST}:"
    f"{DEFAULT_DATABASE_PORT}/{DEFAULT_DATABASE_NAME}"
)
DEFAULT_REDIS_URL = f"redis://{DEFAULT_DATABASE_HOST}:6379/0"
DEFAULT_S3_ENDPOINT_URL = "http://localhost:9000"
DEFAULT_S3_ACCESS_KEY = "alicebot"
DEFAULT_S3_SECRET_KEY = "alicebot-secret"
DEFAULT_S3_BUCKET = "alicebot-local"
DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS = 2
DEFAULT_MODEL_PROVIDER = "openai_responses"
DEFAULT_MODEL_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL_NAME = "gpt-5-mini"
DEFAULT_MODEL_API_KEY = ""
DEFAULT_MODEL_TIMEOUT_SECONDS = 30
DEFAULT_TASK_WORKSPACE_ROOT = "/tmp/alicebot/task-workspaces"

Environment = Mapping[str, str]


def _get_env_value(env: Environment, key: str, default: str) -> str:
    return env.get(key, default)


def _get_env_int(env: Environment, key: str, default: int) -> int:
    raw_value = env.get(key)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    app_env: str = DEFAULT_APP_ENV
    app_host: str = DEFAULT_APP_HOST
    app_port: int = DEFAULT_APP_PORT
    database_url: str = DEFAULT_DATABASE_URL
    database_admin_url: str = DEFAULT_DATABASE_ADMIN_URL
    redis_url: str = DEFAULT_REDIS_URL
    s3_endpoint_url: str = DEFAULT_S3_ENDPOINT_URL
    s3_access_key: str = DEFAULT_S3_ACCESS_KEY
    s3_secret_key: str = DEFAULT_S3_SECRET_KEY
    s3_bucket: str = DEFAULT_S3_BUCKET
    healthcheck_timeout_seconds: int = DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS
    model_provider: str = DEFAULT_MODEL_PROVIDER
    model_base_url: str = DEFAULT_MODEL_BASE_URL
    model_name: str = DEFAULT_MODEL_NAME
    model_api_key: str = DEFAULT_MODEL_API_KEY
    model_timeout_seconds: int = DEFAULT_MODEL_TIMEOUT_SECONDS
    task_workspace_root: str = DEFAULT_TASK_WORKSPACE_ROOT

    @classmethod
    def from_env(cls, env: Environment | None = None) -> "Settings":
        current_env = os.environ if env is None else env
        return cls(
            app_env=_get_env_value(current_env, "APP_ENV", cls.app_env),
            app_host=_get_env_value(current_env, "APP_HOST", cls.app_host),
            app_port=_get_env_int(current_env, "APP_PORT", cls.app_port),
            database_url=_get_env_value(current_env, "DATABASE_URL", cls.database_url),
            database_admin_url=_get_env_value(
                current_env,
                "DATABASE_ADMIN_URL",
                cls.database_admin_url,
            ),
            redis_url=_get_env_value(current_env, "REDIS_URL", cls.redis_url),
            s3_endpoint_url=_get_env_value(
                current_env,
                "S3_ENDPOINT_URL",
                cls.s3_endpoint_url,
            ),
            s3_access_key=_get_env_value(current_env, "S3_ACCESS_KEY", cls.s3_access_key),
            s3_secret_key=_get_env_value(current_env, "S3_SECRET_KEY", cls.s3_secret_key),
            s3_bucket=_get_env_value(current_env, "S3_BUCKET", cls.s3_bucket),
            healthcheck_timeout_seconds=_get_env_int(
                current_env,
                "HEALTHCHECK_TIMEOUT_SECONDS",
                cls.healthcheck_timeout_seconds,
            ),
            model_provider=_get_env_value(current_env, "MODEL_PROVIDER", cls.model_provider),
            model_base_url=_get_env_value(current_env, "MODEL_BASE_URL", cls.model_base_url),
            model_name=_get_env_value(current_env, "MODEL_NAME", cls.model_name),
            model_api_key=_get_env_value(current_env, "MODEL_API_KEY", cls.model_api_key),
            model_timeout_seconds=_get_env_int(
                current_env,
                "MODEL_TIMEOUT_SECONDS",
                cls.model_timeout_seconds,
            ),
            task_workspace_root=_get_env_value(
                current_env,
                "TASK_WORKSPACE_ROOT",
                cls.task_workspace_root,
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
