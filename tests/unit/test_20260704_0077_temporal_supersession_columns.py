from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260704_0077_temporal_supersession_columns"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_memory_scope_columns() -> None:
    module = load_migration_module()

    assert module.revision == "20260704_0077"
    assert module.down_revision == "20260704_0076"


def test_upgrade_adds_nullable_supersession_and_observed_at_columns(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert "ALTER TABLE memories ADD COLUMN superseded_by uuid NULL" in executed
    assert "ALTER TABLE memories ADD COLUMN supersedes uuid NULL" in executed
    assert "ALTER TABLE graph_edges ADD COLUMN observed_at timestamptz NULL" in executed


def test_supersession_columns_carry_no_foreign_key_and_document_why() -> None:
    """The pointers are deliberately plain nullable uuids: an FK to
    memories.id would couple delete order between a retired row and its
    replacement. The migration must not create one and must say why."""
    module = load_migration_module()

    joined = "\n".join(module._UPGRADE_STATEMENTS)
    assert "REFERENCES" not in joined
    assert "FOREIGN KEY" not in joined

    docstring = " ".join((module.__doc__ or "").split())
    assert "NO foreign key" in docstring
    assert "delete order" in docstring


def test_upgrade_backfills_from_the_exact_metadata_keys_the_review_flow_writes(monkeypatch) -> None:
    """The backfill must read the keys the supersede-existing flow already
    stashes (metadata_json->>'superseded_by' on the old row and
    metadata_json->>'supersedes' on the replacement), guarded by a
    uuid-shape match so malformed metadata cannot fail the ::uuid cast."""
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "SET superseded_by = (metadata_json ->> 'superseded_by')::uuid" in joined
    assert "SET supersedes = (metadata_json ->> 'supersedes')::uuid" in joined
    # Backfills never overwrite an already-populated column.
    assert "WHERE superseded_by IS NULL" in joined
    assert "WHERE supersedes IS NULL" in joined
    # And only copy uuid-shaped values.
    assert joined.count("[0-9a-fA-F]{12}") == 2


def test_upgrade_backfills_after_columns_and_before_index(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    add_column_index = joined.index("ADD COLUMN superseded_by")
    backfill_index = joined.index("SET superseded_by")
    create_index_index = joined.index("CREATE INDEX memories_user_superseded_by_idx")
    assert add_column_index < backfill_index < create_index_index


def test_upgrade_creates_partial_superseded_by_index(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "CREATE INDEX memories_user_superseded_by_idx" in joined
    assert "ON memories (user_id, superseded_by)" in joined
    assert "WHERE superseded_by IS NOT NULL" in joined


def test_downgrade_is_reversible_dropping_index_and_all_columns(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)
    joined = "\n".join(executed)
    assert "DROP INDEX IF EXISTS memories_user_superseded_by_idx" in joined
    assert "ALTER TABLE memories DROP COLUMN IF EXISTS superseded_by" in joined
    assert "ALTER TABLE memories DROP COLUMN IF EXISTS supersedes" in joined
    assert "ALTER TABLE graph_edges DROP COLUMN IF EXISTS observed_at" in joined
    # The index drop must precede the superseded_by column drop.
    assert joined.index("DROP INDEX") < joined.index("DROP COLUMN IF EXISTS superseded_by")
