from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260311_0004_memory_admission"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_BOOTSTRAP_STATEMENTS,
        module._UPGRADE_SCHEMA_STATEMENT,
        module._UPGRADE_TRIGGER_STATEMENT,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE memories ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE memories FORCE ROW LEVEL SECURITY",
        "ALTER TABLE memory_revisions ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE memory_revisions FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_memory_table_privileges_stay_narrow() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT, UPDATE ON memories TO alicebot_app",
        "GRANT SELECT, INSERT ON memory_revisions TO alicebot_app",
    )
