"""Entity substrate: generic entities and append-only relationship history.

The vNext path had ``people`` and free-text ``graph_edges`` node
references but NO generic entity table, and nothing linked the
``person`` memory_type to ``people``. This migration adds the substrate
temporal graph memory and entity resolution build on:

* ``vnext_entities`` -- one row (named vnext_entities because the legacy
  continuity engine already owns a table called entities) per resolved real-world thing (person,
  organization, project, topic, technology, market, report, agent,
  other). ``normalized_name`` (produced by
  ``alicebot_api.vnext_entity_names.normalize_entity_name``) is the
  resolution key: UNIQUE per (user_id, entity_type, normalized_name),
  indexed on (user_id, normalized_name) for query-time lookups, with a
  jsonb ``aliases`` array for alternate normalized names. Observation
  bookkeeping (``first_observed_at`` / ``last_observed_at`` /
  ``mention_count``) is widened by the store's record_entity_mention.
  RLS enable+force with the app.current_user_id() owner policy and
  alicebot_app grants, matching every vNext table (the 20260704_0073
  agent_api_keys pattern).

* ``entity_relationship_events`` -- append-only relationship history.
  The audit found update_person overwrites relationship_type in place,
  losing "advisor -> investor" transitions; this table records each
  change (before/after, when, from which source). Append-only is
  enforced by a BEFORE UPDATE OR DELETE trigger exactly like
  ``event_log``. ``source_id`` carries NO foreign key on purpose: an FK
  with ON DELETE SET NULL would have to UPDATE rows in this append-only
  table when a source is deleted, which the trigger rejects; a dangling
  source pointer is a historical annotation, not a lifecycle dependency.

Reversible: the downgrade drops the trigger, both tables, and the
trigger function.

Revision ID: 20260705_0078
Revises: 20260704_0077
"""

from __future__ import annotations

from alembic import op


revision = "20260705_0078"
down_revision = "20260704_0077"
branch_labels = None
depends_on = None


# Mirrors ENTITY_TYPES in alicebot_api.vnext_entity_names (and the
# SQLite CHECK constraint in alicebot_api.sqlite_schema).
ENTITY_TYPES = (
    "person",
    "organization",
    "project",
    "topic",
    "technology",
    "market",
    "report",
    "agent",
    "other",
)

_ENTITY_TYPES_SQL = ", ".join(f"'{value}'" for value in ENTITY_TYPES)

_RLS_TABLES = ("vnext_entities", "entity_relationship_events")

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.reject_entity_relationship_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'entity_relationship_events is append-only';
        END;
        $$;
        """,
)

_UPGRADE_SCHEMA_STATEMENT = f"""
        CREATE TABLE vnext_entities (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          entity_type text NOT NULL,
          name text NOT NULL,
          normalized_name text NOT NULL,
          aliases jsonb NOT NULL DEFAULT '[]'::jsonb,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          deleted_at timestamptz NULL,
          first_observed_at timestamptz NULL,
          last_observed_at timestamptz NULL,
          mention_count integer NOT NULL DEFAULT 0,
          UNIQUE (id, user_id),
          UNIQUE (user_id, entity_type, normalized_name),
          CONSTRAINT vnext_entities_entity_type_check
            CHECK (entity_type IN ({_ENTITY_TYPES_SQL})),
          CONSTRAINT vnext_entities_name_length_check
            CHECK (char_length(name) BETWEEN 1 AND 500),
          CONSTRAINT vnext_entities_normalized_name_length_check
            CHECK (char_length(normalized_name) BETWEEN 1 AND 500),
          CONSTRAINT vnext_entities_aliases_array_check
            CHECK (jsonb_typeof(aliases) = 'array'),
          CONSTRAINT vnext_entities_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object'),
          CONSTRAINT vnext_entities_mention_count_non_negative_check
            CHECK (mention_count >= 0),
          CONSTRAINT entities_observed_range_check
            CHECK (
              first_observed_at IS NULL
              OR last_observed_at IS NULL
              OR last_observed_at >= first_observed_at
            )
        );

        CREATE TABLE entity_relationship_events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          entity_id uuid NOT NULL,
          relationship_type_before text NULL,
          relationship_type_after text NOT NULL,
          changed_at timestamptz NOT NULL DEFAULT now(),
          source_id uuid NULL,
          metadata_json jsonb NOT NULL DEFAULT '{{}}'::jsonb,
          UNIQUE (id, user_id),
          CONSTRAINT entity_relationship_events_entity_fkey
            FOREIGN KEY (entity_id, user_id)
            REFERENCES vnext_entities(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT entity_relationship_events_after_length_check
            CHECK (char_length(relationship_type_after) BETWEEN 1 AND 120),
          CONSTRAINT entity_relationship_events_metadata_json_object_check
            CHECK (jsonb_typeof(metadata_json) = 'object')
        );

        CREATE INDEX vnext_entities_user_normalized_name_idx
          ON vnext_entities (user_id, normalized_name);
        CREATE INDEX entity_relationship_events_entity_changed_idx
          ON entity_relationship_events (user_id, entity_id, changed_at DESC, id DESC);
        """

_UPGRADE_TRIGGER_STATEMENTS = (
    """
        CREATE TRIGGER entity_relationship_events_append_only
        BEFORE UPDATE OR DELETE ON entity_relationship_events
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_entity_relationship_event_mutation();
        """,
)

_GRANTS = (
    "GRANT SELECT, INSERT, UPDATE ON vnext_entities TO alicebot_app",
    "GRANT SELECT, INSERT ON entity_relationship_events TO alicebot_app",
)

_POLICIES = """
        CREATE POLICY vnext_entities_is_owner ON vnext_entities
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY entity_relationship_events_read_own ON entity_relationship_events
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY entity_relationship_events_insert_own ON entity_relationship_events
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE = (
    "DROP TRIGGER IF EXISTS entity_relationship_events_append_only ON entity_relationship_events",
    "DROP TABLE IF EXISTS entity_relationship_events",
    "DROP TABLE IF EXISTS vnext_entities",
    "DROP FUNCTION IF EXISTS app.reject_entity_relationship_event_mutation()",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_BOOTSTRAP_STATEMENTS)
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_TRIGGER_STATEMENTS)
    _execute_statements(_GRANTS)
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(_POLICIES)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE)
