from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260408_0043_phase10_identity_workspace_bootstrap"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_migration_mentions_phase10_control_plane_tables() -> None:
    module = load_migration_module()

    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)
    for table_name in (
        "user_accounts",
        "auth_sessions",
        "magic_link_challenges",
        "devices",
        "device_link_challenges",
        "workspaces",
        "workspace_members",
        "user_preferences",
        "beta_cohorts",
        "feature_flags",
    ):
        assert table_name in joined_upgrade_sql


def test_migration_stores_challenge_tokens_hashed_at_rest() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    assert "challenge_token_hash text NOT NULL UNIQUE" in joined_upgrade_sql
    assert "challenge_token text NOT NULL UNIQUE" not in joined_upgrade_sql
