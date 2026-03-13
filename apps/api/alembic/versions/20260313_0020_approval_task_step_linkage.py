"""Link approvals directly to their durable task step."""

from __future__ import annotations

from alembic import op


revision = "20260313_0020"
down_revision = "20260313_0019"
branch_labels = None
depends_on = None

_UPGRADE_SCHEMA_STATEMENT = """
        ALTER TABLE approvals
          ADD COLUMN task_step_id uuid,
          ADD CONSTRAINT approvals_task_step_user_fk
            FOREIGN KEY (task_step_id, user_id)
            REFERENCES task_steps(id, user_id)
            ON DELETE RESTRICT;
        """

_DOWNGRADE_STATEMENTS = (
    """
        ALTER TABLE approvals
          DROP CONSTRAINT approvals_task_step_user_fk,
          DROP COLUMN task_step_id;
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
