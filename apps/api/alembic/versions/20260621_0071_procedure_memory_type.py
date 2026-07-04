"""Allow procedure memories in the vNext memory kernel."""

from __future__ import annotations

from alembic import op


revision = "20260621_0071"
down_revision = "20260511_0070"
branch_labels = None
depends_on = None

LEGACY_MEMORY_TYPES = (
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

VNEXT_MEMORY_TYPES = (
    "episode",
    "semantic",
    "project_state",
    "decision",
    "belief",
    "thesis",
    "person",
    "relationship",
    "open_loop",
    "preference",
    "value",
    "pattern",
    "contradiction",
    "question",
    "answer",
    "artifact_summary",
    "agent_run",
    "system",
    "procedure",
)

UPGRADE_MEMORY_TYPES = tuple(dict.fromkeys((*LEGACY_MEMORY_TYPES, *VNEXT_MEMORY_TYPES)))
DOWNGRADE_MEMORY_TYPES = tuple(value for value in UPGRADE_MEMORY_TYPES if value != "procedure")

_UPGRADE_MEMORY_TYPES_SQL = ", ".join(f"'{value}'" for value in UPGRADE_MEMORY_TYPES)
_DOWNGRADE_MEMORY_TYPES_SQL = ", ".join(f"'{value}'" for value in DOWNGRADE_MEMORY_TYPES)

_UPGRADE_STATEMENTS = (
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_memory_type_check",
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_memory_type_check
          CHECK (memory_type IN ({_UPGRADE_MEMORY_TYPES_SQL}))
        """,
)

_DOWNGRADE_STATEMENTS = (
    "UPDATE memories SET memory_type = 'semantic' WHERE memory_type = 'procedure'",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_memory_type_check",
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_memory_type_check
          CHECK (memory_type IN ({_DOWNGRADE_MEMORY_TYPES_SQL}))
        """,
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
