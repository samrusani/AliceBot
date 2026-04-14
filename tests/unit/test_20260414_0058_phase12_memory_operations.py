from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260414_0058_phase12_memory_operations"


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
        "ALTER TABLE memory_operation_candidates ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE memory_operation_candidates FORCE ROW LEVEL SECURITY",
        "ALTER TABLE memory_operations ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE memory_operations FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_memory_operation_tables_have_expected_permissions() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT, UPDATE ON memory_operation_candidates TO alicebot_app",
        "GRANT SELECT, INSERT ON memory_operations TO alicebot_app",
    )


def test_memory_operation_schema_mentions_candidate_and_operation_audit_columns() -> None:
    module = load_migration_module()
    joined_upgrade_sql = module._UPGRADE_SCHEMA_STATEMENT

    for table_name in ("memory_operation_candidates", "memory_operations"):
        assert table_name in joined_upgrade_sql
    for column_name in (
        "sync_fingerprint",
        "source_candidate_id",
        "candidate_payload",
        "operation_type",
        "policy_action",
        "target_snapshot",
        "applied_operation_id",
        "correction_event_id",
        "before_snapshot",
        "after_snapshot",
        "details",
    ):
        assert column_name in joined_upgrade_sql
