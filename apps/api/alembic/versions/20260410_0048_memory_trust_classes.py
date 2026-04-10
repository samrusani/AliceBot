"""Add trust classes and promotion metadata to typed memories."""

from __future__ import annotations

from alembic import op


revision = "20260410_0048"
down_revision = "20260409_0047"
branch_labels = None
depends_on = None

MEMORY_TRUST_CLASSES = (
    "deterministic",
    "llm_single_source",
    "llm_corroborated",
    "human_curated",
)

MEMORY_PROMOTION_ELIGIBILITIES = (
    "promotable",
    "not_promotable",
)

_MEMORY_TRUST_CLASSES_SQL = ", ".join(f"'{value}'" for value in MEMORY_TRUST_CLASSES)
_MEMORY_PROMOTION_ELIGIBILITIES_SQL = ", ".join(
    f"'{value}'" for value in MEMORY_PROMOTION_ELIGIBILITIES
)

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE memories
          ADD COLUMN trust_class text NOT NULL DEFAULT 'deterministic',
          ADD COLUMN promotion_eligibility text NOT NULL DEFAULT 'promotable',
          ADD COLUMN evidence_count integer NULL,
          ADD COLUMN independent_source_count integer NULL,
          ADD COLUMN extracted_by_model text NULL,
          ADD COLUMN trust_reason text NULL
        """,
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_trust_class_check
          CHECK (trust_class IN ({_MEMORY_TRUST_CLASSES_SQL}))
        """,
    f"""
        ALTER TABLE memories
          ADD CONSTRAINT memories_promotion_eligibility_check
          CHECK (promotion_eligibility IN ({_MEMORY_PROMOTION_ELIGIBILITIES_SQL}))
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_evidence_count_non_negative_check
          CHECK (evidence_count IS NULL OR evidence_count >= 0)
        """,
    """
        ALTER TABLE memories
          ADD CONSTRAINT memories_independent_source_count_non_negative_check
          CHECK (independent_source_count IS NULL OR independent_source_count >= 0)
        """,
    """
        CREATE INDEX memories_user_trust_class_updated_idx
          ON memories (user_id, trust_class, updated_at)
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS memories_user_trust_class_updated_idx",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_independent_source_count_non_negative_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_evidence_count_non_negative_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_promotion_eligibility_check",
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_trust_class_check",
    "ALTER TABLE memories DROP COLUMN IF EXISTS trust_reason",
    "ALTER TABLE memories DROP COLUMN IF EXISTS extracted_by_model",
    "ALTER TABLE memories DROP COLUMN IF EXISTS independent_source_count",
    "ALTER TABLE memories DROP COLUMN IF EXISTS evidence_count",
    "ALTER TABLE memories DROP COLUMN IF EXISTS promotion_eligibility",
    "ALTER TABLE memories DROP COLUMN IF EXISTS trust_class",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
