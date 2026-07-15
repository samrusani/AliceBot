from __future__ import annotations

import pytest

from alicebot_api.config import Settings, get_runtime_settings


def test_settings_defaults(monkeypatch):
    for key in (
        "APP_ENV",
        "APP_HOST",
        "APP_PORT",
        "APP_LOG_MODE",
        "APP_LOG_LEVEL",
        "APP_LOG_PATH",
        "APP_LOG_MAX_BYTES",
        "APP_LOG_BACKUP_COUNT",
        "APP_ACCESS_LOG",
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
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    assert settings.app_env == "development"
    assert settings.app_port == 8000
    assert settings.app_log_mode == "stdout"
    assert settings.app_log_level == "INFO"
    assert settings.app_log_path == ""
    assert settings.app_log_max_bytes == 10 * 1024 * 1024
    assert settings.app_log_backup_count == 5
    assert settings.app_access_log is True
    assert settings.database_url.endswith("/alicebot")
    assert settings.database_admin_url.endswith("/alicebot")
    assert settings.s3_bucket == "alicebot-local"
    assert settings.model_provider == "openai_responses"
    assert settings.model_base_url == "https://api.openai.com/v1"
    assert settings.model_name == "gpt-5-mini"
    assert settings.model_timeout_seconds == 30
    assert settings.task_workspace_root == "/tmp/alicebot/task-workspaces"
    assert settings.workspace_provider_configs == ()
    assert settings.gmail_secret_manager_url == ""
    assert settings.calendar_secret_manager_url == ""
    assert settings.auth_user_id == ""
    assert settings.cors_allowed_origins == ()
    assert settings.cors_allowed_methods == ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
    assert settings.cors_allowed_headers == (
        "Authorization",
        "Content-Type",
        "X-AliceBot-User-Id",
    )
    assert settings.cors_allow_credentials is False
    assert settings.cors_preflight_max_age_seconds == 600
    assert settings.security_headers_enabled is True
    assert settings.security_headers_hsts_max_age_seconds == 31_536_000
    assert settings.security_headers_hsts_include_subdomains is True
    assert settings.trust_proxy_headers is False
    assert settings.trusted_proxy_ips == ()


def test_settings_honor_environment_overrides(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_PORT", "8100")
    monkeypatch.setenv("APP_LOG_MODE", "file")
    monkeypatch.setenv("APP_LOG_LEVEL", "debug")
    monkeypatch.setenv("APP_LOG_PATH", "/tmp/custom-logs/alicebot.log")
    monkeypatch.setenv("APP_LOG_MAX_BYTES", "2048")
    monkeypatch.setenv("APP_LOG_BACKUP_COUNT", "4")
    monkeypatch.setenv("APP_ACCESS_LOG", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:secret@localhost:5432/custom")
    monkeypatch.setenv("HEALTHCHECK_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("MODEL_NAME", "gpt-5")
    monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("TASK_WORKSPACE_ROOT", "/tmp/custom-workspaces")
    monkeypatch.setenv("GMAIL_SECRET_MANAGER_URL", "file:///tmp/custom-gmail-secrets")
    monkeypatch.setenv("CALENDAR_SECRET_MANAGER_URL", "file:///tmp/custom-calendar-secrets")
    monkeypatch.setenv("ALICEBOT_AUTH_USER_ID", "00000000-0000-0000-0000-000000000001")
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

    settings = Settings.from_env()

    assert settings.app_env == "test"
    assert settings.app_port == 8100
    assert settings.app_log_mode == "file"
    assert settings.app_log_level == "DEBUG"
    assert settings.app_log_path == "/tmp/custom-logs/alicebot.log"
    assert settings.app_log_max_bytes == 2048
    assert settings.app_log_backup_count == 4
    assert settings.app_access_log is False
    assert settings.database_url == "postgresql://app:secret@localhost:5432/custom"
    assert settings.healthcheck_timeout_seconds == 9
    assert settings.model_base_url == "https://example.test/v1"
    assert settings.model_name == "gpt-5"
    assert settings.model_timeout_seconds == 45
    assert settings.task_workspace_root == "/tmp/custom-workspaces"
    assert settings.workspace_provider_configs == ()
    assert settings.gmail_secret_manager_url == "file:///tmp/custom-gmail-secrets"
    assert settings.calendar_secret_manager_url == "file:///tmp/custom-calendar-secrets"
    assert settings.auth_user_id == "00000000-0000-0000-0000-000000000001"
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


def test_settings_can_be_loaded_from_an_explicit_environment_mapping() -> None:
    settings = Settings.from_env(
        {
            "APP_ENV": "test",
            "APP_PORT": "8200",
            "APP_LOG_MODE": "file",
            "APP_LOG_LEVEL": "warning",
            "APP_LOG_PATH": "/tmp/mapped-logs/alicebot.log",
            "APP_LOG_MAX_BYTES": "4096",
            "APP_LOG_BACKUP_COUNT": "2",
            "APP_ACCESS_LOG": "false",
            "DATABASE_URL": "postgresql://app:secret@localhost:5432/mapped",
            "MODEL_PROVIDER": "openai_responses",
            "MODEL_NAME": "gpt-5-mini",
            "TASK_WORKSPACE_ROOT": "/tmp/mapped-workspaces",
            "WORKSPACE_PROVIDER_CONFIGS_JSON": (
                '[{"display_name":"Configured OpenAI",'
                '"base_url":"https://provider.example/v1",'
                '"api_key":"provider-secret-key",'
                '"default_model":"gpt-5-mini"}]'
            ),
            "GMAIL_SECRET_MANAGER_URL": "file:///tmp/mapped-gmail-secrets",
            "CALENDAR_SECRET_MANAGER_URL": "file:///tmp/mapped-calendar-secrets",
            "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001",
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
        }
    )

    assert settings.app_env == "test"
    assert settings.app_port == 8200
    assert settings.app_log_mode == "file"
    assert settings.app_log_level == "WARNING"
    assert settings.app_log_path == "/tmp/mapped-logs/alicebot.log"
    assert settings.app_log_max_bytes == 4096
    assert settings.app_log_backup_count == 2
    assert settings.app_access_log is False
    assert settings.database_url == "postgresql://app:secret@localhost:5432/mapped"
    assert settings.model_provider == "openai_responses"
    assert settings.model_name == "gpt-5-mini"
    assert settings.task_workspace_root == "/tmp/mapped-workspaces"
    assert len(settings.workspace_provider_configs) == 1
    assert settings.workspace_provider_configs[0].display_name == "Configured OpenAI"
    assert settings.workspace_provider_configs[0].provider_key == "openai_compatible"
    assert settings.gmail_secret_manager_url == "file:///tmp/mapped-gmail-secrets"
    assert settings.calendar_secret_manager_url == "file:///tmp/mapped-calendar-secrets"
    assert settings.auth_user_id == "00000000-0000-0000-0000-000000000001"
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


def test_settings_raise_clear_error_for_invalid_integer_values() -> None:
    with pytest.raises(ValueError, match="APP_PORT must be an integer"):
        Settings.from_env({"APP_PORT": "not-an-integer"})

    with pytest.raises(ValueError, match="MODEL_TIMEOUT_SECONDS must be an integer"):
        Settings.from_env({"MODEL_TIMEOUT_SECONDS": "not-an-integer"})



@pytest.mark.parametrize(
    "key",
    [
        "APP_ACCESS_LOG",
        "CORS_ALLOW_CREDENTIALS",
        "SECURITY_HEADERS_ENABLED",
        "TRUST_PROXY_HEADERS",
    ],
)
def test_settings_reject_unknown_boolean_tokens(key: str) -> None:
    with pytest.raises(ValueError, match=rf"{key} must be a boolean"):
        Settings.from_env({key: "definitely"})


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"APP_PORT": "0"}, "APP_PORT must be between 1 and 65535"),
        ({"APP_PORT": "65536"}, "APP_PORT must be between 1 and 65535"),
        (
            {"HEALTHCHECK_TIMEOUT_SECONDS": "0"},
            "HEALTHCHECK_TIMEOUT_SECONDS must be a positive integer",
        ),
        (
            {"MODEL_TIMEOUT_SECONDS": "0"},
            "MODEL_TIMEOUT_SECONDS must be a positive integer",
        ),
    ],
)
def test_settings_reject_invalid_ports_and_timeouts(
    env: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Settings.from_env(env)


def test_scoped_runtime_settings_can_skip_unrelated_hosted_requirements() -> None:
    settings = Settings.from_env(
        {
            "APP_ENV": "production",
            "DATABASE_URL": "postgresql://app:secret@db/alice",
            "ALICEBOT_AUTH_USER_ID": "11111111-1111-4111-8111-111111111111",
        },
        require_production_services=False,
    )

    assert settings.app_env == "production"
    assert settings.database_url == "postgresql://app:secret@db/alice"


def test_runtime_settings_use_environment_without_hosted_production_requirements(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://runtime:secret@db/alice")
    monkeypatch.setenv(
        "ALICEBOT_AUTH_USER_ID",
        "11111111-1111-4111-8111-111111111111",
    )
    for key in (
        "DATABASE_ADMIN_URL",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "TELEGRAM_WEBHOOK_SECRET",
        "WORKSPACE_PROVIDER_CONFIGS_JSON",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = get_runtime_settings()

    assert settings.app_env == "production"
    assert settings.database_url == "postgresql://runtime:secret@db/alice"


def test_settings_reject_invalid_auth_user_id() -> None:
    with pytest.raises(ValueError, match="ALICEBOT_AUTH_USER_ID must be a valid UUID"):
        Settings.from_env({"ALICEBOT_AUTH_USER_ID": "not-a-uuid"})


def test_settings_reject_invalid_logging_configuration() -> None:
    with pytest.raises(ValueError, match="APP_LOG_MODE must be either 'stdout' or 'file'"):
        Settings.from_env({"APP_LOG_MODE": "stderr"})

    with pytest.raises(
        ValueError,
        match="APP_LOG_LEVEL must be one of CRITICAL, ERROR, WARNING, INFO, or DEBUG",
    ):
        Settings.from_env({"APP_LOG_LEVEL": "TRACE"})

    with pytest.raises(ValueError, match="APP_LOG_MAX_BYTES must be a positive integer"):
        Settings.from_env({"APP_LOG_MAX_BYTES": "0"})

    with pytest.raises(ValueError, match="APP_LOG_BACKUP_COUNT must be a positive integer"):
        Settings.from_env({"APP_LOG_BACKUP_COUNT": "0"})

    with pytest.raises(
        ValueError,
        match="APP_LOG_PATH must be configured when APP_LOG_MODE is 'file'",
    ):
        Settings.from_env({"APP_LOG_MODE": "file"})


def test_settings_reject_invalid_workspace_provider_configs_json() -> None:
    with pytest.raises(ValueError, match="WORKSPACE_PROVIDER_CONFIGS_JSON must be valid JSON"):
        Settings.from_env({"WORKSPACE_PROVIDER_CONFIGS_JSON": "not-json"})

    with pytest.raises(
        ValueError,
        match="WORKSPACE_PROVIDER_CONFIGS_JSON\\[0\\]\\.api_key is required when auth_mode is bearer",
    ):
        Settings.from_env(
            {
                "WORKSPACE_PROVIDER_CONFIGS_JSON": (
                    '[{"display_name":"Configured OpenAI",'
                    '"base_url":"https://provider.example/v1",'
                    '"default_model":"gpt-5-mini"}]'
                )
            }
        )


def test_settings_accept_vllm_workspace_provider_config_defaults() -> None:
    settings = Settings.from_env(
        {
            "WORKSPACE_PROVIDER_CONFIGS_JSON": (
                '[{"provider_key":"vllm",'
                '"display_name":"Configured vLLM",'
                '"base_url":"http://127.0.0.1:8001",'
                '"default_model":"mistral-small-instruct"}]'
            )
        }
    )

    assert len(settings.workspace_provider_configs) == 1
    provider = settings.workspace_provider_configs[0]
    assert provider.provider_key == "vllm"
    assert provider.auth_mode == "none"
    assert provider.model_list_path == "/v1/models"
    assert provider.healthcheck_path == "/health"
    assert provider.invoke_path == "/v1/chat/completions"


def test_removed_hosted_and_telegram_settings_are_not_loaded() -> None:
    settings = Settings.from_env(
        {
            "TELEGRAM_BOT_TOKEN": "must-not-be-loaded",
            "TELEGRAM_WEBHOOK_SECRET": "must-not-be-loaded",
            "HOSTED_CHAT_RATE_LIMIT_WINDOW_SECONDS": "1",
        }
    )

    assert not hasattr(settings, "telegram_bot_token")
    assert not hasattr(settings, "telegram_webhook_secret")
    assert not hasattr(settings, "hosted_chat_rate_limit_window_seconds")


def test_settings_reject_invalid_deployment_limits() -> None:
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
        match="CORS_ALLOWED_ORIGINS cannot include wildcard outside development/test environments",
    ):
        Settings.from_env(
            {
                "APP_ENV": "staging",
                "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001",
                "DATABASE_URL": "postgresql://secure-app:secret@localhost:5432/alicebot_secure",
                "DATABASE_ADMIN_URL": "postgresql://secure-admin:secret@localhost:5432/alicebot_secure",
                "CORS_ALLOWED_ORIGINS": "*",
            }
        )


@pytest.mark.parametrize(
    "s3_environment",
    [
        {},
        {
            "S3_ACCESS_KEY": "alicebot",
            "S3_SECRET_KEY": "alicebot-secret",
        },
    ],
)
def test_core_only_production_settings_boot_without_s3_credentials(
    s3_environment: dict[str, str],
) -> None:
    settings = Settings.from_env(
        {
            "APP_ENV": "production",
            "ALICEBOT_AUTH_USER_ID": "00000000-0000-4000-8000-000000000001",
            "DATABASE_URL": "postgresql://secure-app:secret@db/alicebot",
            "DATABASE_ADMIN_URL": "postgresql://secure-admin:secret@db/alicebot",
            "CORS_ALLOWED_ORIGINS": "https://alice.example",
            **s3_environment,
        }
    )

    assert settings.app_env == "production"
    assert settings.s3_access_key == "alicebot"
    assert settings.s3_secret_key == "alicebot-secret"
