"""Bind deterministic Phase 3 agent profile identity to threads."""

from __future__ import annotations

from alembic import op


revision = "20260324_0032"
down_revision = "20260323_0031"
branch_labels = None
depends_on = None

AGENT_PROFILE_IDS = (
    "assistant_default",
    "coach_default",
)

DEFAULT_AGENT_PROFILE_ID = "assistant_default"

_AGENT_PROFILE_IDS_SQL = ", ".join(f"'{value}'" for value in AGENT_PROFILE_IDS)

_UPGRADE_STATEMENTS = (
    f"""
        ALTER TABLE threads
          ADD COLUMN agent_profile_id text NOT NULL DEFAULT '{DEFAULT_AGENT_PROFILE_ID}'
        """,
    f"""
        ALTER TABLE threads
          ADD CONSTRAINT threads_agent_profile_id_check
          CHECK (agent_profile_id IN ({_AGENT_PROFILE_IDS_SQL}))
        """,
    """
        CREATE INDEX threads_user_agent_profile_created_idx
          ON threads (user_id, agent_profile_id, created_at DESC, id DESC)
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS threads_user_agent_profile_created_idx",
    "ALTER TABLE threads DROP CONSTRAINT IF EXISTS threads_agent_profile_id_check",
    "ALTER TABLE threads DROP COLUMN IF EXISTS agent_profile_id",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
