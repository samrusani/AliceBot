from __future__ import annotations

from pathlib import Path

from alicebot_api.config import Settings
import alicebot_api.main as main_module
from alicebot_api.routers import _api_shared as api_shared


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dead_entrypoint_rate_limiter_carrier_is_absent() -> None:
    carrier_paths = (
        "apps/api/src/alicebot_api/main.py",
        "apps/api/src/alicebot_api/routers/_api_shared.py",
        "apps/api/src/alicebot_api/config.py",
        ".env.example",
        ".env.lite.example",
        "scripts/api_dev.sh",
        "scripts/alice_lite_up.sh",
        "tests/integration/conftest.py",
    )
    combined = "\n".join(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for relative_path in carrier_paths
    )

    for retired_name in (
        "RESPONSE_RATE_LIMIT_WINDOW_SECONDS",
        "RESPONSE_RATE_LIMIT_MAX_REQUESTS",
        "ENTRYPOINT_RATE_LIMIT_BACKEND",
        "DEFAULT_RESPONSE_RATE_LIMIT_WINDOW_SECONDS",
        "DEFAULT_RESPONSE_RATE_LIMIT_MAX_REQUESTS",
        "DEFAULT_ENTRYPOINT_RATE_LIMIT_BACKEND",
        "ResponseRateLimiter",
        "response_rate_limiter",
        "EntrypointRateLimiter",
        "EntrypointRateLimiterUnavailableError",
        "entrypoint_rate_limiter",
        "_entrypoint_rate_limit_error",
        "_enforce_entrypoint_rate_limit",
        "entrypoint_rate:",
    ):
        assert retired_name not in combined


def test_settings_ignore_retired_entrypoint_rate_limit_environment() -> None:
    settings = Settings.from_env(
        {
            "ENTRYPOINT_RATE_LIMIT_BACKEND": "invalid-retired-value",
            "RESPONSE_RATE_LIMIT_WINDOW_SECONDS": "-1",
            "RESPONSE_RATE_LIMIT_MAX_REQUESTS": "-1",
        }
    )

    assert not hasattr(settings, "entrypoint_rate_limit_backend")
    assert not hasattr(settings, "response_rate_limit_window_seconds")
    assert not hasattr(settings, "response_rate_limit_max_requests")


def test_client_identifier_helper_remains_without_rate_limiter_carrier() -> None:
    assert callable(api_shared._request_client_identifier)
    assert main_module._request_client_identifier is api_shared._request_client_identifier
    assert not hasattr(main_module, "entrypoint_rate_limiter")
    assert not hasattr(main_module, "_enforce_entrypoint_rate_limit")
