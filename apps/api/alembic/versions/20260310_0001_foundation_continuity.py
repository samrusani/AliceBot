"""Create continuity foundation tables with RLS and append-only events."""

from __future__ import annotations

from alembic import op


revision = "20260310_0001"
down_revision = None
branch_labels = None
depends_on = None

_RLS_TABLES = ("users", "threads", "sessions", "events")
_RLS_ACTIONS = ("ENABLE", "FORCE")

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    "CREATE EXTENSION IF NOT EXISTS vector",
    "CREATE SCHEMA IF NOT EXISTS app",
    """
        CREATE OR REPLACE FUNCTION app.current_user_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
          SELECT NULLIF(current_setting('app.current_user_id', true), '')::uuid
        $$;
        """,
    """
        CREATE OR REPLACE FUNCTION app.reject_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'events are append-only';
        END;
        $$;
        """,
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE users (
          id uuid PRIMARY KEY,
          email text NOT NULL UNIQUE,
          display_name text,
          created_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE threads (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id)
        );

        CREATE TABLE sessions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          thread_id uuid NOT NULL,
          status text NOT NULL DEFAULT 'active',
          started_at timestamptz NOT NULL DEFAULT now(),
          ended_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          FOREIGN KEY (thread_id, user_id)
            REFERENCES threads(id, user_id)
            ON DELETE CASCADE
        );

        CREATE TABLE events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          thread_id uuid NOT NULL,
          session_id uuid,
          sequence_no bigint NOT NULL,
          kind text NOT NULL,
          payload jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (thread_id, sequence_no),
          FOREIGN KEY (thread_id, user_id)
            REFERENCES threads(id, user_id)
            ON DELETE CASCADE,
          FOREIGN KEY (session_id, user_id)
            REFERENCES sessions(id, user_id)
            ON DELETE CASCADE
        );

        CREATE INDEX sessions_thread_created_idx
          ON sessions (thread_id, created_at);
        CREATE INDEX threads_user_created_idx
          ON threads (user_id, created_at);
        """

_UPGRADE_TRIGGER_STATEMENT = """
        CREATE TRIGGER events_append_only
        BEFORE UPDATE OR DELETE ON events
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_event_mutation();
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT USAGE ON SCHEMA public TO alicebot_app",
    "GRANT USAGE ON SCHEMA app TO alicebot_app",
    "GRANT SELECT, INSERT ON users TO alicebot_app",
    "GRANT SELECT, INSERT ON threads TO alicebot_app",
    "GRANT SELECT, INSERT ON sessions TO alicebot_app",
    "GRANT SELECT, INSERT ON events TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY users_is_owner ON users
          USING (id = app.current_user_id())
          WITH CHECK (id = app.current_user_id());

        CREATE POLICY threads_is_owner ON threads
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY sessions_is_owner ON sessions
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY events_read_own ON events
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY events_insert_own ON events
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TRIGGER IF EXISTS events_append_only ON events",
    "DROP TABLE IF EXISTS events",
    "DROP TABLE IF EXISTS sessions",
    "DROP TABLE IF EXISTS threads",
    "DROP TABLE IF EXISTS users",
    "DROP FUNCTION IF EXISTS app.reject_event_mutation()",
    "DROP FUNCTION IF EXISTS app.current_user_id()",
    "DROP SCHEMA IF EXISTS app",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _row_level_security_statements(table_name: str) -> tuple[str, ...]:
    return tuple(f"ALTER TABLE {table_name} {action} ROW LEVEL SECURITY" for action in _RLS_ACTIONS)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        _execute_statements(_row_level_security_statements(table_name))


def upgrade() -> None:
    _execute_statements(_UPGRADE_BOOTSTRAP_STATEMENTS)
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    op.execute(_UPGRADE_TRIGGER_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
