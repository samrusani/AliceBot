from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260721_0094_browser_clip_capabilities"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_artifact_rating_reviewer_constraint() -> None:
    module = load_migration_module()

    assert module.revision == "20260721_0094"
    assert module.down_revision == "20260721_0093"


def test_upgrade_creates_hash_only_short_lived_capability_table_with_rls(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "CREATE TABLE browser_clip_capabilities" in joined
    assert "user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE" in joined
    assert "capability_hash text NOT NULL UNIQUE" in joined
    assert "origin text NOT NULL" in joined
    assert "expires_at timestamptz NOT NULL" in joined
    assert "consumed_at timestamptz NULL" in joined
    assert "created_at timestamptz NOT NULL DEFAULT clock_timestamp()" in joined
    assert "browser_clip_capabilities_hash_check" in joined
    assert "browser_clip_capabilities_expiry_range_check" in joined
    assert "interval '5 minutes'" in joined
    assert "browser_clip_capabilities_live_expiry_idx" in joined
    assert "browser_clip_capabilities_consumed_idx" in joined
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON browser_clip_capabilities TO alicebot_app" in joined
    assert "ALTER TABLE browser_clip_capabilities ENABLE ROW LEVEL SECURITY" in executed
    assert "ALTER TABLE browser_clip_capabilities FORCE ROW LEVEL SECURITY" in executed
    assert "CREATE POLICY browser_clip_capabilities_is_owner" in joined
    assert "user_id = app.current_user_id()" in joined

    assert "raw_capability" not in joined
    assert "capture_token" not in joined
    assert "alice_clip_" not in joined


def test_downgrade_drops_browser_clip_capabilities_table(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == ["DROP TABLE IF EXISTS browser_clip_capabilities"]
