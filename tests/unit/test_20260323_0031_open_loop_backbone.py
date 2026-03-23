from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260323_0031_open_loop_backbone"


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
        "ALTER TABLE open_loops ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE open_loops FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_open_loop_status_domain_matches_sprint_contract() -> None:
    module = load_migration_module()

    assert module.OPEN_LOOP_STATUSES == ("open", "resolved", "dismissed")
