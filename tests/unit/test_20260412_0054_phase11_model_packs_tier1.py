from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260412_0054_phase11_model_packs_tier1"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == list(module._UPGRADE_STATEMENTS) + list(module._UPGRADE_GRANT_STATEMENTS)


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_upgrade_adds_workspace_consistent_binding_constraint() -> None:
    module = load_migration_module()
    ddl = "\n".join(module._UPGRADE_STATEMENTS)
    assert "FOREIGN KEY (model_pack_id, workspace_id)" in ddl
    assert "REFERENCES model_packs(id, workspace_id)" in ddl


def test_upgrade_adds_model_pack_workspace_composite_unique() -> None:
    module = load_migration_module()
    ddl = "\n".join(module._UPGRADE_STATEMENTS)
    assert "UNIQUE (id, workspace_id)" in ddl
