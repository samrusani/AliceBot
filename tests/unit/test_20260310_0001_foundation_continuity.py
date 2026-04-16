from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260310_0001_foundation_continuity"


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
        "ALTER TABLE users ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE users FORCE ROW LEVEL SECURITY",
        "ALTER TABLE threads ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE threads FORCE ROW LEVEL SECURITY",
        "ALTER TABLE sessions ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE sessions FORCE ROW LEVEL SECURITY",
        "ALTER TABLE events ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE events FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_base_downgrade_does_not_drop_global_extensions() -> None:
    module = load_migration_module()

    assert "DROP EXTENSION IF EXISTS vector" not in module._DOWNGRADE_STATEMENTS
    assert "DROP EXTENSION IF EXISTS pgcrypto" not in module._DOWNGRADE_STATEMENTS


def test_base_schema_does_not_create_redundant_events_sequence_index() -> None:
    module = load_migration_module()

    assert "CREATE INDEX events_thread_sequence_idx" not in module._UPGRADE_SCHEMA_STATEMENT


def test_base_schema_keeps_thread_created_index_for_deterministic_review_queries() -> None:
    module = load_migration_module()

    assert "CREATE INDEX threads_user_created_idx" in module._UPGRADE_SCHEMA_STATEMENT


def test_row_level_security_statements_cover_enable_and_force_modes() -> None:
    module = load_migration_module()

    assert module._row_level_security_statements("users") == (
        "ALTER TABLE users ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE users FORCE ROW LEVEL SECURITY",
    )
