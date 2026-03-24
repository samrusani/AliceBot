"""Scope memory records to durable agent profiles."""

from __future__ import annotations

from alembic import op


revision = "20260324_0034"
down_revision = "20260324_0033"
branch_labels = None
depends_on = None

DEFAULT_AGENT_PROFILE_ID = "assistant_default"

_UPGRADE_STATEMENTS = (
    f"""
        ALTER TABLE memories
          ADD COLUMN agent_profile_id text NOT NULL DEFAULT '{DEFAULT_AGENT_PROFILE_ID}'
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_agent_profile_id_fkey
          FOREIGN KEY (agent_profile_id)
          REFERENCES agent_profiles(id)
        """,
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_user_id_memory_key_key",
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_user_profile_memory_key_key
          UNIQUE (user_id, agent_profile_id, memory_key)
        """,
    """
        CREATE INDEX memories_user_profile_updated_created_id_idx
          ON memories (user_id, agent_profile_id, updated_at, created_at, id)
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS memories_user_profile_updated_created_id_idx",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_user_profile_memory_key_key",
    """
        WITH ranked_memories AS (
          SELECT
            id,
            user_id,
            memory_key,
            agent_profile_id,
            ROW_NUMBER() OVER (
              PARTITION BY user_id, memory_key
              ORDER BY
                CASE
                  WHEN agent_profile_id = 'assistant_default' THEN 0
                  ELSE 1
                END ASC,
                created_at ASC,
                id ASC
            ) AS duplicate_rank
          FROM memories
        )
        UPDATE memories
        SET memory_key = ranked_memories.memory_key
          || '#profile:'
          || ranked_memories.agent_profile_id
          || '#'
          || ranked_memories.id::text
        FROM ranked_memories
        WHERE memories.id = ranked_memories.id
          AND ranked_memories.duplicate_rank > 1
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_user_id_memory_key_key
          UNIQUE (user_id, memory_key)
        """,
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_agent_profile_id_fkey",
    "ALTER TABLE memories DROP COLUMN IF EXISTS agent_profile_id",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
