from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260313_0013_tool_executions"


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
        "ALTER TABLE tool_executions ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE tool_executions FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_tool_executions_privileges_stay_narrow() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT ON tool_executions TO alicebot_app",
    )
