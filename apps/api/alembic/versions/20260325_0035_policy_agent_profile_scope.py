"""Scope policy evaluation inputs to global + thread profile policies."""

from __future__ import annotations

from alembic import op


revision = "20260325_0035"
down_revision = "20260324_0034"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE policies
          ADD COLUMN agent_profile_id text NULL
        """,
    """
        ALTER TABLE policies
          ADD CONSTRAINT policies_agent_profile_id_fkey
          FOREIGN KEY (agent_profile_id)
          REFERENCES agent_profiles(id)
        """,
    "DROP INDEX IF EXISTS policies_user_active_priority_created_idx",
    """
        CREATE INDEX policies_user_active_profile_priority_created_idx
          ON policies (user_id, active, agent_profile_id, priority, created_at, id)
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS policies_user_active_profile_priority_created_idx",
    "ALTER TABLE policies DROP CONSTRAINT IF EXISTS policies_agent_profile_id_fkey",
    "ALTER TABLE policies DROP COLUMN IF EXISTS agent_profile_id",
    """
        CREATE INDEX policies_user_active_priority_created_idx
          ON policies (user_id, active, priority, created_at, id)
        """,
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
