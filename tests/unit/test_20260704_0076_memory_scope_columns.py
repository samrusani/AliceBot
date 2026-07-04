from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260704_0076_memory_scope_columns"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_staleness_write_path() -> None:
    module = load_migration_module()

    assert module.revision == "20260704_0076"
    assert module.down_revision == "20260704_0075"


def test_upgrade_adds_nullable_scope_columns_to_memories(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert "ALTER TABLE memories ADD COLUMN project_id text NULL" in executed
    assert "ALTER TABLE memories ADD COLUMN created_by_agent_id text NULL" in executed
    assert "ALTER TABLE memories ADD COLUMN run_id text NULL" in executed


def test_upgrade_backfills_from_the_exact_metadata_keys_the_write_path_uses(monkeypatch) -> None:
    """The backfill must read the keys agentic commits already stash:
    metadata_json->>'project_id' for project scope, plus the top-level
    agent_id/agent_run_id keys from agent_metadata with a fallback to the
    nested agentic_memory.agent_identity block."""
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "SET project_id = metadata_json ->> 'project_id'" in joined
    assert "metadata_json ->> 'agent_id'" in joined
    assert "metadata_json #>> '{agentic_memory,agent_identity,agent_id}'" in joined
    assert "metadata_json ->> 'agent_run_id'" in joined
    assert "metadata_json #>> '{agentic_memory,agent_identity,agent_run_id}'" in joined
    # Backfills never overwrite an already-populated column.
    assert "WHERE project_id IS NULL" in joined
    assert "WHERE created_by_agent_id IS NULL" in joined
    assert "WHERE run_id IS NULL" in joined


def test_upgrade_backfills_after_columns_and_before_index(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    add_column_index = joined.index("ADD COLUMN project_id")
    backfill_index = joined.index("SET project_id")
    create_index_index = joined.index("CREATE INDEX memories_user_project_idx")
    assert add_column_index < backfill_index < create_index_index


def test_upgrade_creates_partial_project_index(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "CREATE INDEX memories_user_project_idx" in joined
    assert "ON memories (user_id, project_id)" in joined
    assert "WHERE project_id IS NOT NULL" in joined


def test_upgrade_adds_project_scope_binding_column_to_agent_api_keys(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert "ALTER TABLE agent_api_keys ADD COLUMN project_scope text NULL" in executed


def test_downgrade_is_reversible_dropping_index_and_all_columns(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)
    joined = "\n".join(executed)
    assert "DROP INDEX IF EXISTS memories_user_project_idx" in joined
    assert "ALTER TABLE memories DROP COLUMN IF EXISTS project_id" in joined
    assert "ALTER TABLE memories DROP COLUMN IF EXISTS created_by_agent_id" in joined
    assert "ALTER TABLE memories DROP COLUMN IF EXISTS run_id" in joined
    assert "ALTER TABLE agent_api_keys DROP COLUMN IF EXISTS project_scope" in joined
    # The index drop must precede the project_id column drop.
    assert joined.index("DROP INDEX") < joined.index("DROP COLUMN IF EXISTS project_id")


def test_migration_documents_run_id_as_metadata_plus_filter_only() -> None:
    module = load_migration_module()

    docstring = " ".join((module.__doc__ or "").split())
    assert "no session entity" in docstring
