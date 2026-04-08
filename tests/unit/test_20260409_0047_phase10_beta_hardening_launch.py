from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260409_0047_phase10_beta_hardening_launch"


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


def test_migration_adds_chat_telemetry_and_evidence_fields() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    assert "CREATE TABLE chat_telemetry" in joined_upgrade_sql
    assert "ADD COLUMN support_status text" in joined_upgrade_sql
    assert "ADD COLUMN rollout_evidence jsonb" in joined_upgrade_sql
    assert "ADD COLUMN rate_limit_evidence jsonb" in joined_upgrade_sql
    assert "ADD COLUMN incident_evidence jsonb" in joined_upgrade_sql
    assert "ALTER TABLE channel_delivery_receipts" in joined_upgrade_sql
    assert "ALTER TABLE daily_brief_jobs" in joined_upgrade_sql


def test_migration_seeds_phase10_s5_rollout_flags() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    assert "hosted_admin_read" in joined_upgrade_sql
    assert "hosted_admin_operator" in joined_upgrade_sql
    assert "hosted_chat_handle_enabled" in joined_upgrade_sql
    assert "hosted_scheduler_delivery_enabled" in joined_upgrade_sql
    assert "hosted_abuse_controls_enabled" in joined_upgrade_sql
    assert "hosted_rate_limits_enabled" in joined_upgrade_sql
    assert "'p10-ops'" in joined_upgrade_sql
