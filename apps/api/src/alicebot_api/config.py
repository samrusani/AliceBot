from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
import json
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
DEFAULT_APP_LOG_MODE = "stdout"
DEFAULT_APP_LOG_LEVEL = "INFO"
DEFAULT_APP_LOG_PATH = ""
DEFAULT_APP_LOG_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_APP_LOG_BACKUP_COUNT = 5
DEFAULT_APP_ACCESS_LOG = True
DEFAULT_MODEL_PROVIDER = "openai_responses"
DEFAULT_MODEL_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL_NAME = "gpt-5-mini"
DEFAULT_MODEL_API_KEY = ""
DEFAULT_MODEL_TIMEOUT_SECONDS = 30
DEFAULT_TASK_WORKSPACE_ROOT = "/tmp/alicebot/task-workspaces"
DEFAULT_PROVIDER_SECRET_MANAGER_URL = ""
DEFAULT_WORKSPACE_PROVIDER_CONFIGS_JSON = "[]"
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
DEFAULT_HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS = 20
DEFAULT_HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS = 300
DEFAULT_HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS = 20
DEFAULT_HOSTED_ABUSE_WINDOW_SECONDS = 600
DEFAULT_HOSTED_ABUSE_BLOCK_THRESHOLD = 5
DEFAULT_HOSTED_RATE_LIMITS_ENABLED_BY_DEFAULT = True
DEFAULT_HOSTED_ABUSE_CONTROLS_ENABLED_BY_DEFAULT = True
DEFAULT_MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS = 300
DEFAULT_MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS = 5
DEFAULT_MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS = 300
DEFAULT_MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS = 10
DEFAULT_TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS = 120
DEFAULT_CORS_ALLOWED_ORIGINS: tuple[str, ...] = ()
DEFAULT_CORS_ALLOWED_METHODS: tuple[str, ...] = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
)
DEFAULT_CORS_ALLOWED_HEADERS: tuple[str, ...] = (
    "Authorization",
    "Content-Type",
    "X-AliceBot-User-Id",
    "X-Telegram-Bot-Api-Secret-Token",
)
DEFAULT_CORS_ALLOW_CREDENTIALS = False
DEFAULT_CORS_PREFLIGHT_MAX_AGE_SECONDS = 600
DEFAULT_SECURITY_HEADERS_ENABLED = True
DEFAULT_SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS = 31_536_000
DEFAULT_SECURITY_HEADERS_HSTS_INCLUDE_SUBDOMAINS = True
DEFAULT_TRUST_PROXY_HEADERS = False
DEFAULT_TRUSTED_PROXY_IPS: tuple[str, ...] = ()
DEFAULT_ENTRYPOINT_RATE_LIMIT_BACKEND = "redis"
DEFAULT_RETRIEVAL_TRACE_RETENTION_DAYS = 14
DEFAULT_LEGACY_V0_ENABLED_OUTSIDE_DEV = False

Environment = Mapping[str, str]


@dataclass(frozen=True)
class WorkspaceProviderConfig:
    provider_key: str
    display_name: str
    base_url: str
    api_key: str
    default_model: str
    auth_mode: str = "bearer"
    model_list_path: str = "/models"
    healthcheck_path: str = "/models"
    invoke_path: str = "/responses"
    metadata: Mapping[str, object] | None = None


_WORKSPACE_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai_compatible": {
        "auth_mode": "bearer",
        "model_list_path": "/models",
        "healthcheck_path": "/models",
        "invoke_path": "/responses",
    },
    "vllm": {
        "auth_mode": "none",
        "model_list_path": "/v1/models",
        "healthcheck_path": "/health",
        "invoke_path": "/v1/chat/completions",
    },
}


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


def _get_env_bool(env: Environment, key: str, default: bool) -> bool:
    raw_value = env.get(key)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_env_csv(env: Environment, key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = env.get(key)
    if raw_value is None:
        return default

    return tuple(item.strip() for item in raw_value.split(",") if item.strip() != "")


def _normalize_csv_tokens(
    values: tuple[str, ...],
    *,
    uppercase: bool = False,
) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        token = value.strip()
        if token == "":
            continue
        if uppercase:
            token = token.upper()
        if token not in normalized:
            normalized.append(token)
    return tuple(normalized)


@dataclass(frozen=True)
class Settings:
    app_env: str = DEFAULT_APP_ENV
    app_host: str = DEFAULT_APP_HOST
    app_port: int = DEFAULT_APP_PORT
    app_log_mode: str = DEFAULT_APP_LOG_MODE
    app_log_level: str = DEFAULT_APP_LOG_LEVEL
    app_log_path: str = DEFAULT_APP_LOG_PATH
    app_log_max_bytes: int = DEFAULT_APP_LOG_MAX_BYTES
    app_log_backup_count: int = DEFAULT_APP_LOG_BACKUP_COUNT
    app_access_log: bool = DEFAULT_APP_ACCESS_LOG
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
    provider_secret_manager_url: str = DEFAULT_PROVIDER_SECRET_MANAGER_URL
    workspace_provider_configs: tuple[WorkspaceProviderConfig, ...] = ()
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
    hosted_chat_rate_limit_window_seconds: int = DEFAULT_HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS
    hosted_chat_rate_limit_max_requests: int = DEFAULT_HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS
    hosted_scheduler_rate_limit_window_seconds: int = DEFAULT_HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS
    hosted_scheduler_rate_limit_max_requests: int = DEFAULT_HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS
    hosted_abuse_window_seconds: int = DEFAULT_HOSTED_ABUSE_WINDOW_SECONDS
    hosted_abuse_block_threshold: int = DEFAULT_HOSTED_ABUSE_BLOCK_THRESHOLD
    hosted_rate_limits_enabled_by_default: bool = DEFAULT_HOSTED_RATE_LIMITS_ENABLED_BY_DEFAULT
    hosted_abuse_controls_enabled_by_default: bool = DEFAULT_HOSTED_ABUSE_CONTROLS_ENABLED_BY_DEFAULT
    magic_link_start_rate_limit_window_seconds: int = (
        DEFAULT_MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS
    )
    magic_link_start_rate_limit_max_requests: int = DEFAULT_MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS
    magic_link_verify_rate_limit_window_seconds: int = (
        DEFAULT_MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS
    )
    magic_link_verify_rate_limit_max_requests: int = DEFAULT_MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS
    telegram_webhook_rate_limit_window_seconds: int = (
        DEFAULT_TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS
    )
    telegram_webhook_rate_limit_max_requests: int = DEFAULT_TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS
    cors_allowed_origins: tuple[str, ...] = DEFAULT_CORS_ALLOWED_ORIGINS
    cors_allowed_methods: tuple[str, ...] = DEFAULT_CORS_ALLOWED_METHODS
    cors_allowed_headers: tuple[str, ...] = DEFAULT_CORS_ALLOWED_HEADERS
    cors_allow_credentials: bool = DEFAULT_CORS_ALLOW_CREDENTIALS
    cors_preflight_max_age_seconds: int = DEFAULT_CORS_PREFLIGHT_MAX_AGE_SECONDS
    security_headers_enabled: bool = DEFAULT_SECURITY_HEADERS_ENABLED
    security_headers_hsts_max_age_seconds: int = DEFAULT_SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS
    security_headers_hsts_include_subdomains: bool = (
        DEFAULT_SECURITY_HEADERS_HSTS_INCLUDE_SUBDOMAINS
    )
    trust_proxy_headers: bool = DEFAULT_TRUST_PROXY_HEADERS
    trusted_proxy_ips: tuple[str, ...] = DEFAULT_TRUSTED_PROXY_IPS
    entrypoint_rate_limit_backend: str = DEFAULT_ENTRYPOINT_RATE_LIMIT_BACKEND
    retrieval_trace_retention_days: int = DEFAULT_RETRIEVAL_TRACE_RETENTION_DAYS
    legacy_v0_enabled_outside_dev: bool = DEFAULT_LEGACY_V0_ENABLED_OUTSIDE_DEV

    @classmethod
    def from_env(cls, env: Environment | None = None) -> "Settings":
        current_env = os.environ if env is None else env
        settings = cls(
            app_env=_get_env_value(current_env, "APP_ENV", cls.app_env),
            app_host=_get_env_value(current_env, "APP_HOST", cls.app_host),
            app_port=_get_env_int(current_env, "APP_PORT", cls.app_port),
            app_log_mode=_get_env_value(current_env, "APP_LOG_MODE", cls.app_log_mode).strip().lower(),
            app_log_level=_get_env_value(current_env, "APP_LOG_LEVEL", cls.app_log_level).strip().upper(),
            app_log_path=_get_env_value(current_env, "APP_LOG_PATH", cls.app_log_path).strip(),
            app_log_max_bytes=_get_env_int(
                current_env,
                "APP_LOG_MAX_BYTES",
                cls.app_log_max_bytes,
            ),
            app_log_backup_count=_get_env_int(
                current_env,
                "APP_LOG_BACKUP_COUNT",
                cls.app_log_backup_count,
            ),
            app_access_log=_get_env_bool(
                current_env,
                "APP_ACCESS_LOG",
                cls.app_access_log,
            ),
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
            provider_secret_manager_url=_get_env_value(
                current_env,
                "PROVIDER_SECRET_MANAGER_URL",
                cls.provider_secret_manager_url,
            ),
            workspace_provider_configs=_parse_workspace_provider_configs(
                _get_env_value(
                    current_env,
                    "WORKSPACE_PROVIDER_CONFIGS_JSON",
                    DEFAULT_WORKSPACE_PROVIDER_CONFIGS_JSON,
                )
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
            hosted_chat_rate_limit_window_seconds=_get_env_int(
                current_env,
                "HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS",
                cls.hosted_chat_rate_limit_window_seconds,
            ),
            hosted_chat_rate_limit_max_requests=_get_env_int(
                current_env,
                "HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS",
                cls.hosted_chat_rate_limit_max_requests,
            ),
            hosted_scheduler_rate_limit_window_seconds=_get_env_int(
                current_env,
                "HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS",
                cls.hosted_scheduler_rate_limit_window_seconds,
            ),
            hosted_scheduler_rate_limit_max_requests=_get_env_int(
                current_env,
                "HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS",
                cls.hosted_scheduler_rate_limit_max_requests,
            ),
            hosted_abuse_window_seconds=_get_env_int(
                current_env,
                "HOSTED_ABUSE_WINDOW_SECONDS",
                cls.hosted_abuse_window_seconds,
            ),
            hosted_abuse_block_threshold=_get_env_int(
                current_env,
                "HOSTED_ABUSE_BLOCK_THRESHOLD",
                cls.hosted_abuse_block_threshold,
            ),
            hosted_rate_limits_enabled_by_default=_get_env_bool(
                current_env,
                "HOSTED_RATE_LIMITS_ENABLED_BY_DEFAULT",
                cls.hosted_rate_limits_enabled_by_default,
            ),
            hosted_abuse_controls_enabled_by_default=_get_env_bool(
                current_env,
                "HOSTED_ABUSE_CONTROLS_ENABLED_BY_DEFAULT",
                cls.hosted_abuse_controls_enabled_by_default,
            ),
            magic_link_start_rate_limit_window_seconds=_get_env_int(
                current_env,
                "MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS",
                cls.magic_link_start_rate_limit_window_seconds,
            ),
            magic_link_start_rate_limit_max_requests=_get_env_int(
                current_env,
                "MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS",
                cls.magic_link_start_rate_limit_max_requests,
            ),
            magic_link_verify_rate_limit_window_seconds=_get_env_int(
                current_env,
                "MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS",
                cls.magic_link_verify_rate_limit_window_seconds,
            ),
            magic_link_verify_rate_limit_max_requests=_get_env_int(
                current_env,
                "MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS",
                cls.magic_link_verify_rate_limit_max_requests,
            ),
            telegram_webhook_rate_limit_window_seconds=_get_env_int(
                current_env,
                "TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS",
                cls.telegram_webhook_rate_limit_window_seconds,
            ),
            telegram_webhook_rate_limit_max_requests=_get_env_int(
                current_env,
                "TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS",
                cls.telegram_webhook_rate_limit_max_requests,
            ),
            cors_allowed_origins=_normalize_csv_tokens(
                _get_env_csv(current_env, "CORS_ALLOWED_ORIGINS", cls.cors_allowed_origins),
            ),
            cors_allowed_methods=_normalize_csv_tokens(
                _get_env_csv(current_env, "CORS_ALLOWED_METHODS", cls.cors_allowed_methods),
                uppercase=True,
            ),
            cors_allowed_headers=_normalize_csv_tokens(
                _get_env_csv(current_env, "CORS_ALLOWED_HEADERS", cls.cors_allowed_headers),
            ),
            cors_allow_credentials=_get_env_bool(
                current_env,
                "CORS_ALLOW_CREDENTIALS",
                cls.cors_allow_credentials,
            ),
            cors_preflight_max_age_seconds=_get_env_int(
                current_env,
                "CORS_PREFLIGHT_MAX_AGE_SECONDS",
                cls.cors_preflight_max_age_seconds,
            ),
            security_headers_enabled=_get_env_bool(
                current_env,
                "SECURITY_HEADERS_ENABLED",
                cls.security_headers_enabled,
            ),
            security_headers_hsts_max_age_seconds=_get_env_int(
                current_env,
                "SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS",
                cls.security_headers_hsts_max_age_seconds,
            ),
            security_headers_hsts_include_subdomains=_get_env_bool(
                current_env,
                "SECURITY_HEADERS_HSTS_INCLUDE_SUBDOMAINS",
                cls.security_headers_hsts_include_subdomains,
            ),
            trust_proxy_headers=_get_env_bool(
                current_env,
                "TRUST_PROXY_HEADERS",
                cls.trust_proxy_headers,
            ),
            trusted_proxy_ips=_normalize_csv_tokens(
                _get_env_csv(current_env, "TRUSTED_PROXY_IPS", cls.trusted_proxy_ips),
            ),
            entrypoint_rate_limit_backend=_get_env_value(
                current_env,
                "ENTRYPOINT_RATE_LIMIT_BACKEND",
                cls.entrypoint_rate_limit_backend,
            ).strip().lower(),
            retrieval_trace_retention_days=_get_env_int(
                current_env,
                "RETRIEVAL_TRACE_RETENTION_DAYS",
                cls.retrieval_trace_retention_days,
            ),
            legacy_v0_enabled_outside_dev=_get_env_bool(
                current_env,
                "LEGACY_V0_ENABLED_OUTSIDE_DEV",
                cls.legacy_v0_enabled_outside_dev,
            ),
        )
        return _validate_settings(settings)


def _parse_workspace_provider_configs(raw_value: str) -> tuple[WorkspaceProviderConfig, ...]:
    normalized_raw = raw_value.strip()
    if normalized_raw == "":
        return ()

    try:
        payload = json.loads(normalized_raw)
    except json.JSONDecodeError as exc:
        raise ValueError("WORKSPACE_PROVIDER_CONFIGS_JSON must be valid JSON") from exc

    if not isinstance(payload, list):
        raise ValueError("WORKSPACE_PROVIDER_CONFIGS_JSON must decode to a list")

    configs: list[WorkspaceProviderConfig] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}] must be an object"
            )

        provider_key = str(item.get("provider_key", "openai_compatible")).strip()
        provider_defaults = _WORKSPACE_PROVIDER_DEFAULTS.get(provider_key)
        if provider_defaults is None:
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].provider_key must be one of "
                f"{', '.join(sorted(_WORKSPACE_PROVIDER_DEFAULTS))}"
            )

        metadata = item.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].metadata must be an object"
            )

        config = WorkspaceProviderConfig(
            provider_key=provider_key,
            display_name=str(item.get("display_name", "")).strip(),
            base_url=str(item.get("base_url", "")).strip(),
            api_key=str(item.get("api_key", "")).strip(),
            default_model=str(item.get("default_model", "")).strip(),
            auth_mode=str(item.get("auth_mode", provider_defaults["auth_mode"])).strip().lower(),
            model_list_path=str(item.get("model_list_path", provider_defaults["model_list_path"])).strip(),
            healthcheck_path=str(item.get("healthcheck_path", provider_defaults["healthcheck_path"])).strip(),
            invoke_path=str(item.get("invoke_path", provider_defaults["invoke_path"])).strip(),
            metadata=metadata,
        )
        configs.append(config)

    return tuple(configs)


def _validate_settings(settings: Settings) -> Settings:
    if settings.app_log_mode not in {"stdout", "file"}:
        raise ValueError("APP_LOG_MODE must be either 'stdout' or 'file'")
    if settings.app_log_level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
        raise ValueError(
            "APP_LOG_LEVEL must be one of CRITICAL, ERROR, WARNING, INFO, or DEBUG"
        )
    if settings.app_log_max_bytes <= 0:
        raise ValueError("APP_LOG_MAX_BYTES must be a positive integer")
    if settings.app_log_backup_count <= 0:
        raise ValueError("APP_LOG_BACKUP_COUNT must be a positive integer")
    if settings.app_log_mode == "file" and settings.app_log_path == "":
        raise ValueError("APP_LOG_PATH must be configured when APP_LOG_MODE is 'file'")
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
    if settings.hosted_chat_rate_limit_window_seconds <= 0:
        raise ValueError("HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS must be a positive integer")
    if settings.hosted_chat_rate_limit_max_requests <= 0:
        raise ValueError("HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS must be a positive integer")
    if settings.hosted_scheduler_rate_limit_window_seconds <= 0:
        raise ValueError("HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS must be a positive integer")
    if settings.hosted_scheduler_rate_limit_max_requests <= 0:
        raise ValueError("HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS must be a positive integer")
    if settings.hosted_abuse_window_seconds <= 0:
        raise ValueError("HOSTED_ABUSE_WINDOW_SECONDS must be a positive integer")
    if settings.hosted_abuse_block_threshold <= 0:
        raise ValueError("HOSTED_ABUSE_BLOCK_THRESHOLD must be a positive integer")
    if settings.magic_link_start_rate_limit_window_seconds <= 0:
        raise ValueError("MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS must be a positive integer")
    if settings.magic_link_start_rate_limit_max_requests <= 0:
        raise ValueError("MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS must be a positive integer")
    if settings.magic_link_verify_rate_limit_window_seconds <= 0:
        raise ValueError("MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS must be a positive integer")
    if settings.magic_link_verify_rate_limit_max_requests <= 0:
        raise ValueError("MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS must be a positive integer")
    if settings.telegram_webhook_rate_limit_window_seconds <= 0:
        raise ValueError("TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS must be a positive integer")
    if settings.telegram_webhook_rate_limit_max_requests <= 0:
        raise ValueError("TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS must be a positive integer")
    if settings.cors_preflight_max_age_seconds <= 0:
        raise ValueError("CORS_PREFLIGHT_MAX_AGE_SECONDS must be a positive integer")
    if len(settings.cors_allowed_methods) == 0:
        raise ValueError("CORS_ALLOWED_METHODS must include at least one method")
    if settings.security_headers_hsts_max_age_seconds <= 0:
        raise ValueError("SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS must be a positive integer")
    if settings.entrypoint_rate_limit_backend not in {"redis", "memory"}:
        raise ValueError("ENTRYPOINT_RATE_LIMIT_BACKEND must be either 'redis' or 'memory'")
    if settings.retrieval_trace_retention_days <= 0:
        raise ValueError("RETRIEVAL_TRACE_RETENTION_DAYS must be a positive integer")
    if settings.trust_proxy_headers and len(settings.trusted_proxy_ips) == 0:
        raise ValueError("TRUSTED_PROXY_IPS must include at least one IP when TRUST_PROXY_HEADERS is enabled")
    for index, provider_config in enumerate(settings.workspace_provider_configs):
        if provider_config.display_name == "":
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].display_name is required"
            )
        if provider_config.base_url == "":
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].base_url is required"
            )
        if provider_config.default_model == "":
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].default_model is required"
            )
        if provider_config.auth_mode not in {"bearer", "none"}:
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].auth_mode must be bearer or none"
            )
        if provider_config.auth_mode == "bearer" and provider_config.api_key == "":
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].api_key is required when auth_mode is bearer"
            )
        if provider_config.auth_mode == "none" and provider_config.api_key != "":
            raise ValueError(
                f"WORKSPACE_PROVIDER_CONFIGS_JSON[{index}].api_key must be empty when auth_mode is none"
            )

    if settings.app_env not in {"development", "test"}:
        if "*" in settings.cors_allowed_origins:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS cannot include wildcard outside development/test environments"
            )
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
        if settings.telegram_webhook_secret == "":
            raise ValueError(
                "TELEGRAM_WEBHOOK_SECRET must be configured outside development/test environments"
            )

    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
