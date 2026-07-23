from __future__ import annotations

from pathlib import Path

from alicebot_api.vnext_secrets import (
    EnvironmentSecretProvider,
    InMemorySecretProvider,
    LocalEncryptedFileSecretProvider,
    redact_secret_fields,
    redact_secret_value,
)


def test_environment_secret_provider_resolves_env_refs_without_plain_storage(monkeypatch) -> None:
    monkeypatch.setenv("CONNECTOR_API_TOKEN", "provider-secret")
    provider = EnvironmentSecretProvider()

    assert provider.get_secret("env:CONNECTOR_API_TOKEN") == "provider-secret"
    assert provider.has_secret("env:CONNECTOR_API_TOKEN") is True
    assert provider.get_secret("connector.api_token.default") is None


def test_local_encrypted_file_secret_provider_round_trips_without_plaintext(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ALICE_VNEXT_SECRET_STORE_KEY", "test-key")
    store_path = tmp_path / "secrets.json"
    key_path = tmp_path / "local.key"
    provider = LocalEncryptedFileSecretProvider(path=store_path, key_path=key_path)

    provider.set_secret("connector.api_token.default", "provider-secret-value")

    assert provider.has_secret("connector.api_token.default") is True
    assert provider.get_secret("connector.api_token.default") == "provider-secret-value"
    assert "provider-secret-value" not in store_path.read_text(encoding="utf-8")


def test_in_memory_secret_provider_supports_mocked_connector_tests() -> None:
    provider = InMemorySecretProvider({"browser.capture_token.default": "clip-token"})

    assert provider.has_secret("browser.capture_token.default") is True
    assert provider.get_secret("browser.capture_token.default") == "clip-token"


def test_secret_redaction_recurses_through_payloads() -> None:
    redacted = redact_secret_fields(
        {
            "capture_token": "clip-token",
            "nested": {"provider_secret": "provider-token"},
            "items": [{"api_key": "abc"}],
            "safe": "visible",
        }
    )

    assert redacted == {
        "capture_token": "***",
        "nested": {"provider_secret": "***"},
        "items": [{"api_key": "***"}],
        "safe": "visible",
    }


def test_secret_value_redaction_removes_nested_values_keys_and_substrings() -> None:
    secret = "alice_clip_secret-value"

    redacted = redact_secret_value(
        {
            "url": f"https://example.test/article?cap={secret}",
            "nested": [{"title": f"before {secret} after"}],
            f"key-{secret}": secret,
            "safe": "visible",
        },
        secret,
    )

    assert redacted == {
        "url": "https://example.test/article?cap=***",
        "nested": [{"title": "before *** after"}],
        "key-***": "***",
        "safe": "visible",
    }
