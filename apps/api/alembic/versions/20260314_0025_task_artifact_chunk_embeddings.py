"""Add user-scoped task artifact chunk embedding records."""

from __future__ import annotations

from alembic import op


revision = "20260314_0025"
down_revision = "20260314_0024"
branch_labels = None
depends_on = None

_RLS_TABLES = ("task_artifact_chunk_embeddings",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE task_artifact_chunk_embeddings (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_artifact_chunk_id uuid NOT NULL,
          embedding_config_id uuid NOT NULL,
          dimensions integer NOT NULL,
          vector jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, task_artifact_chunk_id, embedding_config_id),
          CONSTRAINT task_artifact_chunk_embeddings_chunk_fkey
            FOREIGN KEY (task_artifact_chunk_id, user_id)
            REFERENCES task_artifact_chunks(id, user_id) ON DELETE CASCADE,
          CONSTRAINT task_artifact_chunk_embeddings_embedding_config_fkey
            FOREIGN KEY (embedding_config_id, user_id)
            REFERENCES embedding_configs(id, user_id) ON DELETE CASCADE,
          CONSTRAINT task_artifact_chunk_embeddings_dimensions_check
            CHECK (dimensions > 0),
          CONSTRAINT task_artifact_chunk_embeddings_vector_array_check
            CHECK (jsonb_typeof(vector) = 'array'),
          CONSTRAINT task_artifact_chunk_embeddings_vector_nonempty_check
            CHECK (jsonb_array_length(vector) > 0),
          CONSTRAINT task_artifact_chunk_embeddings_vector_dimensions_match_check
            CHECK (jsonb_array_length(vector) = dimensions)
        );

        CREATE INDEX task_artifact_chunk_embeddings_user_chunk_created_idx
          ON task_artifact_chunk_embeddings (user_id, task_artifact_chunk_id, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON task_artifact_chunk_embeddings TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY task_artifact_chunk_embeddings_is_owner ON task_artifact_chunk_embeddings
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS task_artifact_chunk_embeddings",
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
