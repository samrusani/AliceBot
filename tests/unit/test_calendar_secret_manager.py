from __future__ import annotations

import pytest

from alicebot_api.calendar_secret_manager import (
    CalendarSecretManagerError,
    build_calendar_secret_manager,
)


def test_build_calendar_secret_manager_rejects_non_file_schemes() -> None:
    with pytest.raises(ValueError, match="CALENDAR_SECRET_MANAGER_URL must use the file:// scheme"):
        build_calendar_secret_manager("memory://calendar-secrets")


def test_build_calendar_secret_manager_requires_explicit_configuration() -> None:
    with pytest.raises(ValueError, match="CALENDAR_SECRET_MANAGER_URL must be configured"):
        build_calendar_secret_manager("")


def test_file_calendar_secret_manager_round_trips_secret_payload(tmp_path) -> None:
    manager = build_calendar_secret_manager(tmp_path.resolve().as_uri())
    secret_ref = "users/00000000-0000-0000-0000-000000000001/calendar-account-credentials/cred.json"
    payload = {
        "credential_kind": "calendar_oauth_access_token_v1",
        "access_token": "token-001",
    }

    manager.write_secret(secret_ref=secret_ref, payload=payload)

    assert manager.load_secret(secret_ref=secret_ref) == payload


def test_file_calendar_secret_manager_rejects_missing_or_escaped_refs(tmp_path) -> None:
    manager = build_calendar_secret_manager(tmp_path.resolve().as_uri())

    with pytest.raises(CalendarSecretManagerError, match="was not found"):
        manager.load_secret(secret_ref="users/u/calendar-account-credentials/missing.json")

    with pytest.raises(CalendarSecretManagerError, match="outside the configured root"):
        manager.write_secret(
            secret_ref="../../escape.json",
            payload={"credential_kind": "calendar_oauth_access_token_v1", "access_token": "token"},
        )
