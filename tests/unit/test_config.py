from __future__ import annotations

import pytest

from alicebot_api.config import Settings


def test_settings_defaults(monkeypatch):
    for key in (
        "APP_ENV",
        "APP_HOST",
        "APP_PORT",
        "DATABASE_URL",
        "DATABASE_ADMIN_URL",
        "REDIS_URL",
        "S3_ENDPOINT_URL",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_BUCKET",
        "HEALTHCHECK_TIMEOUT_SECONDS",
        "MODEL_PROVIDER",
        "MODEL_BASE_URL",
        "MODEL_NAME",
        "MODEL_API_KEY",
        "MODEL_TIMEOUT_SECONDS",
        "TASK_WORKSPACE_ROOT",
        "GMAIL_SECRET_MANAGER_URL",
        "CALENDAR_SECRET_MANAGER_URL",
        "ALICEBOT_AUTH_USER_ID",
        "RESPONSE_RATE_LIMIT_WINDOW_SECONDS",
        "RESPONSE_RATE_LIMIT_MAX_REQUESTS",
        "TELEGRAM_LINK_TTL_SECONDS",
        "TELEGRAM_BOT_USERNAME",
        "TELEGRAM_WEBHOOK_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS",
        "HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS",
        "HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS",
        "HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS",
        "HOSTED_ABUSE_WINDOW_SECONDS",
        "HOSTED_ABUSE_BLOCK_THRESHOLD",
        "HOSTED_RATE_LIMITS_ENABLED_BY_DEFAULT",
        "HOSTED_ABUSE_CONTROLS_ENABLED_BY_DEFAULT",
        "MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS",
        "MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS",
        "MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS",
        "MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS",
        "TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS",
        "TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS",
        "CORS_ALLOWED_ORIGINS",
        "CORS_ALLOWED_METHODS",
        "CORS_ALLOWED_HEADERS",
        "CORS_ALLOW_CREDENTIALS",
        "CORS_PREFLIGHT_MAX_AGE_SECONDS",
        "SECURITY_HEADERS_ENABLED",
        "SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS",
        "SECURITY_HEADERS_HSTS_INCLUDE_SUBDOMAINS",
        "TRUST_PROXY_HEADERS",
        "TRUSTED_PROXY_IPS",
        "ENTRYPOINT_RATE_LIMIT_BACKEND",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    assert settings.app_env == "development"
    assert settings.app_port == 8000
    assert settings.database_url.endswith("/alicebot")
    assert settings.database_admin_url.endswith("/alicebot")
    assert settings.s3_bucket == "alicebot-local"
    assert settings.model_provider == "openai_responses"
    assert settings.model_base_url == "https://api.openai.com/v1"
    assert settings.model_name == "gpt-5-mini"
    assert settings.model_timeout_seconds == 30
    assert settings.task_workspace_root == "/tmp/alicebot/task-workspaces"
    assert settings.gmail_secret_manager_url == ""
    assert settings.calendar_secret_manager_url == ""
    assert settings.auth_user_id == ""
    assert settings.response_rate_limit_window_seconds == 60
    assert settings.response_rate_limit_max_requests == 20
    assert settings.telegram_link_ttl_seconds == 600
    assert settings.telegram_bot_username == "alicebot"
    assert settings.telegram_webhook_secret == ""
    assert settings.telegram_bot_token == ""
    assert settings.hosted_chat_rate_limit_window_seconds == 60
    assert settings.hosted_chat_rate_limit_max_requests == 20
    assert settings.hosted_scheduler_rate_limit_window_seconds == 300
    assert settings.hosted_scheduler_rate_limit_max_requests == 20
    assert settings.hosted_abuse_window_seconds == 600
    assert settings.hosted_abuse_block_threshold == 5
    assert settings.hosted_rate_limits_enabled_by_default is True
    assert settings.hosted_abuse_controls_enabled_by_default is True
    assert settings.magic_link_start_rate_limit_window_seconds == 300
    assert settings.magic_link_start_rate_limit_max_requests == 5
    assert settings.magic_link_verify_rate_limit_window_seconds == 300
    assert settings.magic_link_verify_rate_limit_max_requests == 10
    assert settings.telegram_webhook_rate_limit_window_seconds == 60
    assert settings.telegram_webhook_rate_limit_max_requests == 120
    assert settings.cors_allowed_origins == ()
    assert settings.cors_allowed_methods == ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
    assert settings.cors_allowed_headers == (
        "Authorization",
        "Content-Type",
        "X-AliceBot-User-Id",
        "X-Telegram-Bot-Api-Secret-Token",
    )
    assert settings.cors_allow_credentials is False
    assert settings.cors_preflight_max_age_seconds == 600
    assert settings.security_headers_enabled is True
    assert settings.security_headers_hsts_max_age_seconds == 31_536_000
    assert settings.security_headers_hsts_include_subdomains is True
    assert settings.trust_proxy_headers is False
    assert settings.trusted_proxy_ips == ()
    assert settings.entrypoint_rate_limit_backend == "redis"


def test_settings_honor_environment_overrides(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_PORT", "8100")
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:secret@localhost:5432/custom")
    monkeypatch.setenv("HEALTHCHECK_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("MODEL_NAME", "gpt-5")
    monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("TASK_WORKSPACE_ROOT", "/tmp/custom-workspaces")
    monkeypatch.setenv("GMAIL_SECRET_MANAGER_URL", "file:///tmp/custom-gmail-secrets")
    monkeypatch.setenv("CALENDAR_SECRET_MANAGER_URL", "file:///tmp/custom-calendar-secrets")
    monkeypatch.setenv("ALICEBOT_AUTH_USER_ID", "00000000-0000-0000-0000-000000000001")
    monkeypatch.setenv("RESPONSE_RATE_LIMIT_WINDOW_SECONDS", "120")
    monkeypatch.setenv("RESPONSE_RATE_LIMIT_MAX_REQUESTS", "30")
    monkeypatch.setenv("TELEGRAM_LINK_TTL_SECONDS", "900")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "alicebuilder_bot")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "phase10-secret")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-bot-token")
    monkeypatch.setenv("HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS", "75")
    monkeypatch.setenv("HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS", "7")
    monkeypatch.setenv("HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS", "900")
    monkeypatch.setenv("HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS", "12")
    monkeypatch.setenv("HOSTED_ABUSE_WINDOW_SECONDS", "1800")
    monkeypatch.setenv("HOSTED_ABUSE_BLOCK_THRESHOLD", "6")
    monkeypatch.setenv("HOSTED_RATE_LIMITS_ENABLED_BY_DEFAULT", "false")
    monkeypatch.setenv("HOSTED_ABUSE_CONTROLS_ENABLED_BY_DEFAULT", "false")
    monkeypatch.setenv("MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS", "360")
    monkeypatch.setenv("MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS", "8")
    monkeypatch.setenv("MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS", "420")
    monkeypatch.setenv("MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS", "12")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "90")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS", "180")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com, https://staging.example.com",
    )
    monkeypatch.setenv("CORS_ALLOWED_METHODS", "GET,POST,OPTIONS")
    monkeypatch.setenv("CORS_ALLOWED_HEADERS", "Authorization,Content-Type")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    monkeypatch.setenv("CORS_PREFLIGHT_MAX_AGE_SECONDS", "900")
    monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "false")
    monkeypatch.setenv("SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS", "86400")
    monkeypatch.setenv("SECURITY_HEADERS_HSTS_INCLUDE_SUBDOMAINS", "false")
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1,10.0.0.2")
    monkeypatch.setenv("ENTRYPOINT_RATE_LIMIT_BACKEND", "memory")

    settings = Settings.from_env()

    assert settings.app_env == "test"
    assert settings.app_port == 8100
    assert settings.database_url == "postgresql://app:secret@localhost:5432/custom"
    assert settings.healthcheck_timeout_seconds == 9
    assert settings.model_base_url == "https://example.test/v1"
    assert settings.model_name == "gpt-5"
    assert settings.model_timeout_seconds == 45
    assert settings.task_workspace_root == "/tmp/custom-workspaces"
    assert settings.gmail_secret_manager_url == "file:///tmp/custom-gmail-secrets"
    assert settings.calendar_secret_manager_url == "file:///tmp/custom-calendar-secrets"
    assert settings.auth_user_id == "00000000-0000-0000-0000-000000000001"
    assert settings.response_rate_limit_window_seconds == 120
    assert settings.response_rate_limit_max_requests == 30
    assert settings.telegram_link_ttl_seconds == 900
    assert settings.telegram_bot_username == "alicebuilder_bot"
    assert settings.telegram_webhook_secret == "phase10-secret"
    assert settings.telegram_bot_token == "test-bot-token"
    assert settings.hosted_chat_rate_limit_window_seconds == 75
    assert settings.hosted_chat_rate_limit_max_requests == 7
    assert settings.hosted_scheduler_rate_limit_window_seconds == 900
    assert settings.hosted_scheduler_rate_limit_max_requests == 12
    assert settings.hosted_abuse_window_seconds == 1800
    assert settings.hosted_abuse_block_threshold == 6
    assert settings.hosted_rate_limits_enabled_by_default is False
    assert settings.hosted_abuse_controls_enabled_by_default is False
    assert settings.magic_link_start_rate_limit_window_seconds == 360
    assert settings.magic_link_start_rate_limit_max_requests == 8
    assert settings.magic_link_verify_rate_limit_window_seconds == 420
    assert settings.magic_link_verify_rate_limit_max_requests == 12
    assert settings.telegram_webhook_rate_limit_window_seconds == 90
    assert settings.telegram_webhook_rate_limit_max_requests == 180
    assert settings.cors_allowed_origins == ("https://app.example.com", "https://staging.example.com")
    assert settings.cors_allowed_methods == ("GET", "POST", "OPTIONS")
    assert settings.cors_allowed_headers == ("Authorization", "Content-Type")
    assert settings.cors_allow_credentials is True
    assert settings.cors_preflight_max_age_seconds == 900
    assert settings.security_headers_enabled is False
    assert settings.security_headers_hsts_max_age_seconds == 86400
    assert settings.security_headers_hsts_include_subdomains is False
    assert settings.trust_proxy_headers is True
    assert settings.trusted_proxy_ips == ("127.0.0.1", "10.0.0.2")
    assert settings.entrypoint_rate_limit_backend == "memory"


def test_settings_can_be_loaded_from_an_explicit_environment_mapping() -> None:
    settings = Settings.from_env(
        {
            "APP_ENV": "test",
            "APP_PORT": "8200",
            "DATABASE_URL": "postgresql://app:secret@localhost:5432/mapped",
            "MODEL_PROVIDER": "openai_responses",
            "MODEL_NAME": "gpt-5-mini",
            "TASK_WORKSPACE_ROOT": "/tmp/mapped-workspaces",
            "GMAIL_SECRET_MANAGER_URL": "file:///tmp/mapped-gmail-secrets",
            "CALENDAR_SECRET_MANAGER_URL": "file:///tmp/mapped-calendar-secrets",
            "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001",
            "RESPONSE_RATE_LIMIT_WINDOW_SECONDS": "75",
            "RESPONSE_RATE_LIMIT_MAX_REQUESTS": "10",
            "TELEGRAM_LINK_TTL_SECONDS": "700",
            "TELEGRAM_BOT_USERNAME": "alicebot_phase10",
            "TELEGRAM_WEBHOOK_SECRET": "secret-value",
            "TELEGRAM_BOT_TOKEN": "bot-token",
            "HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS": "90",
            "HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS": "9",
            "HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS": "600",
            "HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS": "14",
            "HOSTED_ABUSE_WINDOW_SECONDS": "1200",
            "HOSTED_ABUSE_BLOCK_THRESHOLD": "4",
            "HOSTED_RATE_LIMITS_ENABLED_BY_DEFAULT": "true",
            "HOSTED_ABUSE_CONTROLS_ENABLED_BY_DEFAULT": "true",
            "MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS": "360",
            "MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS": "8",
            "MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS": "420",
            "MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS": "12",
            "TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS": "90",
            "TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS": "180",
            "CORS_ALLOWED_ORIGINS": "https://app.example.com,https://staging.example.com",
            "CORS_ALLOWED_METHODS": "GET,POST,OPTIONS",
            "CORS_ALLOWED_HEADERS": "Authorization,Content-Type",
            "CORS_ALLOW_CREDENTIALS": "true",
            "CORS_PREFLIGHT_MAX_AGE_SECONDS": "900",
            "SECURITY_HEADERS_ENABLED": "false",
            "SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS": "86400",
            "SECURITY_HEADERS_HSTS_INCLUDE_SUBDOMAINS": "false",
            "TRUST_PROXY_HEADERS": "true",
            "TRUSTED_PROXY_IPS": "127.0.0.1,10.0.0.2",
            "ENTRYPOINT_RATE_LIMIT_BACKEND": "memory",
        }
    )

    assert settings.app_env == "test"
    assert settings.app_port == 8200
    assert settings.database_url == "postgresql://app:secret@localhost:5432/mapped"
    assert settings.model_provider == "openai_responses"
    assert settings.model_name == "gpt-5-mini"
    assert settings.task_workspace_root == "/tmp/mapped-workspaces"
    assert settings.gmail_secret_manager_url == "file:///tmp/mapped-gmail-secrets"
    assert settings.calendar_secret_manager_url == "file:///tmp/mapped-calendar-secrets"
    assert settings.auth_user_id == "00000000-0000-0000-0000-000000000001"
    assert settings.response_rate_limit_window_seconds == 75
    assert settings.response_rate_limit_max_requests == 10
    assert settings.telegram_link_ttl_seconds == 700
    assert settings.telegram_bot_username == "alicebot_phase10"
    assert settings.telegram_webhook_secret == "secret-value"
    assert settings.telegram_bot_token == "bot-token"
    assert settings.hosted_chat_rate_limit_window_seconds == 90
    assert settings.hosted_chat_rate_limit_max_requests == 9
    assert settings.hosted_scheduler_rate_limit_window_seconds == 600
    assert settings.hosted_scheduler_rate_limit_max_requests == 14
    assert settings.hosted_abuse_window_seconds == 1200
    assert settings.hosted_abuse_block_threshold == 4
    assert settings.hosted_rate_limits_enabled_by_default is True
    assert settings.hosted_abuse_controls_enabled_by_default is True
    assert settings.magic_link_start_rate_limit_window_seconds == 360
    assert settings.magic_link_start_rate_limit_max_requests == 8
    assert settings.magic_link_verify_rate_limit_window_seconds == 420
    assert settings.magic_link_verify_rate_limit_max_requests == 12
    assert settings.telegram_webhook_rate_limit_window_seconds == 90
    assert settings.telegram_webhook_rate_limit_max_requests == 180
    assert settings.cors_allowed_origins == ("https://app.example.com", "https://staging.example.com")
    assert settings.cors_allowed_methods == ("GET", "POST", "OPTIONS")
    assert settings.cors_allowed_headers == ("Authorization", "Content-Type")
    assert settings.cors_allow_credentials is True
    assert settings.cors_preflight_max_age_seconds == 900
    assert settings.security_headers_enabled is False
    assert settings.security_headers_hsts_max_age_seconds == 86400
    assert settings.security_headers_hsts_include_subdomains is False
    assert settings.trust_proxy_headers is True
    assert settings.trusted_proxy_ips == ("127.0.0.1", "10.0.0.2")
    assert settings.entrypoint_rate_limit_backend == "memory"


def test_settings_raise_clear_error_for_invalid_integer_values() -> None:
    with pytest.raises(ValueError, match="APP_PORT must be an integer"):
        Settings.from_env({"APP_PORT": "not-an-integer"})

    with pytest.raises(ValueError, match="MODEL_TIMEOUT_SECONDS must be an integer"):
        Settings.from_env({"MODEL_TIMEOUT_SECONDS": "not-an-integer"})

    with pytest.raises(ValueError, match="RESPONSE_RATE_LIMIT_MAX_REQUESTS must be an integer"):
        Settings.from_env({"RESPONSE_RATE_LIMIT_MAX_REQUESTS": "not-an-integer"})


def test_settings_reject_invalid_auth_user_id() -> None:
    with pytest.raises(ValueError, match="ALICEBOT_AUTH_USER_ID must be a valid UUID"):
        Settings.from_env({"ALICEBOT_AUTH_USER_ID": "not-a-uuid"})


def test_settings_reject_non_positive_rate_limit_values() -> None:
    with pytest.raises(
        ValueError,
        match="RESPONSE_RATE_LIMIT_WINDOW_SECONDS must be a positive integer",
    ):
        Settings.from_env({"RESPONSE_RATE_LIMIT_WINDOW_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="RESPONSE_RATE_LIMIT_MAX_REQUESTS must be a positive integer",
    ):
        Settings.from_env({"RESPONSE_RATE_LIMIT_MAX_REQUESTS": "0"})

    with pytest.raises(
        ValueError,
        match="TELEGRAM_LINK_TTL_SECONDS must be a positive integer",
    ):
        Settings.from_env({"TELEGRAM_LINK_TTL_SECONDS": "0"})

    with pytest.raises(ValueError, match="TELEGRAM_BOT_USERNAME must be provided"):
        Settings.from_env({"TELEGRAM_BOT_USERNAME": "   "})

    with pytest.raises(
        ValueError,
        match="HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS must be a positive integer",
    ):
        Settings.from_env({"HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS must be a positive integer",
    ):
        Settings.from_env({"HOSTED_CHAT_RATE_LIMIT_MAX_REQUESTS": "0"})

    with pytest.raises(
        ValueError,
        match="HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS must be a positive integer",
    ):
        Settings.from_env({"HOSTED_SCHEDULER_RATE_LIMIT_WINDOW_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS must be a positive integer",
    ):
        Settings.from_env({"HOSTED_SCHEDULER_RATE_LIMIT_MAX_REQUESTS": "0"})

    with pytest.raises(
        ValueError,
        match="HOSTED_ABUSE_WINDOW_SECONDS must be a positive integer",
    ):
        Settings.from_env({"HOSTED_ABUSE_WINDOW_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="HOSTED_ABUSE_BLOCK_THRESHOLD must be a positive integer",
    ):
        Settings.from_env({"HOSTED_ABUSE_BLOCK_THRESHOLD": "0"})

    with pytest.raises(
        ValueError,
        match="MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS must be a positive integer",
    ):
        Settings.from_env({"MAGIC_LINK_START_RATE_LIMIT_WINDOW_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS must be a positive integer",
    ):
        Settings.from_env({"MAGIC_LINK_START_RATE_LIMIT_MAX_REQUESTS": "0"})

    with pytest.raises(
        ValueError,
        match="MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS must be a positive integer",
    ):
        Settings.from_env({"MAGIC_LINK_VERIFY_RATE_LIMIT_WINDOW_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS must be a positive integer",
    ):
        Settings.from_env({"MAGIC_LINK_VERIFY_RATE_LIMIT_MAX_REQUESTS": "0"})

    with pytest.raises(
        ValueError,
        match="TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS must be a positive integer",
    ):
        Settings.from_env({"TELEGRAM_WEBHOOK_RATE_LIMIT_WINDOW_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS must be a positive integer",
    ):
        Settings.from_env({"TELEGRAM_WEBHOOK_RATE_LIMIT_MAX_REQUESTS": "0"})

    with pytest.raises(
        ValueError,
        match="CORS_PREFLIGHT_MAX_AGE_SECONDS must be a positive integer",
    ):
        Settings.from_env({"CORS_PREFLIGHT_MAX_AGE_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="CORS_ALLOWED_METHODS must include at least one method",
    ):
        Settings.from_env({"CORS_ALLOWED_METHODS": "   "})

    with pytest.raises(
        ValueError,
        match="SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS must be a positive integer",
    ):
        Settings.from_env({"SECURITY_HEADERS_HSTS_MAX_AGE_SECONDS": "0"})

    with pytest.raises(
        ValueError,
        match="ENTRYPOINT_RATE_LIMIT_BACKEND must be either 'redis' or 'memory'",
    ):
        Settings.from_env({"ENTRYPOINT_RATE_LIMIT_BACKEND": "invalid"})

    with pytest.raises(
        ValueError,
        match="TRUSTED_PROXY_IPS must include at least one IP when TRUST_PROXY_HEADERS is enabled",
    ):
        Settings.from_env({"TRUST_PROXY_HEADERS": "true"})


def test_settings_require_hardened_non_dev_configuration() -> None:
    with pytest.raises(
        ValueError,
        match="ALICEBOT_AUTH_USER_ID must be configured outside development/test environments",
    ):
        Settings.from_env({"APP_ENV": "staging"})

    with pytest.raises(ValueError, match="DATABASE_URL must be overridden outside development/test environments"):
        Settings.from_env(
            {
                "APP_ENV": "staging",
                "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001",
            }
        )

    with pytest.raises(
        ValueError,
        match="TELEGRAM_WEBHOOK_SECRET must be configured outside development/test environments",
    ):
        Settings.from_env(
            {
                "APP_ENV": "staging",
                "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001",
                "DATABASE_URL": "postgresql://secure-app:secret@localhost:5432/alicebot_secure",
                "DATABASE_ADMIN_URL": "postgresql://secure-admin:secret@localhost:5432/alicebot_secure",
                "S3_ACCESS_KEY": "secure-access",
                "S3_SECRET_KEY": "secure-secret",
            }
        )

    with pytest.raises(
        ValueError,
        match="CORS_ALLOWED_ORIGINS cannot include wildcard outside development/test environments",
    ):
        Settings.from_env(
            {
                "APP_ENV": "staging",
                "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001",
                "DATABASE_URL": "postgresql://secure-app:secret@localhost:5432/alicebot_secure",
                "DATABASE_ADMIN_URL": "postgresql://secure-admin:secret@localhost:5432/alicebot_secure",
                "S3_ACCESS_KEY": "secure-access",
                "S3_SECRET_KEY": "secure-secret",
                "TELEGRAM_WEBHOOK_SECRET": "secure-webhook-secret",
                "CORS_ALLOWED_ORIGINS": "*",
            }
        )
