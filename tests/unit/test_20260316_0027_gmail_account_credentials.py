from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260316_0027_gmail_account_credentials"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        module._UPGRADE_SCHEMA_STATEMENT,
        module._UPGRADE_BACKFILL_STATEMENT,
        *module._UPGRADE_DROP_PLAINTEXT_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE gmail_account_credentials ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE gmail_account_credentials FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == [
        *module._DOWNGRADE_ADD_PLAINTEXT_STATEMENTS,
        module._DOWNGRADE_BACKFILL_STATEMENT,
        *module._DOWNGRADE_RESTORE_CONSTRAINT_STATEMENTS,
    ]


def test_gmail_account_credential_privileges_allow_only_expected_runtime_writes() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT ON gmail_account_credentials TO alicebot_app",
    )
