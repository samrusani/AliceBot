from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260325_0035_policy_agent_profile_scope"


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


def test_policy_profile_scope_upgrade_contract() -> None:
    module = load_migration_module()

    assert "ADD COLUMN agent_profile_id text NULL" in module._UPGRADE_STATEMENTS[0]
    assert "policies_agent_profile_id_fkey" in module._UPGRADE_STATEMENTS[1]
    assert "FOREIGN KEY (agent_profile_id)" in module._UPGRADE_STATEMENTS[1]
    assert "REFERENCES agent_profiles(id)" in module._UPGRADE_STATEMENTS[1]
    assert "DROP INDEX IF EXISTS policies_user_active_priority_created_idx" in module._UPGRADE_STATEMENTS[2]
    assert "policies_user_active_profile_priority_created_idx" in module._UPGRADE_STATEMENTS[3]
    assert "(user_id, active, agent_profile_id, priority, created_at, id)" in module._UPGRADE_STATEMENTS[3]


def test_policy_profile_scope_downgrade_contract() -> None:
    module = load_migration_module()

    assert "DROP INDEX IF EXISTS policies_user_active_profile_priority_created_idx" in module._DOWNGRADE_STATEMENTS[0]
    assert "DROP CONSTRAINT IF EXISTS policies_agent_profile_id_fkey" in module._DOWNGRADE_STATEMENTS[1]
    assert "DROP COLUMN IF EXISTS agent_profile_id" in module._DOWNGRADE_STATEMENTS[2]
    assert "CREATE INDEX policies_user_active_priority_created_idx" in module._DOWNGRADE_STATEMENTS[3]
    assert "(user_id, active, priority, created_at, id)" in module._DOWNGRADE_STATEMENTS[3]
