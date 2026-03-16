from __future__ import annotations

import pytest

from alicebot_api.gmail_secret_manager import (
    GmailSecretManagerError,
    build_gmail_secret_manager,
)


def test_build_gmail_secret_manager_rejects_non_file_schemes() -> None:
    with pytest.raises(ValueError, match="GMAIL_SECRET_MANAGER_URL must use the file:// scheme"):
        build_gmail_secret_manager("memory://gmail-secrets")


def test_build_gmail_secret_manager_requires_explicit_configuration() -> None:
    with pytest.raises(ValueError, match="GMAIL_SECRET_MANAGER_URL must be configured"):
        build_gmail_secret_manager("")


def test_file_gmail_secret_manager_round_trips_secret_payload(tmp_path) -> None:
    manager = build_gmail_secret_manager(tmp_path.resolve().as_uri())
    secret_ref = "users/00000000-0000-0000-0000-000000000001/gmail-account-credentials/cred.json"
    payload = {
        "credential_kind": "gmail_oauth_access_token_v1",
        "access_token": "token-001",
    }

    manager.write_secret(secret_ref=secret_ref, payload=payload)

    assert manager.load_secret(secret_ref=secret_ref) == payload


def test_file_gmail_secret_manager_rejects_missing_or_escaped_refs(tmp_path) -> None:
    manager = build_gmail_secret_manager(tmp_path.resolve().as_uri())

    with pytest.raises(GmailSecretManagerError, match="was not found"):
        manager.load_secret(secret_ref="users/u/gmail-account-credentials/missing.json")

    with pytest.raises(GmailSecretManagerError, match="outside the configured root"):
        manager.write_secret(
            secret_ref="../../escape.json",
            payload={"credential_kind": "gmail_oauth_access_token_v1", "access_token": "token"},
        )
