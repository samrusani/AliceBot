from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260325_0036_agent_profile_model_runtime"


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


def test_profile_runtime_upgrade_contract() -> None:
    module = load_migration_module()

    assert module.AGENT_PROFILE_RUNTIME_SEED_ROWS == (
        ("assistant_default", "openai_responses", "gpt-5-mini"),
        ("coach_default", "openai_responses", "gpt-5"),
    )
    assert "ADD COLUMN model_provider text NULL" in module._UPGRADE_STATEMENTS[0]
    assert "ADD COLUMN model_name text NULL" in module._UPGRADE_STATEMENTS[1]
    assert "agent_profiles_model_provider_check" in module._UPGRADE_STATEMENTS[2]
    assert "model_provider = 'openai_responses'" in module._UPGRADE_STATEMENTS[2]
    assert "agent_profiles_model_runtime_pairing_check" in module._UPGRADE_STATEMENTS[3]
    assert "(model_provider IS NULL AND model_name IS NULL)" in module._UPGRADE_STATEMENTS[3]
    assert "(model_provider IS NOT NULL AND char_length(model_name) > 0)" in module._UPGRADE_STATEMENTS[3]
    assert "UPDATE agent_profiles" in module._UPGRADE_STATEMENTS[4]
    assert "assistant_default" in module._UPGRADE_STATEMENTS[4]
    assert "coach_default" in module._UPGRADE_STATEMENTS[4]


def test_profile_runtime_downgrade_contract() -> None:
    module = load_migration_module()

    assert "DROP CONSTRAINT IF EXISTS agent_profiles_model_runtime_pairing_check" in module._DOWNGRADE_STATEMENTS[0]
    assert "DROP CONSTRAINT IF EXISTS agent_profiles_model_provider_check" in module._DOWNGRADE_STATEMENTS[1]
    assert "DROP COLUMN IF EXISTS model_name" in module._DOWNGRADE_STATEMENTS[2]
    assert "DROP COLUMN IF EXISTS model_provider" in module._DOWNGRADE_STATEMENTS[3]
