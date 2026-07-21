"""Bind each artifact quality rating to one reviewer row.

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
