"""Staleness write path: expiry-sweep indexes and the staleness_sweep workflow.

The staleness upgrade adds a ``stale`` value to the vNext memory status
vocabulary and a daily ``staleness_sweep`` scheduler workflow. On Postgres the
``memories`` table carries NO status CHECK constraint: migration
``20260510_0067`` defined ``MEMORY_STATUSES`` (and built
``_MEMORY_STATUSES_SQL``) but never attached a constraint to
``memories.status``, so allowing ``stale`` requires no constraint change here.
The SQLite schema's status CHECK is maintained separately in
``sqlite_schema.py``.

This migration therefore only:

* adds a partial index on ``memories (user_id, valid_to)`` where ``valid_to``
  is set, to support expiry sweeps;
* documents that a ``(user_id, status)``-leading index already exists
  (``memories_user_status_updated_idx`` from ``20260311_0004`` covers
  ``(user_id, status, updated_at)``), so no new status index is created;
* extends ``scheduler_workflows_type_check`` and
  ``scheduler_runs_type_check`` to allow the new ``staleness_sweep`` workflow
  type registered in ``vnext_scheduler.WORKFLOW_TYPES`` (same pattern as
  ``20260704_0074``).

Revision ID: 20260704_0075
Revises: 20260704_0074
"""

from __future__ import annotations

from alembic import op


revision = "20260704_0075"
down_revision = "20260704_0074"
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
    "staleness_sweep",
)

LEGACY_WORKFLOW_TYPES = WORKFLOW_TYPES[:-1]

_TYPE_CHECKS = (
    ("scheduler_workflows", "scheduler_workflows_type_check"),
    ("scheduler_runs", "scheduler_runs_type_check"),
)

_VALID_TO_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS memories_user_valid_to_expiry_idx
      ON memories (user_id, valid_to)
      WHERE valid_to IS NOT NULL
    """

_DROP_VALID_TO_INDEX_SQL = "DROP INDEX IF EXISTS memories_user_valid_to_expiry_idx"


def _types_sql(workflow_types: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in workflow_types)


def upgrade() -> None:
    op.execute(_VALID_TO_INDEX_SQL)
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
    op.execute("DELETE FROM scheduler_runs WHERE workflow_type = 'staleness_sweep'")
    op.execute(
        "DELETE FROM scheduler_workflows WHERE workflow_type = 'staleness_sweep'"
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
    op.execute(_DROP_VALID_TO_INDEX_SQL)
