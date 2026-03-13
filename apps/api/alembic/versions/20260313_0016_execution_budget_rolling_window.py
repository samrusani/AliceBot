"""Add optional rolling-window execution budget support."""

from __future__ import annotations

from alembic import op


revision = "20260313_0016"
down_revision = "20260313_0015"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE execution_budgets
          ADD COLUMN rolling_window_seconds integer;
        """,
    """
        ALTER TABLE execution_budgets
          ADD CONSTRAINT execution_budgets_rolling_window_seconds_check
            CHECK (rolling_window_seconds IS NULL OR rolling_window_seconds > 0);
        """,
)

_DOWNGRADE_STATEMENTS = (
    """
        ALTER TABLE execution_budgets
          DROP CONSTRAINT IF EXISTS execution_budgets_rolling_window_seconds_check;
        """,
    """
        ALTER TABLE execution_budgets
          DROP COLUMN IF EXISTS rolling_window_seconds;
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
