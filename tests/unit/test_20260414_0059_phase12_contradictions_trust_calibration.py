from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260414_0059_phase12_contradictions_trust_calibration"


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
        "ALTER TABLE contradiction_cases ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE contradiction_cases FORCE ROW LEVEL SECURITY",
        "ALTER TABLE trust_signals ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE trust_signals FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_phase12_contradiction_schema_mentions_expected_tables_and_constraints() -> None:
    module = load_migration_module()
    joined_upgrade_sql = module._UPGRADE_SCHEMA_STATEMENT

    for table_name in ("contradiction_cases", "trust_signals"):
        assert table_name in joined_upgrade_sql
    for column_name in (
        "canonical_key",
        "continuity_object_id",
        "counterpart_object_id",
        "detection_payload",
        "resolution_action",
        "signal_key",
        "signal_type",
        "signal_state",
        "direction",
        "magnitude",
        "contradiction_case_id",
    ):
        assert column_name in joined_upgrade_sql
