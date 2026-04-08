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
