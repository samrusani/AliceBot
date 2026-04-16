from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260416_0064_phase14_provider_model_pack_bindings"


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


def test_upgrade_adds_provider_binding_column_and_index() -> None:
    module = load_migration_module()
    ddl = "\n".join(module._UPGRADE_STATEMENTS)

    assert "ADD COLUMN provider_id uuid NULL" in ddl
    assert "REFERENCES model_providers(id) ON DELETE CASCADE" in ddl
    assert "workspace_model_pack_bindings_workspace_provider_created_idx" in ddl
