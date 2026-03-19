from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260319_0030_calendar_accounts_and_credentials"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        module._UPGRADE_SCHEMA_STATEMENT,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE calendar_accounts ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE calendar_accounts FORCE ROW LEVEL SECURITY",
        "ALTER TABLE calendar_account_credentials ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE calendar_account_credentials FORCE ROW LEVEL SECURITY",
        *module._UPGRADE_POLICY_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_calendar_account_privileges_allow_only_expected_runtime_writes() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT ON calendar_accounts TO alicebot_app",
        "GRANT SELECT, INSERT ON calendar_account_credentials TO alicebot_app",
    )
