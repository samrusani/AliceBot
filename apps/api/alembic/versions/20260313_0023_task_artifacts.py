"""Add user-scoped task artifact records."""

from __future__ import annotations

from alembic import op


revision = "20260313_0023"
down_revision = "20260313_0022"
branch_labels = None
depends_on = None

_RLS_TABLES = ("task_artifacts",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE task_artifacts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_id uuid NOT NULL,
          task_workspace_id uuid NOT NULL,
          status text NOT NULL,
          ingestion_status text NOT NULL,
          relative_path text NOT NULL,
          media_type_hint text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT task_artifacts_task_user_fk
            FOREIGN KEY (task_id, user_id)
            REFERENCES tasks(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT task_artifacts_workspace_user_fk
            FOREIGN KEY (task_workspace_id, user_id)
            REFERENCES task_workspaces(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT task_artifacts_status_check
            CHECK (status IN ('registered')),
          CONSTRAINT task_artifacts_ingestion_status_check
            CHECK (ingestion_status IN ('pending')),
          CONSTRAINT task_artifacts_relative_path_nonempty_check
            CHECK (length(relative_path) > 0),
          CONSTRAINT task_artifacts_media_type_hint_nonempty_check
            CHECK (media_type_hint IS NULL OR length(media_type_hint) > 0)
        );

        CREATE INDEX task_artifacts_user_created_idx
          ON task_artifacts (user_id, created_at, id);

        CREATE UNIQUE INDEX task_artifacts_workspace_relative_path_idx
          ON task_artifacts (user_id, task_workspace_id, relative_path);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON task_artifacts TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY task_artifacts_is_owner ON task_artifacts
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS task_artifacts",
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
