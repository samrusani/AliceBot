from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260323_0030_typed_memory_backbone"


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


def test_memory_type_and_confirmation_status_domains_match_sprint_contract() -> None:
    module = load_migration_module()

    assert module.MEMORY_TYPES == (
        "preference",
        "identity_fact",
        "relationship_fact",
        "project_fact",
        "decision",
        "commitment",
        "routine",
        "constraint",
        "working_style",
    )
    assert module.MEMORY_CONFIRMATION_STATUSES == (
        "unconfirmed",
        "confirmed",
        "contested",
    )
