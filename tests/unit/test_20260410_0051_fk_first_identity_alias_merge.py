from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260410_0051_fk_first_identity_alias_merge"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE entity_aliases ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE entity_aliases FORCE ROW LEVEL SECURITY",
        "ALTER TABLE entity_merge_log ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE entity_merge_log FORCE ROW LEVEL SECURITY",
        *module._UPGRADE_POLICY_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_new_tables_stay_insert_select_only() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT ON entity_aliases TO alicebot_app",
        "GRANT SELECT, INSERT ON entity_merge_log TO alicebot_app",
    )
