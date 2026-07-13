"""Bound persistence and scheduler hot paths while preserving repaired data.

This follow-up is intentionally additive: v0.10.2 migrations are immutable.
Indexes are built concurrently so populated installations keep accepting
writes. PostgreSQL's original memories table never received its declared
status CHECK; add it as NOT VALID so future writes are constrained without a
monolithic historical rewrite. Operators may repair unknown legacy values in
bounded batches and validate the constraint in a later maintenance window.

Revision ID: 20260713_0087
Revises: 20260713_0086
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text as sql_text


revision = "20260713_0087"
down_revision = "20260713_0086"
branch_labels = None
depends_on = None


MEMORY_STATUSES = (
    # The shared ``memories`` table still serves the legacy memory API, whose
    # tombstone transition writes ``deleted`` while retaining the row for
    # revision/audit history.  The table-level constraint must therefore cover
    # the union of legacy and vNext lifecycle vocabularies.
    "deleted",
    "candidate",
    "active",
    "accepted",
    "rejected",
    "superseded",
    "stale",
    "archived",
    "needs_review",
    "private_only",
)


_CONCURRENT_INDEX_STATEMENTS: tuple[str, ...] = (
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS sources_user_content_hash_idx
      ON sources (user_id, content_hash)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_user_live_canonical_text_idx
      ON memories (user_id, md5(lower(canonical_text)), domain, sensitivity)
      WHERE deleted_at IS NULL
        AND canonical_text IS NOT NULL
        AND status IN ('candidate', 'active', 'accepted', 'needs_review', 'private_only')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_user_pending_confirmation_idx
      ON memories (user_id, updated_at DESC, id DESC)
      WHERE deleted_at IS NULL
        AND status = 'needs_review'
        AND confirmation_status = 'unconfirmed'
        AND metadata_json #>> '{agentic_memory,confirmation,status}' = 'pending'
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_user_staleness_confirmation_idx
      ON memories (
        user_id,
        memory_type,
        COALESCE(last_confirmed_at, last_seen_at, created_at)
      )
      WHERE deleted_at IS NULL
        AND status = 'active'
        AND memory_type IN ('open_loop', 'commitment', 'project_state')
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_user_project_staleness_idx
      ON memories (
        user_id,
        project_id,
        memory_type,
        COALESCE(last_confirmed_at, last_seen_at, created_at)
      )
      WHERE deleted_at IS NULL
        AND status = 'active'
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_user_project_rollup_digest_idx
      ON memories (
        user_id,
        project_id,
        (metadata_json ->> 'candidate_kind'),
        (metadata_json ->> 'rollup_digest'),
        updated_at DESC,
        id DESC
      )
      WHERE deleted_at IS NULL
        AND status = 'candidate'
        AND metadata_json ->> 'rollup_digest' IS NOT NULL
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS memories_user_project_rollup_key_idx
      ON memories (
        user_id,
        project_id,
        (metadata_json ->> 'candidate_kind'),
        (metadata_json ->> 'rollup_key'),
        updated_at DESC,
        id DESC
      )
      WHERE deleted_at IS NULL
        AND status IN ('active', 'accepted')
        AND metadata_json ->> 'rollup_key' IS NOT NULL
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS generated_artifacts_user_workflow_digest_idx
      ON generated_artifacts (
        user_id,
        artifact_type,
        (metadata_json ->> 'workflow'),
        (COALESCE(
          metadata_json ->> 'automation_digest',
          metadata_json ->> 'consolidation_digest'
        )),
        created_at DESC,
        id DESC
      )
      WHERE COALESCE(
        metadata_json ->> 'automation_digest',
        metadata_json ->> 'consolidation_digest'
      ) IS NOT NULL
    """,
    """
    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS generated_artifacts_user_idempotency_digest_uidx
      ON generated_artifacts (
        user_id,
        artifact_type,
        (metadata_json ->> 'workflow'),
        (metadata_json ->> 'idempotency_digest')
      )
      WHERE metadata_json ->> 'idempotency_digest' IS NOT NULL
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS open_loops_user_automation_digest_idx
      ON open_loops (
        user_id,
        (metadata_json ->> 'automation_digest'),
        project_id,
        person_id,
        created_at DESC,
        id DESC
      )
      WHERE metadata_json ->> 'automation_digest' IS NOT NULL
    """,
    """
    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS open_loops_user_idempotency_digest_uidx
      ON open_loops (user_id, (metadata_json ->> 'idempotency_digest'))
      WHERE metadata_json ->> 'idempotency_digest' IS NOT NULL
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS event_log_user_occurred_idx
      ON event_log (user_id, occurred_at DESC, id DESC)
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS task_queue_user_pending_claim_idx
      ON task_queue (
        user_id,
        scheduled_for ASC NULLS FIRST,
        created_at ASC,
        id ASC
      )
      WHERE status = 'pending'
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS scheduler_workflows_user_due_claim_idx
      ON scheduler_workflows (
        user_id,
        next_run_at ASC,
        claim_expires_at ASC,
        workflow_type ASC,
        id ASC
      )
      WHERE enabled = true AND paused = false AND next_run_at IS NOT NULL
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS scheduler_runs_user_expired_claim_idx
      ON scheduler_runs (user_id, claim_expires_at ASC, id ASC)
      WHERE status = 'started' AND claim_token IS NOT NULL
    """,
)


_CONCURRENT_INDEX_NAMES: tuple[str, ...] = (
    "sources_user_content_hash_idx",
    "memories_user_live_canonical_text_idx",
    "memories_user_pending_confirmation_idx",
    "memories_user_staleness_confirmation_idx",
    "memories_user_project_staleness_idx",
    "memories_user_project_rollup_digest_idx",
    "memories_user_project_rollup_key_idx",
    "generated_artifacts_user_workflow_digest_idx",
    "generated_artifacts_user_idempotency_digest_uidx",
    "open_loops_user_automation_digest_idx",
    "open_loops_user_idempotency_digest_uidx",
    "event_log_user_occurred_idx",
    "task_queue_user_pending_claim_idx",
    "scheduler_workflows_user_due_claim_idx",
    "scheduler_runs_user_expired_claim_idx",
)


_INDEX_INVALIDITY_QUERY = """
    SELECT NOT index_metadata.indisvalid
    FROM pg_catalog.pg_class AS index_class
    JOIN pg_catalog.pg_index AS index_metadata
      ON index_metadata.indexrelid = index_class.oid
    JOIN pg_catalog.pg_namespace AS index_namespace
      ON index_namespace.oid = index_class.relnamespace
    WHERE index_class.relkind = 'i'
      AND index_namespace.nspname = current_schema()
      AND index_class.relname = :index_name
    """


_UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    ALTER TABLE scheduler_workflows
      ADD COLUMN IF NOT EXISTS claim_token text NULL
    """,
    """
    ALTER TABLE scheduler_workflows
      ADD COLUMN IF NOT EXISTS claim_version bigint NOT NULL DEFAULT 0
    """,
    """
    ALTER TABLE scheduler_workflows
      ADD COLUMN IF NOT EXISTS claim_expires_at timestamptz NULL
    """,
    """
    DO $migration$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conrelid = 'scheduler_workflows'::regclass
          AND conname = 'scheduler_workflows_claim_version_non_negative_check'
      ) THEN
        ALTER TABLE scheduler_workflows
          ADD CONSTRAINT scheduler_workflows_claim_version_non_negative_check
          CHECK (claim_version >= 0);
      END IF;
    END
    $migration$
    """,
    """
    ALTER TABLE scheduler_runs
      ADD COLUMN IF NOT EXISTS claim_token text NULL
    """,
    """
    ALTER TABLE scheduler_runs
      ADD COLUMN IF NOT EXISTS claim_version bigint NOT NULL DEFAULT 0
    """,
    """
    ALTER TABLE scheduler_runs
      ADD COLUMN IF NOT EXISTS claim_expires_at timestamptz NULL
    """,
    """
    ALTER TABLE scheduler_runs
      ADD COLUMN IF NOT EXISTS scheduled_for timestamptz NULL
    """,
    """
    DO $migration$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conrelid = 'scheduler_runs'::regclass
          AND conname = 'scheduler_runs_claim_version_non_negative_check'
      ) THEN
        ALTER TABLE scheduler_runs
          ADD CONSTRAINT scheduler_runs_claim_version_non_negative_check
          CHECK (claim_version >= 0);
      END IF;
    END
    $migration$
    """,
    """
    DO $migration$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conrelid = 'scheduler_runs'::regclass
          AND conname = 'scheduler_runs_claim_shape_check'
      ) THEN
        ALTER TABLE scheduler_runs
          ADD CONSTRAINT scheduler_runs_claim_shape_check
          CHECK (
            (claim_token IS NULL AND claim_expires_at IS NULL)
            OR (claim_token IS NOT NULL AND claim_expires_at IS NOT NULL)
          );
      END IF;
    END
    $migration$
    """,
    f"""
    DO $migration$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conrelid = 'memories'::regclass
          AND conname = 'memories_status_check'
      ) THEN
        ALTER TABLE memories
          ADD CONSTRAINT memories_status_check
          CHECK (status IN ({", ".join(repr(value) for value in MEMORY_STATUSES)}))
          NOT VALID;
      END IF;
    END
    $migration$
    """,
)


_DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_status_check",
    "ALTER TABLE scheduler_runs DROP CONSTRAINT IF EXISTS scheduler_runs_claim_shape_check",
    "ALTER TABLE scheduler_runs DROP CONSTRAINT IF EXISTS scheduler_runs_claim_version_non_negative_check",
    "ALTER TABLE scheduler_runs DROP COLUMN IF EXISTS scheduled_for",
    "ALTER TABLE scheduler_runs DROP COLUMN IF EXISTS claim_expires_at",
    "ALTER TABLE scheduler_runs DROP COLUMN IF EXISTS claim_version",
    "ALTER TABLE scheduler_runs DROP COLUMN IF EXISTS claim_token",
    "ALTER TABLE scheduler_workflows DROP CONSTRAINT IF EXISTS scheduler_workflows_claim_version_non_negative_check",
    "ALTER TABLE scheduler_workflows DROP COLUMN IF EXISTS claim_expires_at",
    "ALTER TABLE scheduler_workflows DROP COLUMN IF EXISTS claim_version",
    "ALTER TABLE scheduler_workflows DROP COLUMN IF EXISTS claim_token",
)


_CONCURRENT_DOWNGRADE_STATEMENTS: tuple[str, ...] = tuple(
    statement
    for statement in (
        "DROP INDEX CONCURRENTLY IF EXISTS scheduler_runs_user_expired_claim_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS scheduler_workflows_user_due_claim_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS task_queue_user_pending_claim_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS event_log_user_occurred_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS open_loops_user_idempotency_digest_uidx",
        "DROP INDEX CONCURRENTLY IF EXISTS open_loops_user_automation_digest_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS generated_artifacts_user_idempotency_digest_uidx",
        "DROP INDEX CONCURRENTLY IF EXISTS generated_artifacts_user_workflow_digest_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS memories_user_project_rollup_key_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS memories_user_project_rollup_digest_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS memories_user_project_staleness_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS memories_user_staleness_confirmation_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS memories_user_pending_confirmation_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS memories_user_live_canonical_text_idx",
        "DROP INDEX CONCURRENTLY IF EXISTS sources_user_content_hash_idx",
    )
)


def _index_is_invalid(index_name: str) -> bool:
    """Detect catalog rows left unusable by an interrupted concurrent build."""

    invalid = (
        op.get_bind()
        .execute(
            sql_text(_INDEX_INVALIDITY_QUERY),
            {"index_name": index_name},
        )
        .scalar_one_or_none()
    )
    return invalid is True


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)
    with op.get_context().autocommit_block():
        for index_name, statement in zip(
            _CONCURRENT_INDEX_NAMES,
            _CONCURRENT_INDEX_STATEMENTS,
            strict=True,
        ):
            # PostgreSQL retains an invalid catalog row when a concurrent
            # build is cancelled or fails. CREATE ... IF NOT EXISTS would
            # otherwise skip that unusable index and let the migration pass.
            if _index_is_invalid(index_name):
                op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")
            op.execute(statement)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for statement in _CONCURRENT_DOWNGRADE_STATEMENTS:
            op.execute(statement)
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
