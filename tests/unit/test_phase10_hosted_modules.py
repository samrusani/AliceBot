from __future__ import annotations

import pytest

from alicebot_api.hosted_auth import hash_token, normalize_email
from alicebot_api.hosted_preferences import HostedPreferencesValidationError, validate_timezone
from alicebot_api.hosted_workspace import slugify_workspace_name


def test_normalize_email_and_hash_token_are_deterministic() -> None:
    assert normalize_email("  Builder@Example.COM ") == "builder@example.com"
    assert hash_token("phase10-token") == hash_token("phase10-token")
    assert len(hash_token("phase10-token")) == 64


def test_normalize_email_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="valid"):
        normalize_email("missing-at-symbol")


def test_slugify_workspace_name_collapses_symbols_and_whitespace() -> None:
    assert slugify_workspace_name("  Builder Workspace: Alpha / Beta  ") == "builder-workspace-alpha-beta"
    assert slugify_workspace_name("!!!") == "alice-workspace"


def test_validate_timezone_requires_known_zoneinfo_key() -> None:
    assert validate_timezone("Europe/Stockholm") == "Europe/Stockholm"
    with pytest.raises(HostedPreferencesValidationError, match="not recognized"):
        validate_timezone("Mars/Olympus")
