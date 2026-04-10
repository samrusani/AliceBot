"""Separate preservation, searchability, and promotability lifecycle flags."""

from __future__ import annotations

from alembic import op


revision = "20260410_0049"
down_revision = "20260410_0048"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    "ALTER TABLE continuity_objects ADD COLUMN is_preserved boolean NOT NULL DEFAULT TRUE",
    "ALTER TABLE continuity_objects ADD COLUMN is_searchable boolean NOT NULL DEFAULT TRUE",
    "ALTER TABLE continuity_objects ADD COLUMN is_promotable boolean NOT NULL DEFAULT TRUE",
    (
        "UPDATE continuity_objects "
        "SET is_searchable = CASE WHEN object_type = 'Note' THEN FALSE ELSE TRUE END, "
        "    is_promotable = CASE "
        "      WHEN object_type IN ('Decision', 'Commitment', 'WaitingFor', 'Blocker', 'NextAction') THEN TRUE "
        "      ELSE FALSE "
        "    END"
    ),
    (
        "CREATE INDEX continuity_objects_user_searchable_updated_idx "
        "ON continuity_objects (user_id, is_searchable, updated_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX continuity_objects_user_promotable_updated_idx "
        "ON continuity_objects (user_id, is_promotable, updated_at DESC, id DESC)"
    ),
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS continuity_objects_user_promotable_updated_idx",
    "DROP INDEX IF EXISTS continuity_objects_user_searchable_updated_idx",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS is_promotable",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS is_searchable",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS is_preserved",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
