from __future__ import annotations

import importlib

from alicebot_api.sqlite_schema import ENTITY_TYPES as SQLITE_ENTITY_TYPES
from alicebot_api.vnext_entity_names import ENTITY_TYPES


MODULE_NAME = "apps.api.alembic.versions.20260705_0078_entity_substrate"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_temporal_supersession_columns() -> None:
    module = load_migration_module()

    assert module.revision == "20260705_0078"
    assert module.down_revision == "20260704_0077"


def test_migration_entity_types_match_the_shared_module_and_sqlite_mirror() -> None:
    module = load_migration_module()

    assert module.ENTITY_TYPES == ENTITY_TYPES
    assert module.ENTITY_TYPES == SQLITE_ENTITY_TYPES


def test_upgrade_creates_entities_table_with_resolution_key_and_rls(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "CREATE TABLE vnext_entities" in joined
    assert "user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE" in joined
    assert "entity_type text NOT NULL" in joined
    assert "name text NOT NULL" in joined
    assert "normalized_name text NOT NULL" in joined
    assert "aliases jsonb NOT NULL DEFAULT '[]'::jsonb" in joined
    assert "metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb" in joined
    assert "created_at timestamptz NOT NULL DEFAULT now()" in joined
    assert "updated_at timestamptz NOT NULL DEFAULT now()" in joined
    assert "deleted_at timestamptz NULL" in joined
    assert "first_observed_at timestamptz NULL" in joined
    assert "last_observed_at timestamptz NULL" in joined
    assert "mention_count integer NOT NULL DEFAULT 0" in joined
    # The resolution key and its lookup index.
    assert "UNIQUE (user_id, entity_type, normalized_name)" in joined
    assert "CREATE INDEX vnext_entities_user_normalized_name_idx" in joined
    assert "ON vnext_entities (user_id, normalized_name)" in joined
    # The entity_type CHECK carries every allowed value.
    assert "vnext_entities_entity_type_check" in joined
    for entity_type in ENTITY_TYPES:
        assert f"'{entity_type}'" in joined
    # Shape checks on the json columns and counters.
    assert "jsonb_typeof(aliases) = 'array'" in joined
    assert "jsonb_typeof(metadata_json) = 'object'" in joined
    assert "mention_count >= 0" in joined
    # RLS like every vNext table (the 0073 agent_api_keys pattern).
    assert "GRANT SELECT, INSERT, UPDATE ON vnext_entities TO alicebot_app" in executed
    assert "ALTER TABLE vnext_entities ENABLE ROW LEVEL SECURITY" in executed
    assert "ALTER TABLE vnext_entities FORCE ROW LEVEL SECURITY" in executed
    assert "CREATE POLICY vnext_entities_is_owner ON vnext_entities" in joined
    assert "user_id = app.current_user_id()" in joined


def test_upgrade_creates_append_only_relationship_history(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "CREATE TABLE entity_relationship_events" in joined
    assert "entity_id uuid NOT NULL" in joined
    assert "relationship_type_before text NULL" in joined
    assert "relationship_type_after text NOT NULL" in joined
    assert "changed_at timestamptz NOT NULL DEFAULT now()" in joined
    assert "source_id uuid NULL" in joined
    # History rows belong to their entity (composite tenant-safe FK).
    assert "REFERENCES vnext_entities(id, user_id)" in joined
    # Append-only enforcement, exactly like event_log: a trigger function
    # plus a BEFORE UPDATE OR DELETE row trigger.
    assert "CREATE OR REPLACE FUNCTION app.reject_entity_relationship_event_mutation()" in joined
    assert "entity_relationship_events is append-only" in joined
    assert "CREATE TRIGGER entity_relationship_events_append_only" in joined
    assert "BEFORE UPDATE OR DELETE ON entity_relationship_events" in joined
    # History reads are (user, entity, recency)-shaped.
    assert "CREATE INDEX entity_relationship_events_entity_changed_idx" in joined
    assert "ON entity_relationship_events (user_id, entity_id, changed_at DESC, id DESC)" in joined
    # Append-only surface gets SELECT + INSERT only, with matching policies.
    assert "GRANT SELECT, INSERT ON entity_relationship_events TO alicebot_app" in executed
    assert "GRANT SELECT, INSERT, UPDATE ON entity_relationship_events" not in joined
    assert "ALTER TABLE entity_relationship_events ENABLE ROW LEVEL SECURITY" in executed
    assert "ALTER TABLE entity_relationship_events FORCE ROW LEVEL SECURITY" in executed
    assert "CREATE POLICY entity_relationship_events_read_own ON entity_relationship_events" in joined
    assert "CREATE POLICY entity_relationship_events_insert_own ON entity_relationship_events" in joined


def test_source_id_carries_no_foreign_key_and_documents_why(monkeypatch) -> None:
    """An FK with ON DELETE SET NULL would have to UPDATE rows in the
    append-only history table when a source is deleted, which the trigger
    rejects. The migration must not create one and must say why."""
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "REFERENCES sources" not in joined

    docstring = " ".join((module.__doc__ or "").split())
    assert "NO foreign key" in docstring
    assert "append-only" in docstring


def test_downgrade_is_reversible_dropping_trigger_tables_and_function(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE)
    joined = "\n".join(executed)
    assert (
        "DROP TRIGGER IF EXISTS entity_relationship_events_append_only ON entity_relationship_events"
        in executed
    )
    assert "DROP TABLE IF EXISTS entity_relationship_events" in executed
    assert "DROP TABLE IF EXISTS vnext_entities" in executed
    assert "DROP FUNCTION IF EXISTS app.reject_entity_relationship_event_mutation()" in executed
    # The trigger drop precedes its table; the history table (which holds
    # the FK) drops before entities; the function goes last.
    assert joined.index("DROP TRIGGER") < joined.index("DROP TABLE IF EXISTS entity_relationship_events")
    assert joined.index("DROP TABLE IF EXISTS entity_relationship_events") < joined.index(
        "DROP TABLE IF EXISTS vnext_entities"
    )
    assert executed[-1] == "DROP FUNCTION IF EXISTS app.reject_entity_relationship_event_mutation()"
