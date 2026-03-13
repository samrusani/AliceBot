"""Add versioned embedding configs and user-scoped memory embeddings."""

from __future__ import annotations

from alembic import op


revision = "20260312_0008"
down_revision = "20260312_0007"
branch_labels = None
depends_on = None

_RLS_TABLES = ("embedding_configs", "memory_embeddings")

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE embedding_configs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider text NOT NULL,
          model text NOT NULL,
          version text NOT NULL,
          dimensions integer NOT NULL,
          status text NOT NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, provider, model, version),
          CONSTRAINT embedding_configs_provider_length_check
            CHECK (char_length(provider) BETWEEN 1 AND 100),
          CONSTRAINT embedding_configs_model_length_check
            CHECK (char_length(model) BETWEEN 1 AND 200),
          CONSTRAINT embedding_configs_version_length_check
            CHECK (char_length(version) BETWEEN 1 AND 100),
          CONSTRAINT embedding_configs_dimensions_check
            CHECK (dimensions > 0),
          CONSTRAINT embedding_configs_status_check
            CHECK (status IN ('active', 'deprecated', 'disabled')),
          CONSTRAINT embedding_configs_metadata_object_check
            CHECK (jsonb_typeof(metadata) = 'object')
        );

        CREATE INDEX embedding_configs_user_created_idx
          ON embedding_configs (user_id, created_at, id);

        CREATE TABLE memory_embeddings (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          memory_id uuid NOT NULL,
          embedding_config_id uuid NOT NULL,
          dimensions integer NOT NULL,
          vector jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, memory_id, embedding_config_id),
          CONSTRAINT memory_embeddings_memory_fkey
            FOREIGN KEY (memory_id, user_id) REFERENCES memories(id, user_id) ON DELETE CASCADE,
          CONSTRAINT memory_embeddings_embedding_config_fkey
            FOREIGN KEY (embedding_config_id, user_id)
            REFERENCES embedding_configs(id, user_id) ON DELETE CASCADE,
          CONSTRAINT memory_embeddings_dimensions_check
            CHECK (dimensions > 0),
          CONSTRAINT memory_embeddings_vector_array_check
            CHECK (jsonb_typeof(vector) = 'array'),
          CONSTRAINT memory_embeddings_vector_nonempty_check
            CHECK (jsonb_array_length(vector) > 0),
          CONSTRAINT memory_embeddings_vector_dimensions_match_check
            CHECK (jsonb_array_length(vector) = dimensions)
        );

        CREATE INDEX memory_embeddings_user_memory_created_idx
          ON memory_embeddings (user_id, memory_id, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON embedding_configs TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON memory_embeddings TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY embedding_configs_is_owner ON embedding_configs
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY memory_embeddings_is_owner ON memory_embeddings
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS memory_embeddings",
    "DROP TABLE IF EXISTS embedding_configs",
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
