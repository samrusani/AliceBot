from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260408_0045_phase10_chat_continuity_approvals"


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
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_migration_adds_chat_intent_result_fields_and_new_tables() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    assert "ADD COLUMN intent_payload jsonb" in joined_upgrade_sql
    assert "ADD COLUMN result_payload jsonb" in joined_upgrade_sql
    assert "ADD COLUMN handled_at timestamptz" in joined_upgrade_sql
    assert "CREATE TABLE approval_challenges" in joined_upgrade_sql
    assert "CREATE TABLE open_loop_reviews" in joined_upgrade_sql


def test_migration_extends_intent_routing_checks_for_phase10_s3() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    for marker in (
        "'capture'",
        "'recall'",
        "'resume'",
        "'correction'",
        "'open_loops'",
        "'open_loop_review'",
        "'approvals'",
        "'approval_approve'",
        "'approval_reject'",
        "'unknown'",
    ):
        assert marker in joined_upgrade_sql

    assert "('pending', 'recorded', 'handled', 'failed')" in joined_upgrade_sql
