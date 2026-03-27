"""Add retry posture, failure class, and Sprint 13 task-run status controls."""

from __future__ import annotations

from alembic import op


revision = "20260327_0040"
down_revision = "20260327_0039"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE task_runs
          ADD COLUMN retry_count integer NOT NULL DEFAULT 0,
          ADD COLUMN retry_cap integer NOT NULL DEFAULT 1,
          ADD COLUMN retry_posture text NOT NULL DEFAULT 'none',
          ADD COLUMN failure_class text,
          ADD COLUMN last_transitioned_at timestamptz NOT NULL DEFAULT clock_timestamp();
        """,
    """
        ALTER TABLE task_runs
          DROP CONSTRAINT task_runs_status_check,
          DROP CONSTRAINT task_runs_stop_reason_check,
          DROP CONSTRAINT task_runs_status_stop_reason_check;
        """,
    """
        UPDATE task_runs
        SET status = CASE
              WHEN status = 'waiting' THEN 'waiting_user'
              WHEN status = 'completed' THEN 'done'
              WHEN status = 'paused' AND stop_reason = 'budget_exhausted' THEN 'failed'
              ELSE status
            END,
            stop_reason = CASE
              WHEN stop_reason = 'wait_state' THEN 'waiting_user'
              WHEN stop_reason = 'completed' THEN 'done'
              ELSE stop_reason
            END,
            failure_class = CASE
              WHEN status = 'paused' AND stop_reason = 'budget_exhausted' THEN 'budget'
              ELSE failure_class
            END,
            retry_posture = CASE
              WHEN status = 'paused' AND stop_reason = 'budget_exhausted' THEN 'terminal'
              WHEN status IN ('queued', 'running') THEN 'none'
              WHEN status = 'waiting_approval' THEN 'awaiting_approval'
              WHEN status = 'waiting' THEN 'awaiting_user'
              WHEN status = 'paused' THEN 'paused'
              WHEN status = 'completed' THEN 'terminal'
              WHEN status = 'cancelled' THEN 'terminal'
              WHEN status = 'failed' THEN 'terminal'
              ELSE retry_posture
            END,
            retry_cap = GREATEST(max_ticks, 1),
            last_transitioned_at = updated_at;
        """,
    """
        ALTER TABLE task_runs
          ADD CONSTRAINT task_runs_status_check
            CHECK (
              status IN (
                'queued',
                'running',
                'waiting_approval',
                'waiting_user',
                'paused',
                'failed',
                'done',
                'cancelled'
              )
            ),
          ADD CONSTRAINT task_runs_stop_reason_check
            CHECK (
              stop_reason IS NULL
              OR stop_reason IN (
                'waiting_approval',
                'waiting_user',
                'paused',
                'budget_exhausted',
                'approval_rejected',
                'policy_blocked',
                'retry_exhausted',
                'fatal_error',
                'done',
                'cancelled'
              )
            ),
          ADD CONSTRAINT task_runs_failure_class_check
            CHECK (
              failure_class IS NULL
              OR failure_class IN ('transient', 'policy', 'approval', 'budget', 'fatal')
            ),
          ADD CONSTRAINT task_runs_retry_posture_check
            CHECK (
              retry_posture IN (
                'none',
                'retryable',
                'exhausted',
                'terminal',
                'paused',
                'awaiting_approval',
                'awaiting_user'
              )
            ),
          ADD CONSTRAINT task_runs_retry_bounds_check
            CHECK (retry_count >= 0 AND retry_count <= retry_cap),
          ADD CONSTRAINT task_runs_status_stop_reason_check
            CHECK (
              (status IN ('queued', 'running') AND stop_reason IS NULL AND failure_class IS NULL)
              OR (status = 'waiting_approval' AND stop_reason = 'waiting_approval' AND failure_class IS NULL)
              OR (status = 'waiting_user' AND stop_reason = 'waiting_user' AND failure_class IS NULL)
              OR (status = 'paused' AND stop_reason = 'paused' AND failure_class IS NULL)
              OR (
                status = 'failed'
                AND stop_reason IN ('budget_exhausted', 'approval_rejected', 'policy_blocked', 'retry_exhausted', 'fatal_error')
                AND failure_class IS NOT NULL
              )
              OR (status = 'done' AND stop_reason = 'done' AND failure_class IS NULL)
              OR (status = 'cancelled' AND stop_reason = 'cancelled' AND failure_class IS NULL)
            );
        """,
    """
        CREATE INDEX task_runs_user_status_transition_idx
          ON task_runs (user_id, status, last_transitioned_at, id);
        """,
)

_DOWNGRADE_STATEMENTS = (
    """
        DROP INDEX IF EXISTS task_runs_user_status_transition_idx;
        """,
    """
        ALTER TABLE task_runs
          DROP CONSTRAINT task_runs_status_check,
          DROP CONSTRAINT task_runs_stop_reason_check,
          DROP CONSTRAINT task_runs_status_stop_reason_check,
          DROP CONSTRAINT IF EXISTS task_runs_failure_class_check,
          DROP CONSTRAINT IF EXISTS task_runs_retry_posture_check,
          DROP CONSTRAINT IF EXISTS task_runs_retry_bounds_check;
        """,
    """
        UPDATE task_runs
        SET status = CASE
              WHEN status = 'waiting_user' THEN 'waiting'
              WHEN status = 'done' THEN 'completed'
              WHEN status = 'failed' THEN 'paused'
              ELSE status
            END,
            stop_reason = CASE
              WHEN stop_reason = 'waiting_user' THEN 'wait_state'
              WHEN stop_reason = 'done' THEN 'completed'
              WHEN stop_reason IN ('approval_rejected', 'policy_blocked', 'retry_exhausted', 'fatal_error') THEN 'paused'
              ELSE stop_reason
            END;
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
        ALTER TABLE task_runs
          DROP COLUMN IF EXISTS retry_count,
          DROP COLUMN IF EXISTS retry_cap,
          DROP COLUMN IF EXISTS retry_posture,
          DROP COLUMN IF EXISTS failure_class,
          DROP COLUMN IF EXISTS last_transitioned_at;
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
