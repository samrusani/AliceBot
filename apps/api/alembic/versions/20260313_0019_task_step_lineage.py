"""Add explicit lineage fields for manual task-step continuation."""

from __future__ import annotations

from alembic import op


revision = "20260313_0019"
down_revision = "20260313_0018"
branch_labels = None
depends_on = None

_UPGRADE_SCHEMA_STATEMENT = """
        ALTER TABLE task_steps
          ADD COLUMN parent_step_id uuid,
          ADD COLUMN source_approval_id uuid,
          ADD COLUMN source_execution_id uuid,
          ADD CONSTRAINT task_steps_parent_step_user_fk
            FOREIGN KEY (parent_step_id, user_id)
            REFERENCES task_steps(id, user_id)
            ON DELETE RESTRICT,
          ADD CONSTRAINT task_steps_source_approval_user_fk
            FOREIGN KEY (source_approval_id, user_id)
            REFERENCES approvals(id, user_id)
            ON DELETE RESTRICT,
          ADD CONSTRAINT task_steps_source_execution_user_fk
            FOREIGN KEY (source_execution_id, user_id)
            REFERENCES tool_executions(id, user_id)
            ON DELETE RESTRICT,
          ADD CONSTRAINT task_steps_parent_step_not_self_check
            CHECK (parent_step_id IS NULL OR parent_step_id <> id);
        """

_DOWNGRADE_STATEMENTS = (
    """
        ALTER TABLE task_steps
          DROP CONSTRAINT task_steps_parent_step_not_self_check,
          DROP CONSTRAINT task_steps_source_execution_user_fk,
          DROP CONSTRAINT task_steps_source_approval_user_fk,
          DROP CONSTRAINT task_steps_parent_step_user_fk,
          DROP COLUMN source_execution_id,
          DROP COLUMN source_approval_id,
          DROP COLUMN parent_step_id;
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
