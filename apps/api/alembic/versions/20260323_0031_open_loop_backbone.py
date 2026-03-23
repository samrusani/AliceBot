"""Add open-loop lifecycle table for unresolved commitments."""

from __future__ import annotations

from alembic import op


revision = "20260323_0031"
down_revision = "20260323_0030"
branch_labels = None
depends_on = None

OPEN_LOOP_STATUSES = (
    "open",
    "resolved",
    "dismissed",
)

_OPEN_LOOP_STATUSES_SQL = ", ".join(f"'{value}'" for value in OPEN_LOOP_STATUSES)

_RLS_TABLES = ("open_loops",)

_UPGRADE_SCHEMA_STATEMENT = f"""
        CREATE TABLE open_loops (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          memory_id uuid NULL,
          title text NOT NULL,
          status text NOT NULL,
          opened_at timestamptz NOT NULL DEFAULT now(),
          due_at timestamptz NULL,
          resolved_at timestamptz NULL,
          resolution_note text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT open_loops_memory_fkey
            FOREIGN KEY (memory_id, user_id)
            REFERENCES memories(id, user_id)
            ON DELETE SET NULL,
          CONSTRAINT open_loops_status_check
            CHECK (status IN ({_OPEN_LOOP_STATUSES_SQL})),
          CONSTRAINT open_loops_title_length_check
            CHECK (char_length(title) <= 280),
          CONSTRAINT open_loops_resolution_note_length_check
            CHECK (resolution_note IS NULL OR char_length(resolution_note) <= 2000),
          CONSTRAINT open_loops_resolved_state_check
            CHECK (
              (status = 'open' AND resolved_at IS NULL AND resolution_note IS NULL)
              OR (status IN ('resolved', 'dismissed') AND resolved_at IS NOT NULL)
            )
        );

        CREATE INDEX open_loops_user_status_opened_idx
          ON open_loops (user_id, status, opened_at DESC, created_at DESC, id DESC);
        CREATE INDEX open_loops_user_memory_idx
          ON open_loops (user_id, memory_id, created_at DESC, id DESC);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON open_loops TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY open_loops_is_owner ON open_loops
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS open_loops",
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
