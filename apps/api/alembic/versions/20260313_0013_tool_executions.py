"""Add durable tool execution review records."""

from __future__ import annotations

from alembic import op


revision = "20260313_0013"
down_revision = "20260312_0012"
branch_labels = None
depends_on = None

_RLS_TABLES = ("tool_executions",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE tool_executions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          approval_id uuid NOT NULL,
          thread_id uuid NOT NULL,
          tool_id uuid NOT NULL,
          trace_id uuid NOT NULL,
          request_event_id uuid,
          result_event_id uuid,
          status text NOT NULL,
          handler_key text,
          request jsonb NOT NULL,
          tool jsonb NOT NULL,
          result jsonb NOT NULL,
          executed_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT tool_executions_approval_user_fk
            FOREIGN KEY (approval_id, user_id)
            REFERENCES approvals(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tool_executions_thread_user_fk
            FOREIGN KEY (thread_id, user_id)
            REFERENCES threads(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT tool_executions_tool_user_fk
            FOREIGN KEY (tool_id, user_id)
            REFERENCES tools(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tool_executions_trace_user_fk
            FOREIGN KEY (trace_id, user_id)
            REFERENCES traces(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tool_executions_request_event_user_fk
            FOREIGN KEY (request_event_id, user_id)
            REFERENCES events(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tool_executions_result_event_user_fk
            FOREIGN KEY (result_event_id, user_id)
            REFERENCES events(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT tool_executions_status_check
            CHECK (status IN ('completed', 'blocked')),
          CONSTRAINT tool_executions_request_object_check
            CHECK (jsonb_typeof(request) = 'object'),
          CONSTRAINT tool_executions_tool_object_check
            CHECK (jsonb_typeof(tool) = 'object'),
          CONSTRAINT tool_executions_result_object_check
            CHECK (jsonb_typeof(result) = 'object'),
          CONSTRAINT tool_executions_status_event_consistency_check
            CHECK (
              (
                status = 'completed'
                AND handler_key IS NOT NULL
                AND request_event_id IS NOT NULL
                AND result_event_id IS NOT NULL
              )
              OR (
                status = 'blocked'
                AND request_event_id IS NULL
                AND result_event_id IS NULL
              )
            )
        );

        CREATE INDEX tool_executions_user_executed_idx
          ON tool_executions (user_id, executed_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON tool_executions TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY tool_executions_is_owner ON tool_executions
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS tool_executions",
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
