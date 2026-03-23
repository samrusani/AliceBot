"""Add typed memory metadata columns to the memory backbone."""

from __future__ import annotations

from alembic import op


revision = "20260323_0030"
down_revision = "20260319_0030"
branch_labels = None
depends_on = None

MEMORY_TYPES = (
    "preference",
    "identity_fact",
    "relationship_fact",
    "project_fact",
    "decision",
    "commitment",
    "routine",
    "constraint",
    "working_style",
)

MEMORY_CONFIRMATION_STATUSES = (
    "unconfirmed",
    "confirmed",
    "contested",
)

_MEMORY_TYPES_SQL = ", ".join(f"'{value}'" for value in MEMORY_TYPES)
_MEMORY_CONFIRMATION_STATUSES_SQL = ", ".join(
    f"'{value}'" for value in MEMORY_CONFIRMATION_STATUSES
)

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE memories
          ADD COLUMN memory_type text NOT NULL DEFAULT 'preference',
          ADD COLUMN confidence double precision NULL,
          ADD COLUMN salience double precision NULL,
          ADD COLUMN confirmation_status text NOT NULL DEFAULT 'unconfirmed',
          ADD COLUMN valid_from timestamptz NULL,
          ADD COLUMN valid_to timestamptz NULL,
          ADD COLUMN last_confirmed_at timestamptz NULL
        """,
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_memory_type_check
          CHECK (memory_type IN ({_MEMORY_TYPES_SQL}))
        """,
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_confirmation_status_check
          CHECK (confirmation_status IN ({_MEMORY_CONFIRMATION_STATUSES_SQL}))
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_confidence_range_check
          CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0))
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_salience_range_check
          CHECK (salience IS NULL OR (salience >= 0.0 AND salience <= 1.0))
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_valid_range_check
          CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from)
        """,
    """
        CREATE INDEX memories_user_type_updated_idx
          ON memories (user_id, memory_type, updated_at)
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS memories_user_type_updated_idx",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_valid_range_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_salience_range_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_confidence_range_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_confirmation_status_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_memory_type_check",
    "ALTER TABLE memories DROP COLUMN IF EXISTS last_confirmed_at",
    "ALTER TABLE memories DROP COLUMN IF EXISTS valid_to",
    "ALTER TABLE memories DROP COLUMN IF EXISTS valid_from",
    "ALTER TABLE memories DROP COLUMN IF EXISTS confirmation_status",
    "ALTER TABLE memories DROP COLUMN IF EXISTS salience",
    "ALTER TABLE memories DROP COLUMN IF EXISTS confidence",
    "ALTER TABLE memories DROP COLUMN IF EXISTS memory_type",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
