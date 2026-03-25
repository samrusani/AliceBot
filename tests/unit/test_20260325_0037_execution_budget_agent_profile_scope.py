from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260325_0037_execution_budget_agent_profile_scope"


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


def test_execution_budget_profile_scope_upgrade_contract() -> None:
    module = load_migration_module()

    assert "ADD COLUMN agent_profile_id text NULL" in module._UPGRADE_STATEMENTS[0]
    assert "execution_budgets_agent_profile_id_fkey" in module._UPGRADE_STATEMENTS[1]
    assert "FOREIGN KEY (agent_profile_id)" in module._UPGRADE_STATEMENTS[1]
    assert "REFERENCES agent_profiles(id)" in module._UPGRADE_STATEMENTS[1]
    assert "DROP INDEX IF EXISTS execution_budgets_user_match_idx" in module._UPGRADE_STATEMENTS[2]
    assert "DROP INDEX IF EXISTS execution_budgets_one_active_scope_idx" in module._UPGRADE_STATEMENTS[3]
    assert "execution_budgets_user_profile_match_idx" in module._UPGRADE_STATEMENTS[4]
    assert "(user_id, agent_profile_id, tool_key, domain_hint, created_at, id)" in module._UPGRADE_STATEMENTS[4]
    assert "execution_budgets_one_active_scope_idx" in module._UPGRADE_STATEMENTS[5]
    assert "COALESCE(agent_profile_id, '')" in module._UPGRADE_STATEMENTS[5]
    assert "COALESCE(tool_key, '')" in module._UPGRADE_STATEMENTS[5]
    assert "COALESCE(domain_hint, '')" in module._UPGRADE_STATEMENTS[5]
    assert "WHERE status = 'active'" in module._UPGRADE_STATEMENTS[5]


def test_execution_budget_profile_scope_downgrade_contract() -> None:
    module = load_migration_module()

    assert "DROP INDEX IF EXISTS execution_budgets_one_active_scope_idx" in module._DOWNGRADE_STATEMENTS[0]
    assert "DROP INDEX IF EXISTS execution_budgets_user_profile_match_idx" in module._DOWNGRADE_STATEMENTS[1]
    assert "DROP CONSTRAINT IF EXISTS execution_budgets_agent_profile_id_fkey" in module._DOWNGRADE_STATEMENTS[2]
    assert "DROP COLUMN IF EXISTS agent_profile_id" in module._DOWNGRADE_STATEMENTS[3]
    assert "CREATE INDEX execution_budgets_user_match_idx" in module._DOWNGRADE_STATEMENTS[4]
    assert "(user_id, tool_key, domain_hint, created_at, id)" in module._DOWNGRADE_STATEMENTS[4]
    assert "CREATE UNIQUE INDEX execution_budgets_one_active_scope_idx" in module._DOWNGRADE_STATEMENTS[5]
    assert "COALESCE(tool_key, '')" in module._DOWNGRADE_STATEMENTS[5]
    assert "COALESCE(domain_hint, '')" in module._DOWNGRADE_STATEMENTS[5]
    assert "WHERE status = 'active'" in module._DOWNGRADE_STATEMENTS[5]
