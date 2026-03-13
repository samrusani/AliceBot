from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260313_0015_execution_budget_lifecycle"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == list(module._UPGRADE_STATEMENTS)


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_execution_budget_lifecycle_privileges_stay_narrow() -> None:
    module = load_migration_module()

    assert module._UPGRADE_STATEMENTS[-1] == "GRANT SELECT, INSERT, UPDATE ON execution_budgets TO alicebot_app"
