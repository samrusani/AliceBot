"""Add persisted traces and trace events for context compilation."""

from __future__ import annotations

from alembic import op


revision = "20260311_0003"
down_revision = "20260311_0002"
branch_labels = None
depends_on = None

_RLS_TABLES = ("traces", "trace_events")

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.reject_trace_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'trace events are append-only';
        END;
        $$;
        """,
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE traces (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          thread_id uuid NOT NULL,
          kind text NOT NULL,
          compiler_version text NOT NULL,
          status text NOT NULL,
          limits jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          FOREIGN KEY (thread_id, user_id)
            REFERENCES threads(id, user_id)
            ON DELETE CASCADE
        );

        CREATE TABLE trace_events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          trace_id uuid NOT NULL,
          sequence_no bigint NOT NULL,
          kind text NOT NULL,
          payload jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (trace_id, sequence_no),
          FOREIGN KEY (trace_id, user_id)
            REFERENCES traces(id, user_id)
            ON DELETE CASCADE
        );

        CREATE INDEX traces_thread_created_idx
          ON traces (thread_id, created_at);
        """

_UPGRADE_TRIGGER_STATEMENT = """
        CREATE TRIGGER trace_events_append_only
        BEFORE UPDATE OR DELETE ON trace_events
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_trace_event_mutation();
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON traces TO alicebot_app",
    "GRANT SELECT, INSERT ON trace_events TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY traces_is_owner ON traces
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY trace_events_read_own ON trace_events
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY trace_events_insert_own ON trace_events
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TRIGGER IF EXISTS trace_events_append_only ON trace_events",
    "DROP TABLE IF EXISTS trace_events",
    "DROP TABLE IF EXISTS traces",
    "DROP FUNCTION IF EXISTS app.reject_trace_event_mutation()",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_BOOTSTRAP_STATEMENTS)
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    op.execute(_UPGRADE_TRIGGER_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
