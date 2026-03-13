"""Add governed memory tables and append-only memory revisions."""

from __future__ import annotations

from alembic import op


revision = "20260311_0004"
down_revision = "20260311_0003"
branch_labels = None
depends_on = None

_RLS_TABLES = ("memories", "memory_revisions")

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.reject_memory_revision_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'memory revisions are append-only';
        END;
        $$;
        """,
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE memories (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          memory_key text NOT NULL,
          value jsonb NOT NULL,
          status text NOT NULL,
          source_event_ids jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          deleted_at timestamptz,
          UNIQUE (id, user_id),
          UNIQUE (user_id, memory_key)
        );

        CREATE TABLE memory_revisions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          memory_id uuid NOT NULL,
          sequence_no bigint NOT NULL,
          action text NOT NULL,
          memory_key text NOT NULL,
          previous_value jsonb,
          new_value jsonb,
          source_event_ids jsonb NOT NULL,
          candidate jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (memory_id, sequence_no),
          FOREIGN KEY (memory_id, user_id)
            REFERENCES memories(id, user_id)
            ON DELETE CASCADE
        );

        CREATE INDEX memories_user_status_updated_idx
          ON memories (user_id, status, updated_at);
        CREATE INDEX memory_revisions_memory_created_idx
          ON memory_revisions (memory_id, created_at);
        """

_UPGRADE_TRIGGER_STATEMENT = """
        CREATE TRIGGER memory_revisions_append_only
        BEFORE UPDATE OR DELETE ON memory_revisions
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_memory_revision_mutation();
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON memories TO alicebot_app",
    "GRANT SELECT, INSERT ON memory_revisions TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY memories_is_owner ON memories
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY memory_revisions_read_own ON memory_revisions
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY memory_revisions_insert_own ON memory_revisions
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TRIGGER IF EXISTS memory_revisions_append_only ON memory_revisions",
    "DROP TABLE IF EXISTS memory_revisions",
    "DROP TABLE IF EXISTS memories",
    "DROP FUNCTION IF EXISTS app.reject_memory_revision_mutation()",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_BOOTSTRAP_STATEMENTS)
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    op.execute(_UPGRADE_TRIGGER_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
