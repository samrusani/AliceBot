"""Link task runs, approvals, and tool executions with idempotent execution keys."""

from __future__ import annotations

from alembic import op


revision = "20260327_0039"
down_revision = "20260327_0038"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE task_runs
          DROP CONSTRAINT task_runs_status_check,
          DROP CONSTRAINT task_runs_stop_reason_check,
          DROP CONSTRAINT task_runs_status_stop_reason_check;
        """,
    """
        ALTER TABLE task_runs
          ADD CONSTRAINT task_runs_status_check
            CHECK (status IN ('queued', 'running', 'waiting', 'waiting_approval', 'paused', 'completed', 'cancelled')),
          ADD CONSTRAINT task_runs_stop_reason_check
            CHECK (
              stop_reason IS NULL
              OR stop_reason IN ('wait_state', 'waiting_approval', 'budget_exhausted', 'paused', 'completed', 'cancelled')
            ),
          ADD CONSTRAINT task_runs_status_stop_reason_check
            CHECK (
              (status IN ('queued', 'running') AND stop_reason IS NULL)
              OR (status = 'waiting' AND stop_reason = 'wait_state')
              OR (status = 'waiting_approval' AND stop_reason = 'waiting_approval')
              OR (status = 'paused' AND stop_reason IN ('budget_exhausted', 'paused'))
              OR (status = 'completed' AND stop_reason = 'completed')
              OR (status = 'cancelled' AND stop_reason = 'cancelled')
            );
        """,
    """
        ALTER TABLE approvals
          ADD COLUMN task_run_id uuid;
        """,
    """
        ALTER TABLE approvals
          ADD CONSTRAINT approvals_task_run_user_fk
            FOREIGN KEY (task_run_id, user_id)
            REFERENCES task_runs(id, user_id)
            ON DELETE SET NULL;
        """,
    """
        CREATE INDEX approvals_user_task_run_created_idx
          ON approvals (user_id, task_run_id, created_at, id)
          WHERE task_run_id IS NOT NULL;
        """,
    """
        ALTER TABLE tool_executions
          ADD COLUMN task_run_id uuid,
          ADD COLUMN idempotency_key text;
        """,
    """
        UPDATE tool_executions AS executions
        SET task_run_id = approvals.task_run_id
        FROM approvals
        WHERE approvals.id = executions.approval_id
          AND approvals.user_id = executions.user_id
          AND approvals.task_run_id IS NOT NULL;
        """,
    """
        ALTER TABLE tool_executions
          ADD CONSTRAINT tool_executions_task_run_user_fk
            FOREIGN KEY (task_run_id, user_id)
            REFERENCES task_runs(id, user_id)
            ON DELETE SET NULL,
          ADD CONSTRAINT tool_executions_idempotency_key_check
            CHECK (idempotency_key IS NULL OR length(btrim(idempotency_key)) > 0);
        """,
    """
        CREATE INDEX tool_executions_user_task_run_executed_idx
          ON tool_executions (user_id, task_run_id, executed_at, id)
          WHERE task_run_id IS NOT NULL;
        """,
    """
        CREATE UNIQUE INDEX tool_executions_task_run_idempotency_idx
          ON tool_executions (user_id, task_run_id, approval_id, idempotency_key)
          WHERE task_run_id IS NOT NULL AND idempotency_key IS NOT NULL;
        """,
)

_DOWNGRADE_STATEMENTS = (
    """
        DROP INDEX IF EXISTS tool_executions_task_run_idempotency_idx;
        """,
    """
        DROP INDEX IF EXISTS tool_executions_user_task_run_executed_idx;
        """,
    """
        ALTER TABLE tool_executions
          DROP CONSTRAINT IF EXISTS tool_executions_task_run_user_fk,
          DROP CONSTRAINT IF EXISTS tool_executions_idempotency_key_check,
          DROP COLUMN IF EXISTS task_run_id,
          DROP COLUMN IF EXISTS idempotency_key;
        """,
    """
        DROP INDEX IF EXISTS approvals_user_task_run_created_idx;
        """,
    """
        ALTER TABLE approvals
          DROP CONSTRAINT IF EXISTS approvals_task_run_user_fk,
          DROP COLUMN IF EXISTS task_run_id;
        """,
    """
        ALTER TABLE task_runs
          DROP CONSTRAINT task_runs_status_check,
          DROP CONSTRAINT task_runs_stop_reason_check,
          DROP CONSTRAINT task_runs_status_stop_reason_check;
        """,
    """
        ALTER TABLE task_runs
          ADD CONSTRAINT task_runs_status_check
            CHECK (status IN ('queued', 'running', 'waiting', 'paused', 'completed', 'cancelled')),
          ADD CONSTRAINT task_runs_stop_reason_check
            CHECK (
              stop_reason IS NULL
              OR stop_reason IN ('wait_state', 'budget_exhausted', 'paused', 'completed', 'cancelled')
            ),
          ADD CONSTRAINT task_runs_status_stop_reason_check
            CHECK (
              (status IN ('queued', 'running') AND stop_reason IS NULL)
              OR (status = 'waiting' AND stop_reason = 'wait_state')
              OR (status = 'paused' AND stop_reason IN ('budget_exhausted', 'paused'))
              OR (status = 'completed' AND stop_reason = 'completed')
              OR (status = 'cancelled' AND stop_reason = 'cancelled')
            );
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
