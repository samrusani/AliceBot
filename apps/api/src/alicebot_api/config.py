from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
import os
from uuid import UUID

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
DEFAULT_GMAIL_SECRET_MANAGER_URL = ""
DEFAULT_CALENDAR_SECRET_MANAGER_URL = ""
DEFAULT_AUTH_USER_ID = ""
DEFAULT_RESPONSE_RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_RESPONSE_RATE_LIMIT_MAX_REQUESTS = 20
DEFAULT_MAGIC_LINK_TTL_SECONDS = 900
DEFAULT_AUTH_SESSION_TTL_SECONDS = 2_592_000
DEFAULT_DEVICE_LINK_TTL_SECONDS = 600
DEFAULT_TELEGRAM_LINK_TTL_SECONDS = 600
DEFAULT_TELEGRAM_BOT_USERNAME = "alicebot"
DEFAULT_TELEGRAM_WEBHOOK_SECRET = ""
DEFAULT_TELEGRAM_BOT_TOKEN = ""

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
    gmail_secret_manager_url: str = DEFAULT_GMAIL_SECRET_MANAGER_URL
    calendar_secret_manager_url: str = DEFAULT_CALENDAR_SECRET_MANAGER_URL
    auth_user_id: str = DEFAULT_AUTH_USER_ID
    response_rate_limit_window_seconds: int = DEFAULT_RESPONSE_RATE_LIMIT_WINDOW_SECONDS
    response_rate_limit_max_requests: int = DEFAULT_RESPONSE_RATE_LIMIT_MAX_REQUESTS
    magic_link_ttl_seconds: int = DEFAULT_MAGIC_LINK_TTL_SECONDS
    auth_session_ttl_seconds: int = DEFAULT_AUTH_SESSION_TTL_SECONDS
    device_link_ttl_seconds: int = DEFAULT_DEVICE_LINK_TTL_SECONDS
    telegram_link_ttl_seconds: int = DEFAULT_TELEGRAM_LINK_TTL_SECONDS
    telegram_bot_username: str = DEFAULT_TELEGRAM_BOT_USERNAME
    telegram_webhook_secret: str = DEFAULT_TELEGRAM_WEBHOOK_SECRET
    telegram_bot_token: str = DEFAULT_TELEGRAM_BOT_TOKEN

    @classmethod
    def from_env(cls, env: Environment | None = None) -> "Settings":
        current_env = os.environ if env is None else env
        settings = cls(
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
            gmail_secret_manager_url=_get_env_value(
                current_env,
                "GMAIL_SECRET_MANAGER_URL",
                cls.gmail_secret_manager_url,
            ),
            calendar_secret_manager_url=_get_env_value(
                current_env,
                "CALENDAR_SECRET_MANAGER_URL",
                cls.calendar_secret_manager_url,
            ),
            auth_user_id=_get_env_value(current_env, "ALICEBOT_AUTH_USER_ID", cls.auth_user_id).strip(),
            response_rate_limit_window_seconds=_get_env_int(
                current_env,
                "RESPONSE_RATE_LIMIT_WINDOW_SECONDS",
                cls.response_rate_limit_window_seconds,
            ),
            response_rate_limit_max_requests=_get_env_int(
                current_env,
                "RESPONSE_RATE_LIMIT_MAX_REQUESTS",
                cls.response_rate_limit_max_requests,
            ),
            magic_link_ttl_seconds=_get_env_int(
                current_env,
                "MAGIC_LINK_TTL_SECONDS",
                cls.magic_link_ttl_seconds,
            ),
            auth_session_ttl_seconds=_get_env_int(
                current_env,
                "AUTH_SESSION_TTL_SECONDS",
                cls.auth_session_ttl_seconds,
            ),
            device_link_ttl_seconds=_get_env_int(
                current_env,
                "DEVICE_LINK_TTL_SECONDS",
                cls.device_link_ttl_seconds,
            ),
            telegram_link_ttl_seconds=_get_env_int(
                current_env,
                "TELEGRAM_LINK_TTL_SECONDS",
                cls.telegram_link_ttl_seconds,
            ),
            telegram_bot_username=_get_env_value(
                current_env,
                "TELEGRAM_BOT_USERNAME",
                cls.telegram_bot_username,
            ).strip(),
            telegram_webhook_secret=_get_env_value(
                current_env,
                "TELEGRAM_WEBHOOK_SECRET",
                cls.telegram_webhook_secret,
            ).strip(),
            telegram_bot_token=_get_env_value(
                current_env,
                "TELEGRAM_BOT_TOKEN",
                cls.telegram_bot_token,
            ).strip(),
        )
        return _validate_settings(settings)


def _validate_settings(settings: Settings) -> Settings:
    if settings.auth_user_id != "":
        try:
            UUID(settings.auth_user_id)
        except ValueError as exc:
            raise ValueError("ALICEBOT_AUTH_USER_ID must be a valid UUID") from exc

    if settings.response_rate_limit_window_seconds <= 0:
        raise ValueError("RESPONSE_RATE_LIMIT_WINDOW_SECONDS must be a positive integer")
    if settings.response_rate_limit_max_requests <= 0:
        raise ValueError("RESPONSE_RATE_LIMIT_MAX_REQUESTS must be a positive integer")
    if settings.magic_link_ttl_seconds <= 0:
        raise ValueError("MAGIC_LINK_TTL_SECONDS must be a positive integer")
    if settings.auth_session_ttl_seconds <= 0:
        raise ValueError("AUTH_SESSION_TTL_SECONDS must be a positive integer")
    if settings.device_link_ttl_seconds <= 0:
        raise ValueError("DEVICE_LINK_TTL_SECONDS must be a positive integer")
    if settings.telegram_link_ttl_seconds <= 0:
        raise ValueError("TELEGRAM_LINK_TTL_SECONDS must be a positive integer")
    if settings.telegram_bot_username == "":
        raise ValueError("TELEGRAM_BOT_USERNAME must be provided")

    if settings.app_env not in {"development", "test"}:
        if settings.auth_user_id == "":
            raise ValueError(
                "ALICEBOT_AUTH_USER_ID must be configured outside development/test environments"
            )
        if settings.database_url == DEFAULT_DATABASE_URL:
            raise ValueError("DATABASE_URL must be overridden outside development/test environments")
        if settings.database_admin_url == DEFAULT_DATABASE_ADMIN_URL:
            raise ValueError(
                "DATABASE_ADMIN_URL must be overridden outside development/test environments"
            )
        if settings.s3_access_key == DEFAULT_S3_ACCESS_KEY:
            raise ValueError("S3_ACCESS_KEY must be overridden outside development/test environments")
        if settings.s3_secret_key == DEFAULT_S3_SECRET_KEY:
            raise ValueError("S3_SECRET_KEY must be overridden outside development/test environments")

    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
