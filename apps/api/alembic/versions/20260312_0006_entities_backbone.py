"""Add explicit user-scoped entities backed by durable source memories."""

from __future__ import annotations

from alembic import op


revision = "20260312_0006"
down_revision = "20260312_0005"
branch_labels = None
depends_on = None

_RLS_TABLES = ("entities",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE entities (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          entity_type text NOT NULL,
          name text NOT NULL,
          source_memory_ids jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT entities_type_check
            CHECK (entity_type IN ('person', 'merchant', 'product', 'project', 'routine')),
          CONSTRAINT entities_name_length_check
            CHECK (char_length(name) BETWEEN 1 AND 200),
          CONSTRAINT entities_source_memory_ids_array_check
            CHECK (jsonb_typeof(source_memory_ids) = 'array'),
          CONSTRAINT entities_source_memory_ids_nonempty_check
            CHECK (jsonb_array_length(source_memory_ids) > 0)
        );

        CREATE INDEX entities_user_created_idx
          ON entities (user_id, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON entities TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY entities_is_owner ON entities
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS entities",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
