from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260408_0046_phase10_daily_brief_notifications"


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


def test_migration_adds_phase10_s4_tables_and_scheduler_receipt_fields() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    assert "CREATE TABLE notification_subscriptions" in joined_upgrade_sql
    assert "CREATE TABLE continuity_briefs" in joined_upgrade_sql
    assert "CREATE TABLE daily_brief_jobs" in joined_upgrade_sql
    assert "ADD COLUMN scheduled_job_id uuid" in joined_upgrade_sql
    assert "ADD COLUMN scheduler_job_kind text" in joined_upgrade_sql
    assert "ADD COLUMN scheduled_for timestamptz" in joined_upgrade_sql
    assert "ADD COLUMN schedule_slot text" in joined_upgrade_sql
    assert "ADD COLUMN notification_policy jsonb" in joined_upgrade_sql
    assert "UNIQUE (workspace_id, channel_type, idempotency_key)" in joined_upgrade_sql


def test_migration_extends_delivery_receipt_status_for_policy_suppression() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    assert "status IN ('delivered', 'failed', 'simulated', 'suppressed')" in joined_upgrade_sql
    assert "scheduler_job_kind IN ('daily_brief', 'open_loop_prompt')" in joined_upgrade_sql
