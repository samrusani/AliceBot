from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from alicebot_api.config import Settings
from alicebot_api.provider_secrets import (
    build_provider_secret_ref,
    encode_provider_secret_ref,
    resolve_provider_api_key,
    write_provider_api_key,
)


def test_provider_secret_round_trip(tmp_path: Path) -> None:
    settings = Settings(provider_secret_manager_url=f"file://{tmp_path}")
    secret_ref = build_provider_secret_ref(workspace_id=uuid4())
    write_provider_api_key(
        settings=settings,
        secret_ref=secret_ref,
        api_key="provider-secret-key",
    )

    resolved = resolve_provider_api_key(
        settings=settings,
        api_key_field=encode_provider_secret_ref(secret_ref=secret_ref),
    )

    assert resolved == "provider-secret-key"


def test_provider_secret_resolution_allows_legacy_plaintext_keys() -> None:
    settings = Settings()

    resolved = resolve_provider_api_key(
        settings=settings,
        api_key_field="legacy-plaintext-key",
    )

    assert resolved == "legacy-plaintext-key"
