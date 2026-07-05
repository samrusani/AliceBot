"""Allow the memory_consolidation artifact type.

The consolidation service persists its review-only report with
``artifact_type="memory_consolidation"``, but the CHECK constraint
``generated_artifacts_type_check`` created by ``20260510_0067`` never
learned the value — migrations 0074/0075 extended the scheduler
workflow-type checks for this workflow while the artifact vocabulary was
missed, so ``generate_memory_consolidation`` raised CheckViolation on any
migrated Postgres store. Same bug family as 0074; only live-Postgres
execution catches it (the SQLite on-ramp has no generated_artifacts
table, and unit tests use fakes).

Revision ID: 20260706_0080
Revises: 20260706_0079
"""

from __future__ import annotations

from alembic import op


revision = "20260706_0080"
down_revision = "20260706_0079"
branch_labels = None
depends_on = None


ARTIFACT_TYPES = (
    "daily_brief",
    "weekly_synthesis",
    "monthly_distillation",
    "connection_report",
    "contradiction_report",
    "project_update",
    "thesis_report",
    "open_loop_report",
    "queue_result",
    "research_brief",
    "draft",
    "context_pack",
    "agent_resumption_brief",
    "system_report",
    "memory_consolidation",
)

LEGACY_ARTIFACT_TYPES = ARTIFACT_TYPES[:-1]

_CONSTRAINT = ("generated_artifacts", "generated_artifacts_type_check")


def _types_sql(artifact_types: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in artifact_types)


def upgrade() -> None:
    table_name, constraint_name = _CONSTRAINT
    op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")
    op.execute(
        f"""
        ALTER TABLE {table_name}
          ADD CONSTRAINT {constraint_name}
          CHECK (artifact_type IN ({_types_sql(ARTIFACT_TYPES)}))
        """
    )


def downgrade() -> None:
    table_name, constraint_name = _CONSTRAINT
    op.execute(
        "DELETE FROM generated_artifacts WHERE artifact_type = 'memory_consolidation'"
    )
    op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")
    op.execute(
        f"""
        ALTER TABLE {table_name}
          ADD CONSTRAINT {constraint_name}
          CHECK (artifact_type IN ({_types_sql(LEGACY_ARTIFACT_TYPES)}))
        """
    )
