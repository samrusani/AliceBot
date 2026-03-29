from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260330_0042_phase5_continuity_corrections"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_BOOTSTRAP_STATEMENTS,
        *module._UPGRADE_SCHEMA_STATEMENTS,
        *module._UPGRADE_TRIGGER_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE continuity_correction_events ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE continuity_correction_events FORCE ROW LEVEL SECURITY",
        *module._UPGRADE_POLICY_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_domains_match_sprint_contract() -> None:
    module = load_migration_module()

    assert module.CONTINUITY_CORRECTION_ACTIONS == (
        "confirm",
        "edit",
        "delete",
        "supersede",
        "mark_stale",
    )
    assert module.CONTINUITY_OBJECT_STATUSES == (
        "active",
        "completed",
        "cancelled",
        "superseded",
        "stale",
        "deleted",
    )
