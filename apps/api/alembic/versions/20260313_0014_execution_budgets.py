"""Add deterministic execution budget records."""

from __future__ import annotations

from alembic import op


revision = "20260313_0014"
down_revision = "20260313_0013"
branch_labels = None
depends_on = None

_RLS_TABLES = ("execution_budgets",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE execution_budgets (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          tool_key text,
          domain_hint text,
          max_completed_executions integer NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT execution_budgets_selector_check
            CHECK (tool_key IS NOT NULL OR domain_hint IS NOT NULL),
          CONSTRAINT execution_budgets_max_completed_executions_check
            CHECK (max_completed_executions > 0)
        );

        CREATE INDEX execution_budgets_user_created_idx
          ON execution_budgets (user_id, created_at, id);

        CREATE INDEX execution_budgets_user_match_idx
          ON execution_budgets (user_id, tool_key, domain_hint, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON execution_budgets TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY execution_budgets_is_owner ON execution_budgets
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS execution_budgets",
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
