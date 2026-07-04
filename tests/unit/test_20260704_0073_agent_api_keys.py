from __future__ import annotations

import importlib

from alicebot_api.vnext_agent_control import PERMISSION_PROFILES


MODULE_NAME = "apps.api.alembic.versions.20260704_0073_agent_api_keys"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_semantic_retrieval_substrate() -> None:
    module = load_migration_module()

    assert module.revision == "20260704_0073"
    assert module.down_revision == "20260704_0072"


def test_migration_profiles_match_agent_control_profiles() -> None:
    module = load_migration_module()

    assert module.PERMISSION_PROFILES == PERMISSION_PROFILES


def test_upgrade_creates_hashed_key_table_with_rls(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "CREATE TABLE agent_api_keys" in joined
    assert "user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE" in joined
    assert "agent_id text NOT NULL" in joined
    assert "permission_profile text NOT NULL" in joined
    assert "key_hash text NOT NULL UNIQUE" in joined
    assert "key_prefix text NOT NULL" in joined
    assert "label text NULL" in joined
    assert "created_at timestamptz NOT NULL DEFAULT now()" in joined
    assert "revoked_at timestamptz NULL" in joined
    assert "last_used_at timestamptz NULL" in joined
    assert "agent_api_keys_permission_profile_check" in joined
    for profile in PERMISSION_PROFILES:
        assert f"'{profile}'" in joined
    assert "CREATE INDEX agent_api_keys_user_agent_idx" in joined
    assert "ON agent_api_keys (user_id, agent_id)" in joined
    assert "GRANT SELECT, INSERT, UPDATE ON agent_api_keys TO alicebot_app" in joined
    assert "ALTER TABLE agent_api_keys ENABLE ROW LEVEL SECURITY" in executed
    assert "ALTER TABLE agent_api_keys FORCE ROW LEVEL SECURITY" in executed
    assert "CREATE POLICY agent_api_keys_is_owner ON agent_api_keys" in joined
    assert "user_id = app.current_user_id()" in joined


def test_upgrade_never_stores_raw_keys(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "raw_key" not in joined
    assert "alice_sk_" not in joined


def test_downgrade_drops_agent_api_keys_table(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE)
    assert "DROP TABLE IF EXISTS agent_api_keys" in executed
