"""Add durable task-step review records."""

from __future__ import annotations

from alembic import op


revision = "20260313_0018"
down_revision = "20260313_0017"
branch_labels = None
depends_on = None

_RLS_TABLES = ("task_steps",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE task_steps (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_id uuid NOT NULL,
          sequence_no integer NOT NULL,
          kind text NOT NULL,
          status text NOT NULL,
          request jsonb NOT NULL,
          outcome jsonb NOT NULL,
          trace_id uuid NOT NULL,
          trace_kind text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT task_steps_task_user_fk
            FOREIGN KEY (task_id, user_id)
            REFERENCES tasks(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT task_steps_trace_user_fk
            FOREIGN KEY (trace_id, user_id)
            REFERENCES traces(id, user_id)
            ON DELETE RESTRICT,
          CONSTRAINT task_steps_sequence_no_check
            CHECK (sequence_no > 0),
          CONSTRAINT task_steps_kind_check
            CHECK (kind IN ('governed_request')),
          CONSTRAINT task_steps_status_check
            CHECK (status IN ('created', 'approved', 'executed', 'blocked', 'denied')),
          CONSTRAINT task_steps_request_object_check
            CHECK (jsonb_typeof(request) = 'object'),
          CONSTRAINT task_steps_outcome_object_check
            CHECK (jsonb_typeof(outcome) = 'object'),
          CONSTRAINT task_steps_trace_kind_nonempty_check
            CHECK (length(trace_kind) > 0)
        );

        CREATE UNIQUE INDEX task_steps_task_sequence_idx
          ON task_steps (user_id, task_id, sequence_no);

        CREATE INDEX task_steps_user_created_idx
          ON task_steps (user_id, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON task_steps TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY task_steps_is_owner ON task_steps
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS task_steps",
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
