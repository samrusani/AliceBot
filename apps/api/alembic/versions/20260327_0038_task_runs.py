"""Add durable task-run lifecycle records for deterministic worker ticking."""

from __future__ import annotations

from alembic import op


revision = "20260327_0038"
down_revision = "20260325_0037"
branch_labels = None
depends_on = None

_RLS_TABLES = ("task_runs",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE task_runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_id uuid NOT NULL,
          status text NOT NULL,
          checkpoint jsonb NOT NULL DEFAULT '{}'::jsonb,
          tick_count integer NOT NULL DEFAULT 0,
          step_count integer NOT NULL DEFAULT 0,
          max_ticks integer NOT NULL,
          stop_reason text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT task_runs_task_user_fk
            FOREIGN KEY (task_id, user_id)
            REFERENCES tasks(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT task_runs_status_check
            CHECK (status IN ('queued', 'running', 'waiting', 'paused', 'completed', 'cancelled')),
          CONSTRAINT task_runs_checkpoint_object_check
            CHECK (jsonb_typeof(checkpoint) = 'object'),
          CONSTRAINT task_runs_tick_count_check
            CHECK (tick_count >= 0),
          CONSTRAINT task_runs_step_count_check
            CHECK (step_count >= 0),
          CONSTRAINT task_runs_max_ticks_check
            CHECK (max_ticks > 0),
          CONSTRAINT task_runs_stop_reason_check
            CHECK (
              stop_reason IS NULL
              OR stop_reason IN ('wait_state', 'budget_exhausted', 'paused', 'completed', 'cancelled')
            ),
          CONSTRAINT task_runs_status_stop_reason_check
            CHECK (
              (status IN ('queued', 'running') AND stop_reason IS NULL)
              OR (status = 'waiting' AND stop_reason = 'wait_state')
              OR (status = 'paused' AND stop_reason IN ('budget_exhausted', 'paused'))
              OR (status = 'completed' AND stop_reason = 'completed')
              OR (status = 'cancelled' AND stop_reason = 'cancelled')
            )
        );

        CREATE INDEX task_runs_user_task_created_idx
          ON task_runs (user_id, task_id, created_at, id);

        CREATE INDEX task_runs_user_status_updated_idx
          ON task_runs (user_id, status, updated_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON task_runs TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY task_runs_is_owner ON task_runs
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS task_runs",
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
