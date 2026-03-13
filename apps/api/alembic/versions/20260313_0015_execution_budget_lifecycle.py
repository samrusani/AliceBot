"""Add execution budget lifecycle controls."""

from __future__ import annotations

from alembic import op


revision = "20260313_0015"
down_revision = "20260313_0014"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE execution_budgets
          ADD COLUMN status text NOT NULL DEFAULT 'active',
          ADD COLUMN deactivated_at timestamptz,
          ADD COLUMN superseded_by_budget_id uuid REFERENCES execution_budgets(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
          ADD COLUMN supersedes_budget_id uuid REFERENCES execution_budgets(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
        """,
    """
        ALTER TABLE execution_budgets
          ADD CONSTRAINT execution_budgets_status_check
            CHECK (status IN ('active', 'inactive', 'superseded')),
          ADD CONSTRAINT execution_budgets_lifecycle_state_check
            CHECK (
              (status = 'active' AND deactivated_at IS NULL AND superseded_by_budget_id IS NULL)
              OR (status = 'inactive' AND deactivated_at IS NOT NULL AND superseded_by_budget_id IS NULL)
              OR (status = 'superseded' AND deactivated_at IS NOT NULL AND superseded_by_budget_id IS NOT NULL)
            ),
          ADD CONSTRAINT execution_budgets_supersedes_budget_unique
            UNIQUE (supersedes_budget_id);
        """,
    """
        CREATE INDEX execution_budgets_user_status_created_idx
          ON execution_budgets (user_id, status, created_at, id);
        """,
    """
        CREATE UNIQUE INDEX execution_budgets_one_active_scope_idx
          ON execution_budgets (
            user_id,
            COALESCE(tool_key, ''),
            COALESCE(domain_hint, '')
          )
          WHERE status = 'active';
        """,
    "GRANT SELECT, INSERT, UPDATE ON execution_budgets TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "REVOKE UPDATE ON execution_budgets FROM alicebot_app",
    "DROP INDEX IF EXISTS execution_budgets_one_active_scope_idx",
    "DROP INDEX IF EXISTS execution_budgets_user_status_created_idx",
    """
        ALTER TABLE execution_budgets
          DROP CONSTRAINT IF EXISTS execution_budgets_supersedes_budget_unique,
          DROP CONSTRAINT IF EXISTS execution_budgets_lifecycle_state_check,
          DROP CONSTRAINT IF EXISTS execution_budgets_status_check;
        """,
    """
        ALTER TABLE execution_budgets
          DROP COLUMN IF EXISTS supersedes_budget_id,
          DROP COLUMN IF EXISTS superseded_by_budget_id,
          DROP COLUMN IF EXISTS deactivated_at,
          DROP COLUMN IF EXISTS status;
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
