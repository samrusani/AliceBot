"""Add user-scoped task artifact chunk records."""

from __future__ import annotations

from alembic import op


revision = "20260314_0024"
down_revision = "20260313_0023"
branch_labels = None
depends_on = None

_RLS_TABLES = ("task_artifact_chunks",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE task_artifact_chunks (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_artifact_id uuid NOT NULL,
          sequence_no integer NOT NULL,
          char_start integer NOT NULL,
          char_end_exclusive integer NOT NULL,
          text text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT task_artifact_chunks_artifact_user_fk
            FOREIGN KEY (task_artifact_id, user_id)
            REFERENCES task_artifacts(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT task_artifact_chunks_sequence_no_check
            CHECK (sequence_no >= 1),
          CONSTRAINT task_artifact_chunks_char_start_check
            CHECK (char_start >= 0),
          CONSTRAINT task_artifact_chunks_char_end_exclusive_check
            CHECK (char_end_exclusive > char_start),
          CONSTRAINT task_artifact_chunks_text_nonempty_check
            CHECK (length(text) > 0)
        );

        CREATE UNIQUE INDEX task_artifact_chunks_artifact_sequence_idx
          ON task_artifact_chunks (user_id, task_artifact_id, sequence_no);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT UPDATE ON task_artifacts TO alicebot_app",
    "GRANT SELECT, INSERT ON task_artifact_chunks TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY task_artifact_chunks_is_owner ON task_artifact_chunks
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_UPGRADE_TASK_ARTIFACTS_STATEMENTS = (
    "ALTER TABLE task_artifacts DROP CONSTRAINT task_artifacts_ingestion_status_check",
    """
        ALTER TABLE task_artifacts
        ADD CONSTRAINT task_artifacts_ingestion_status_check
        CHECK (ingestion_status IN ('pending', 'ingested'))
        """,
)

_DOWNGRADE_STATEMENTS = (
    "REVOKE UPDATE ON task_artifacts FROM alicebot_app",
    "DROP TABLE IF EXISTS task_artifact_chunks",
    "ALTER TABLE task_artifacts DROP CONSTRAINT task_artifacts_ingestion_status_check",
    """
        ALTER TABLE task_artifacts
        ADD CONSTRAINT task_artifacts_ingestion_status_check
        CHECK (ingestion_status IN ('pending'))
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_TASK_ARTIFACTS_STATEMENTS)
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
