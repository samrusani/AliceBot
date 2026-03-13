"""Link tool executions directly to their durable task step."""

from __future__ import annotations

from alembic import op


revision = "20260313_0021"
down_revision = "20260313_0020"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE tool_executions
          ADD COLUMN task_step_id uuid;
        """,
    """
        UPDATE tool_executions AS executions
        SET task_step_id = COALESCE(
          approvals.task_step_id,
          (
            SELECT task_steps.id
            FROM task_steps
            WHERE task_steps.user_id = executions.user_id
              AND task_steps.outcome ->> 'approval_id' = approvals.id::text
            ORDER BY task_steps.created_at ASC, task_steps.id ASC
            LIMIT 1
          )
        )
        FROM approvals
        WHERE approvals.id = executions.approval_id
          AND approvals.user_id = executions.user_id;
        """,
    """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM tool_executions
            WHERE task_step_id IS NULL
          ) THEN
            RAISE EXCEPTION
              'tool_executions.task_step_id backfill failed for existing rows';
          END IF;
        END;
        $$;
        """,
    """
        ALTER TABLE tool_executions
          ADD CONSTRAINT tool_executions_task_step_user_fk
            FOREIGN KEY (task_step_id, user_id)
            REFERENCES task_steps(id, user_id)
            ON DELETE RESTRICT;
        """,
    """
        ALTER TABLE tool_executions
          ALTER COLUMN task_step_id SET NOT NULL;
        """,
)

_DOWNGRADE_STATEMENTS = (
    """
        ALTER TABLE tool_executions
          DROP CONSTRAINT tool_executions_task_step_user_fk,
          DROP COLUMN task_step_id;
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
