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


def test_settings_raise_clear_error_for_invalid_integer_values() -> None:
    with pytest.raises(ValueError, match="APP_PORT must be an integer"):
        Settings.from_env({"APP_PORT": "not-an-integer"})

    with pytest.raises(ValueError, match="MODEL_TIMEOUT_SECONDS must be an integer"):
        Settings.from_env({"MODEL_TIMEOUT_SECONDS": "not-an-integer"})
