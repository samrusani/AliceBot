"""Add approval resolution state and runtime update access."""

from __future__ import annotations

from alembic import op


revision = "20260312_0012"
down_revision = "20260312_0011"
branch_labels = None
depends_on = None

_UPGRADE_SCHEMA_STATEMENT = """
        ALTER TABLE approvals
          DROP CONSTRAINT approvals_status_check,
          ADD COLUMN resolved_at timestamptz,
          ADD COLUMN resolved_by_user_id uuid REFERENCES users(id) ON DELETE RESTRICT,
          ADD CONSTRAINT approvals_status_check
            CHECK (status IN ('pending', 'approved', 'rejected')),
          ADD CONSTRAINT approvals_resolution_consistency_check
            CHECK (
              (status = 'pending' AND resolved_at IS NULL AND resolved_by_user_id IS NULL)
              OR (
                status IN ('approved', 'rejected')
                AND resolved_at IS NOT NULL
                AND resolved_by_user_id IS NOT NULL
              )
            ),
          ADD CONSTRAINT approvals_resolved_by_owner_check
            CHECK (resolved_by_user_id IS NULL OR resolved_by_user_id = user_id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT UPDATE ON approvals TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "REVOKE UPDATE ON approvals FROM alicebot_app",
    """
        ALTER TABLE approvals
          DROP CONSTRAINT approvals_resolved_by_owner_check,
          DROP CONSTRAINT approvals_resolution_consistency_check,
          DROP CONSTRAINT approvals_status_check,
          DROP COLUMN resolved_by_user_id,
          DROP COLUMN resolved_at,
          ADD CONSTRAINT approvals_status_check
            CHECK (status = 'pending');
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
