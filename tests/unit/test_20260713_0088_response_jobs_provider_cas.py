from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260713_0088_response_jobs_provider_cas"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_follows_persistence_scheduler_hardening() -> None:
    module = load_migration_module()
    assert module.revision == "20260713_0088"
    assert module.down_revision == "20260713_0087"


def test_migration_fingerprint_v1_has_a_literal_golden_vector() -> None:
    module = load_migration_module()

    actual = module.provider_config_fingerprint_v1(
        provider_key="openai_compatible",
        model_provider="openai_responses",
        display_name="Provider",
        base_url="https://provider.example/v1",
        api_key="provider_secret_ref:test",
        auth_mode="bearer",
        default_model="gpt-5-mini",
        status="active",
        model_list_path="/models",
        healthcheck_path="/models",
        invoke_path="/responses",
        azure_api_version="",
        azure_auth_secret_ref="",
        metadata={"nested": {"z": 2, "a": 1}, "enabled": True},
    )

    assert actual == "6f2ce85910465032f0276f2230b6220de4507033dc5c1b9ec10d16925e1ad1d6"


def test_upgrade_adds_durable_response_jobs_and_provider_fences(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(
        module,
        "_backfill_provider_config_fingerprints",
        lambda: executed.append("CANONICAL_PROVIDER_FINGERPRINT_BACKFILL"),
    )

    module.upgrade()

    joined = "\n".join(executed)
    assert "ADD COLUMN config_revision bigint NOT NULL DEFAULT 1" in joined
    assert "ADD COLUMN config_fingerprint_sha256 text" in joined
    assert "CANONICAL_PROVIDER_FINGERPRINT_BACKFILL" in joined
    assert "concat_ws" not in joined
    assert "ALTER COLUMN config_fingerprint_sha256 SET DEFAULT" in joined
    assert "CREATE FUNCTION advance_model_provider_config_fence()" in joined
    assert "CREATE TRIGGER model_providers_config_fence_trigger" in joined
    assert "NEW.config_revision := OLD.config_revision + 1" in joined
    assert "cannot be rewound independently of active configuration" in joined
    assert "must advance with active configuration" in joined
    assert "ADD COLUMN provider_config_revision bigint DEFAULT 1" in joined
    assert "ADD COLUMN provider_config_fingerprint_sha256 text DEFAULT" in joined
    capability_add = next(
        index for index, statement in enumerate(executed) if "ADD COLUMN provider_config_revision" in statement
    )
    capability_backfill = next(
        index for index, statement in enumerate(executed) if "UPDATE provider_capabilities AS capability" in statement
    )
    capability_not_null = next(
        index
        for index, statement in enumerate(executed)
        if "ALTER COLUMN provider_config_revision SET NOT NULL" in statement
    )
    assert capability_add < capability_backfill < capability_not_null
    assert "CREATE TABLE response_generation_jobs" in joined
    assert "UNIQUE (user_id, endpoint, idempotency_key_hash)" in joined
    assert "state IN ('pending', 'running', 'succeeded', 'failed')" in joined
    assert "response_generation_jobs_running_shape_check" in joined
    assert "response_generation_jobs_terminal_shape_check" in joined
    assert "WHERE state = 'running'" in joined
    assert "GRANT SELECT, INSERT, UPDATE ON response_generation_jobs TO alicebot_app" in joined
    assert "ENABLE ROW LEVEL SECURITY" in joined
    assert "FORCE ROW LEVEL SECURITY" in joined
    assert "USING (user_id = app.current_user_id())" in joined
    assert "WITH CHECK (user_id = app.current_user_id())" in joined


def test_downgrade_removes_response_jobs_before_provider_fences(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    joined = "\n".join(executed)
    assert joined.index("DROP TABLE IF EXISTS response_generation_jobs") < joined.index(
        "ALTER TABLE provider_capabilities"
    )
    assert "DROP COLUMN IF EXISTS provider_config_revision" in joined
    assert "DROP TRIGGER IF EXISTS model_providers_config_fence_trigger" in joined
    assert "DROP FUNCTION IF EXISTS advance_model_provider_config_fence()" in joined
    assert "DROP COLUMN IF EXISTS config_revision" in joined
