from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260621_0071_procedure_memory_type"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_adds_procedure_to_memory_type_constraint(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == list(module._UPGRADE_STATEMENTS)
    assert "'procedure'" in executed[-1]


def test_downgrade_maps_procedure_to_semantic_before_restoring_constraint(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)
    assert executed[0] == "UPDATE memories SET memory_type = 'semantic' WHERE memory_type = 'procedure'"
    assert "'procedure'" not in executed[-1]
