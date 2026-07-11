from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260711_0083_memory_lifecycle_invariants"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_extends_fact_key_head() -> None:
    module = load_migration_module()
    assert module.revision == "20260711_0083"
    assert module.down_revision == "20260707_0082"


def test_upgrade_deduplicates_before_enforcing_partial_unique_indexes(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    first_unique = joined.index("CREATE UNIQUE INDEX")
    assert joined.index("ROW_NUMBER() OVER") < first_unique
    assert "duplicate_commit_digest_canonical_memory_id" in joined
    assert "duplicate_confirmation_id_canonical_memory_id" in joined
    assert "CREATE UNIQUE INDEX memories_commit_digest_idx" in joined
    assert "CREATE UNIQUE INDEX memories_confirmation_id_idx" in joined
    assert "WHERE commit_digest IS NOT NULL" in joined
    assert "WHERE confirmation_id IS NOT NULL" in joined
    assert "CREATE TRIGGER memories_expire_derived_entity_edges" in joined
    assert "BEFORE UPDATE OF title, canonical_text, summary, value ON memories" in joined
    assert "edge_type IN ('mentions', 'related_to_person')" in joined


def test_upgrade_promotes_only_missing_legacy_nested_project_scopes(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    backfill = executed[0]
    assert "metadata_json #> '{agentic_memory,project_scope}'" in backfill
    assert "metadata_json -> 'project_scope'" in backfill
    assert "IS DISTINCT FROM 'array'" in backfill
    assert "GROUP BY normalized_element.normalized" in backfill
    assert "jsonb_array_length(legacy_scopes.normalized_scope) = 1" in backfill
    assert "THEN legacy_scopes.normalized_scope #>> '{0}'" in backfill


def test_downgrade_restores_non_unique_lookup_indexes(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    joined = "\n".join(executed)
    assert "CREATE UNIQUE INDEX" not in joined
    assert "CREATE INDEX memories_commit_digest_idx" in joined
    assert "CREATE INDEX memories_confirmation_id_idx" in joined
    assert "DROP TRIGGER IF EXISTS memories_expire_derived_entity_edges" in joined
