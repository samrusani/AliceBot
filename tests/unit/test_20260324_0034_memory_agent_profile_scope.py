from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260324_0034_memory_agent_profile_scope"


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


def test_memory_profile_scope_upgrade_contract() -> None:
    module = load_migration_module()

    assert module.DEFAULT_AGENT_PROFILE_ID == "assistant_default"
    assert "ADD COLUMN agent_profile_id text NOT NULL DEFAULT 'assistant_default'" in module._UPGRADE_STATEMENTS[0]
    assert "FOREIGN KEY (agent_profile_id)" in module._UPGRADE_STATEMENTS[1]
    assert "REFERENCES agent_profiles(id)" in module._UPGRADE_STATEMENTS[1]
    assert "DROP CONSTRAINT IF EXISTS memories_user_id_memory_key_key" in module._UPGRADE_STATEMENTS[2]
    assert "memories_user_profile_memory_key_key" in module._UPGRADE_STATEMENTS[3]
    assert "UNIQUE (user_id, agent_profile_id, memory_key)" in module._UPGRADE_STATEMENTS[3]
    assert "memories_user_profile_updated_created_id_idx" in module._UPGRADE_STATEMENTS[4]
    assert "(user_id, agent_profile_id, updated_at, created_at, id)" in module._UPGRADE_STATEMENTS[4]


def test_memory_profile_scope_downgrade_contract_handles_cross_profile_duplicates() -> None:
    module = load_migration_module()

    assert "DROP CONSTRAINT IF EXISTS memories_user_profile_memory_key_key" in module._DOWNGRADE_STATEMENTS[1]
    assert "ROW_NUMBER() OVER" in module._DOWNGRADE_STATEMENTS[2]
    assert "PARTITION BY user_id, memory_key" in module._DOWNGRADE_STATEMENTS[2]
    assert "memory_key = ranked_memories.memory_key" in module._DOWNGRADE_STATEMENTS[2]
    assert "#profile:" in module._DOWNGRADE_STATEMENTS[2]
    assert "ADD CONSTRAINT memories_user_id_memory_key_key" in module._DOWNGRADE_STATEMENTS[3]
