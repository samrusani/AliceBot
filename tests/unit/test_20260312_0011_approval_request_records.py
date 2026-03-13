from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260312_0011_approval_request_records"


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
        "ALTER TABLE approvals ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE approvals FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_approvals_privileges_stay_narrow() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT ON approvals TO alicebot_app",
    )
