"""Add user-scoped task workspace records."""

from __future__ import annotations

from alembic import op


revision = "20260313_0022"
down_revision = "20260313_0021"
branch_labels = None
depends_on = None

_RLS_TABLES = ("task_workspaces",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE task_workspaces (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_id uuid NOT NULL,
          status text NOT NULL,
          local_path text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT task_workspaces_task_user_fk
            FOREIGN KEY (task_id, user_id)
            REFERENCES tasks(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT task_workspaces_status_check
            CHECK (status IN ('active')),
          CONSTRAINT task_workspaces_local_path_nonempty_check
            CHECK (length(local_path) > 0)
        );

        CREATE INDEX task_workspaces_user_created_idx
          ON task_workspaces (user_id, created_at, id);

        CREATE UNIQUE INDEX task_workspaces_active_task_idx
          ON task_workspaces (user_id, task_id)
          WHERE status = 'active';
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON task_workspaces TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY task_workspaces_is_owner ON task_workspaces
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS task_workspaces",
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
