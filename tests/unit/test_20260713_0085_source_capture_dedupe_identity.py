from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260713_0085_source_capture_dedupe_identity"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_extends_lifecycle_identifier_repair() -> None:
    module = load_migration_module()
    assert module.revision == "20260713_0085"
    assert module.down_revision == "20260712_0084"


def test_upgrade_backfills_before_partial_unique_index(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "ALTER TABLE sources ADD COLUMN dedupe_key text NULL" in joined
    assert "metadata_json ->> 'raw_text'" in joined
    assert "metadata_json -> 'project_scope'" in joined
    assert "row_number() OVER" in joined
    assert joined.index("UPDATE sources") < joined.index("CREATE UNIQUE INDEX")
    assert "sources_user_dedupe_key_unique_idx" in joined
    assert "WHERE deleted_at IS NULL AND dedupe_key IS NOT NULL" in joined
    # Public content identity is deliberately not rewritten.
    assert "SET content_hash" not in joined


def test_downgrade_removes_index_constraint_and_column(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)
    assert "DROP INDEX IF EXISTS sources_user_dedupe_key_unique_idx" in executed[0]
    assert "DROP COLUMN IF EXISTS dedupe_key" in executed[-1]
