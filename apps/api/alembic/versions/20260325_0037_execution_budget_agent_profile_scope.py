"""Add optional execution budget profile scope with deterministic active-scope uniqueness."""

from __future__ import annotations

from alembic import op


revision = "20260325_0037"
down_revision = "20260325_0036"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE execution_budgets
          ADD COLUMN agent_profile_id text NULL;
        """,
    """
        ALTER TABLE execution_budgets
          ADD CONSTRAINT execution_budgets_agent_profile_id_fkey
          FOREIGN KEY (agent_profile_id)
          REFERENCES agent_profiles(id);
        """,
    "DROP INDEX IF EXISTS execution_budgets_user_match_idx",
    "DROP INDEX IF EXISTS execution_budgets_one_active_scope_idx",
    """
        CREATE INDEX execution_budgets_user_profile_match_idx
          ON execution_budgets (user_id, agent_profile_id, tool_key, domain_hint, created_at, id);
        """,
    """
        CREATE UNIQUE INDEX execution_budgets_one_active_scope_idx
          ON execution_budgets (
            user_id,
            COALESCE(agent_profile_id, ''),
            COALESCE(tool_key, ''),
            COALESCE(domain_hint, '')
          )
          WHERE status = 'active';
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS execution_budgets_one_active_scope_idx",
    "DROP INDEX IF EXISTS execution_budgets_user_profile_match_idx",
    """
        ALTER TABLE execution_budgets
          DROP CONSTRAINT IF EXISTS execution_budgets_agent_profile_id_fkey;
        """,
    """
        ALTER TABLE execution_budgets
          DROP COLUMN IF EXISTS agent_profile_id;
        """,
    """
        CREATE INDEX execution_budgets_user_match_idx
          ON execution_budgets (user_id, tool_key, domain_hint, created_at, id);
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
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
