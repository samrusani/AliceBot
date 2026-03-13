"""Add explicit user-scoped entity edges with simple temporal metadata."""

from __future__ import annotations

from alembic import op


revision = "20260312_0007"
down_revision = "20260312_0006"
branch_labels = None
depends_on = None

_RLS_TABLES = ("entity_edges",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE entity_edges (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          from_entity_id uuid NOT NULL,
          to_entity_id uuid NOT NULL,
          relationship_type text NOT NULL,
          valid_from timestamptz NULL,
          valid_to timestamptz NULL,
          source_memory_ids jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT entity_edges_from_entity_fkey
            FOREIGN KEY (from_entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE CASCADE,
          CONSTRAINT entity_edges_to_entity_fkey
            FOREIGN KEY (to_entity_id, user_id) REFERENCES entities(id, user_id) ON DELETE CASCADE,
          CONSTRAINT entity_edges_relationship_type_length_check
            CHECK (char_length(relationship_type) BETWEEN 1 AND 100),
          CONSTRAINT entity_edges_source_memory_ids_array_check
            CHECK (jsonb_typeof(source_memory_ids) = 'array'),
          CONSTRAINT entity_edges_source_memory_ids_nonempty_check
            CHECK (jsonb_array_length(source_memory_ids) > 0),
          CONSTRAINT entity_edges_valid_range_check
            CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from)
        );

        CREATE INDEX entity_edges_user_created_idx
          ON entity_edges (user_id, created_at, id);
        CREATE INDEX entity_edges_user_from_created_idx
          ON entity_edges (user_id, from_entity_id, created_at, id);
        CREATE INDEX entity_edges_user_to_created_idx
          ON entity_edges (user_id, to_entity_id, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON entity_edges TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY entity_edges_is_owner ON entity_edges
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS entity_edges",
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
