"""Bind each artifact quality rating to one reviewer row.

``artifact_quality_ratings`` has forced row-level security, while the migration
owner intentionally has no ``BYPASSRLS`` privilege. Bracketing the dedupe and
constraint creation with ``NO FORCE`` and ``FORCE`` lets that owner repair all
rows. Alembic runs the upgrade in one transaction, so concurrent sessions never
observe the relaxed policy; a failure rolls the bracket and all intervening
work back together.

Editing this revision in place is safe because no published release contains
0093. A database already stamped at 0093 does not rerun the body, and its
successful unique-constraint application proves the original dedupe left no
duplicate reviewer rows. Its final schema therefore already matches this
revision, including the idempotent trailing ``FORCE ROW LEVEL SECURITY``.

Revision ID: 20260721_0093
Revises: 20260716_0092
"""

from __future__ import annotations

from alembic import op


revision = "20260721_0093"
down_revision = "20260716_0092"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE artifact_quality_ratings NO FORCE ROW LEVEL SECURITY",
    """
    WITH ranked_ratings AS (
      SELECT
        id,
        row_number() OVER (
          PARTITION BY artifact_id, reviewer_id
          ORDER BY created_at DESC, id DESC
        ) AS row_number
      FROM artifact_quality_ratings
      WHERE reviewer_id IS NOT NULL
    )
    DELETE FROM artifact_quality_ratings AS rating
    USING ranked_ratings
    WHERE rating.id = ranked_ratings.id
      AND ranked_ratings.row_number > 1
    """,
    """
    ALTER TABLE artifact_quality_ratings
      ADD CONSTRAINT artifact_quality_ratings_artifact_reviewer_key
      UNIQUE (artifact_id, reviewer_id)
    """,
    "ALTER TABLE artifact_quality_ratings FORCE ROW LEVEL SECURITY",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE artifact_quality_ratings
          DROP CONSTRAINT IF EXISTS artifact_quality_ratings_artifact_reviewer_key
        """
    )
