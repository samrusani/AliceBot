"""Allow the memory_consolidation scheduler workflow type.

The research-informed memory upgrade registered a seventh scheduler
workflow, ``memory_consolidation``, in ``vnext_scheduler.WORKFLOW_TYPES``
without extending the check constraints created by ``20260511_0068``.
Ensuring default workflows then violated ``scheduler_workflows_type_check``
on any live Postgres store, crashing scheduler bootstrap.

Revision ID: 20260704_0074
Revises: 20260704_0073
"""

from __future__ import annotations

from alembic import op


revision = "20260704_0074"
down_revision = "20260704_0073"
branch_labels = None
depends_on = None


WORKFLOW_TYPES = (
    "daily_brief",
    "weekly_synthesis",
    "connection_report",
    "contradiction_report",
    "open_loop_review",
    "project_update_scan",
    "memory_consolidation",
)

LEGACY_WORKFLOW_TYPES = WORKFLOW_TYPES[:-1]

_TYPE_CHECKS = (
    ("scheduler_workflows", "scheduler_workflows_type_check"),
    ("scheduler_runs", "scheduler_runs_type_check"),
)


def _types_sql(workflow_types: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in workflow_types)


def upgrade() -> None:
    for table_name, constraint_name in _TYPE_CHECKS:
        op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")
        op.execute(
            f"""
            ALTER TABLE {table_name}
              ADD CONSTRAINT {constraint_name}
              CHECK (workflow_type IN ({_types_sql(WORKFLOW_TYPES)}))
            """
        )


def downgrade() -> None:
    op.execute("DELETE FROM scheduler_runs WHERE workflow_type = 'memory_consolidation'")
    op.execute(
        "DELETE FROM scheduler_workflows WHERE workflow_type = 'memory_consolidation'"
    )
    for table_name, constraint_name in _TYPE_CHECKS:
        op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")
        op.execute(
            f"""
            ALTER TABLE {table_name}
              ADD CONSTRAINT {constraint_name}
              CHECK (workflow_type IN ({_types_sql(LEGACY_WORKFLOW_TYPES)}))
            """
        )
