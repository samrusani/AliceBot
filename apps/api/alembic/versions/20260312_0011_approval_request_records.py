"""Add durable approval request records."""

from __future__ import annotations

from alembic import op


revision = "20260312_0011"
down_revision = "20260312_0010"
branch_labels = None
depends_on = None

_RLS_TABLES = ("approvals",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE approvals (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          thread_id uuid NOT NULL,
          tool_id uuid NOT NULL,
          status text NOT NULL DEFAULT 'pending',
          request jsonb NOT NULL,
          tool jsonb NOT NULL,
          routing jsonb NOT NULL,
          routing_trace_id uuid NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT approvals_thread_user_fk
            FOREIGN KEY (thread_id, user_id)
            REFERENCES threads(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT approvals_tool_user_fk
            FOREIGN KEY (tool_id, user_id)
            REFERENCES tools(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT approvals_routing_trace_user_fk
            FOREIGN KEY (routing_trace_id, user_id)
            REFERENCES traces(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT approvals_status_check
            CHECK (status = 'pending'),
          CONSTRAINT approvals_request_object_check
            CHECK (jsonb_typeof(request) = 'object'),
          CONSTRAINT approvals_tool_object_check
            CHECK (jsonb_typeof(tool) = 'object'),
          CONSTRAINT approvals_routing_object_check
            CHECK (jsonb_typeof(routing) = 'object')
        );

        CREATE INDEX approvals_user_created_idx
          ON approvals (user_id, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON approvals TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY approvals_is_owner ON approvals
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS approvals",
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
