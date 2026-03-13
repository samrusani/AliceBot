"""Add durable task records with deterministic lifecycle status."""

from __future__ import annotations

from alembic import op


revision = "20260313_0017"
down_revision = "20260313_0016"
branch_labels = None
depends_on = None

_RLS_TABLES = ("tasks",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE tasks (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          thread_id uuid NOT NULL,
          tool_id uuid NOT NULL,
          status text NOT NULL,
          request jsonb NOT NULL,
          tool jsonb NOT NULL,
          latest_approval_id uuid,
          latest_execution_id uuid,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT tasks_thread_user_fk
            FOREIGN KEY (thread_id, user_id)
            REFERENCES threads(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT tasks_tool_user_fk
            FOREIGN KEY (tool_id, user_id)
            REFERENCES tools(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tasks_latest_approval_user_fk
            FOREIGN KEY (latest_approval_id, user_id)
            REFERENCES approvals(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tasks_latest_execution_user_fk
            FOREIGN KEY (latest_execution_id, user_id)
            REFERENCES tool_executions(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tasks_status_check
            CHECK (status IN ('pending_approval', 'approved', 'executed', 'denied', 'blocked')),
          CONSTRAINT tasks_request_object_check
            CHECK (jsonb_typeof(request) = 'object'),
          CONSTRAINT tasks_tool_object_check
            CHECK (jsonb_typeof(tool) = 'object'),
          CONSTRAINT tasks_pending_approval_link_check
            CHECK (status <> 'pending_approval' OR latest_approval_id IS NOT NULL),
          CONSTRAINT tasks_execution_link_check
            CHECK (
              (
                status IN ('executed', 'blocked')
                AND latest_execution_id IS NOT NULL
              )
              OR (
                status NOT IN ('executed', 'blocked')
                AND latest_execution_id IS NULL
              )
            )
        );

        CREATE INDEX tasks_user_created_idx
          ON tasks (user_id, created_at, id);

        CREATE UNIQUE INDEX tasks_latest_approval_unique_idx
          ON tasks (user_id, latest_approval_id)
          WHERE latest_approval_id IS NOT NULL;

        CREATE UNIQUE INDEX tasks_latest_execution_unique_idx
          ON tasks (user_id, latest_execution_id)
          WHERE latest_execution_id IS NOT NULL;
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON tasks TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY tasks_is_owner ON tasks
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS tasks",
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
