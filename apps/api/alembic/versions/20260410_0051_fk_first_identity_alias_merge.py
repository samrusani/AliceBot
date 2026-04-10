"""Add FK-backed continuity entity bindings plus alias and merge audit tables."""

from __future__ import annotations

from alembic import op


revision = "20260410_0051"
down_revision = "20260410_0050"
branch_labels = None
depends_on = None

_RLS_TABLES = ("entity_aliases", "entity_merge_log")

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE entities DROP CONSTRAINT IF EXISTS entities_type_check
        """,
    """
        ALTER TABLE entities
          ADD CONSTRAINT entities_type_check
          CHECK (entity_type IN ('person', 'merchant', 'product', 'project', 'routine', 'topic'))
        """,
    """
        CREATE TABLE entity_aliases (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          entity_id uuid NOT NULL,
          alias text NOT NULL,
          normalized_alias text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT entity_aliases_entity_fkey
            FOREIGN KEY (entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE CASCADE,
          CONSTRAINT entity_aliases_alias_length_check
            CHECK (char_length(alias) BETWEEN 1 AND 200),
          CONSTRAINT entity_aliases_normalized_alias_length_check
            CHECK (char_length(normalized_alias) BETWEEN 1 AND 200),
          CONSTRAINT entity_aliases_unique_per_entity
            UNIQUE (user_id, entity_id, normalized_alias)
        )
        """,
    """
        CREATE INDEX entity_aliases_user_normalized_alias_idx
          ON entity_aliases (user_id, normalized_alias, created_at, id)
        """,
    """
        CREATE TABLE entity_merge_log (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_entity_id uuid NOT NULL,
          target_entity_id uuid NOT NULL,
          reason text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT entity_merge_log_source_entity_fkey
            FOREIGN KEY (source_entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE CASCADE,
          CONSTRAINT entity_merge_log_target_entity_fkey
            FOREIGN KEY (target_entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE CASCADE,
          CONSTRAINT entity_merge_log_distinct_entities_check
            CHECK (source_entity_id <> target_entity_id),
          CONSTRAINT entity_merge_log_reason_length_check
            CHECK (reason IS NULL OR char_length(reason) BETWEEN 1 AND 500)
        )
        """,
    """
        CREATE INDEX entity_merge_log_user_source_created_idx
          ON entity_merge_log (user_id, source_entity_id, created_at DESC, id DESC)
        """,
    """
        CREATE INDEX entity_merge_log_user_target_created_idx
          ON entity_merge_log (user_id, target_entity_id, created_at DESC, id DESC)
        """,
    """
        ALTER TABLE continuity_objects
          ADD COLUMN project_entity_id uuid NULL,
          ADD COLUMN person_entity_id uuid NULL,
          ADD COLUMN topic_entity_id uuid NULL
        """,
    """
        ALTER TABLE continuity_objects
          ADD CONSTRAINT continuity_objects_project_entity_fkey
          FOREIGN KEY (project_entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE SET NULL
        """,
    """
        ALTER TABLE continuity_objects
          ADD CONSTRAINT continuity_objects_person_entity_fkey
          FOREIGN KEY (person_entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE SET NULL
        """,
    """
        ALTER TABLE continuity_objects
          ADD CONSTRAINT continuity_objects_topic_entity_fkey
          FOREIGN KEY (topic_entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE SET NULL
        """,
    """
        CREATE INDEX continuity_objects_user_project_entity_created_idx
          ON continuity_objects (user_id, project_entity_id, created_at DESC, id DESC)
        """,
    """
        CREATE INDEX continuity_objects_user_person_entity_created_idx
          ON continuity_objects (user_id, person_entity_id, created_at DESC, id DESC)
        """,
    """
        CREATE INDEX continuity_objects_user_topic_entity_created_idx
          ON continuity_objects (user_id, topic_entity_id, created_at DESC, id DESC)
        """,
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON entity_aliases TO alicebot_app",
    "GRANT SELECT, INSERT ON entity_merge_log TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENTS = (
    """
        CREATE POLICY entity_aliases_is_owner ON entity_aliases
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id())
        """,
    """
        CREATE POLICY entity_merge_log_is_owner ON entity_merge_log
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id())
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS continuity_objects_user_topic_entity_created_idx",
    "DROP INDEX IF EXISTS continuity_objects_user_person_entity_created_idx",
    "DROP INDEX IF EXISTS continuity_objects_user_project_entity_created_idx",
    "ALTER TABLE continuity_objects DROP CONSTRAINT IF EXISTS continuity_objects_topic_entity_fkey",
    "ALTER TABLE continuity_objects DROP CONSTRAINT IF EXISTS continuity_objects_person_entity_fkey",
    "ALTER TABLE continuity_objects DROP CONSTRAINT IF EXISTS continuity_objects_project_entity_fkey",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS topic_entity_id",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS person_entity_id",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS project_entity_id",
    "DROP INDEX IF EXISTS entity_merge_log_user_target_created_idx",
    "DROP INDEX IF EXISTS entity_merge_log_user_source_created_idx",
    "DROP TABLE IF EXISTS entity_merge_log",
    "DROP INDEX IF EXISTS entity_aliases_user_normalized_alias_idx",
    "DROP TABLE IF EXISTS entity_aliases",
    "ALTER TABLE entities DROP CONSTRAINT IF EXISTS entities_type_check",
    """
        ALTER TABLE entities
          ADD CONSTRAINT entities_type_check
          CHECK (entity_type IN ('person', 'merchant', 'product', 'project', 'routine'))
        """,
)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)
    for statement in _UPGRADE_GRANT_STATEMENTS:
        op.execute(statement)
    _enable_row_level_security()
    for statement in _UPGRADE_POLICY_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
