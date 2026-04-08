"""Add Phase 10 Sprint 4 daily brief jobs, notification subscriptions, and scheduled receipt metadata."""

from __future__ import annotations

from alembic import op


revision = "20260408_0046"
down_revision = "20260408_0045"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE notification_subscriptions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_type text NOT NULL,
          channel_identity_id uuid NOT NULL REFERENCES channel_identities(id) ON DELETE CASCADE,
          notifications_enabled boolean NOT NULL DEFAULT TRUE,
          daily_brief_enabled boolean NOT NULL DEFAULT TRUE,
          daily_brief_window_start text NOT NULL DEFAULT '07:00',
          open_loop_prompts_enabled boolean NOT NULL DEFAULT TRUE,
          waiting_for_prompts_enabled boolean NOT NULL DEFAULT TRUE,
          stale_prompts_enabled boolean NOT NULL DEFAULT TRUE,
          timezone text NOT NULL DEFAULT 'UTC',
          quiet_hours_enabled boolean NOT NULL DEFAULT FALSE,
          quiet_hours_start text NOT NULL DEFAULT '22:00',
          quiet_hours_end text NOT NULL DEFAULT '07:00',
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (workspace_id, channel_type),
          UNIQUE (channel_identity_id, channel_type),
          CONSTRAINT notification_subscriptions_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT notification_subscriptions_window_start_format_check
            CHECK (daily_brief_window_start ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'),
          CONSTRAINT notification_subscriptions_quiet_start_format_check
            CHECK (quiet_hours_start ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'),
          CONSTRAINT notification_subscriptions_quiet_end_format_check
            CHECK (quiet_hours_end ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
        )
        """,
    (
        "CREATE INDEX notification_subscriptions_workspace_updated_idx "
        "ON notification_subscriptions (workspace_id, channel_type, updated_at DESC, id DESC)"
    ),
    """
        CREATE TABLE continuity_briefs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_type text NOT NULL,
          channel_identity_id uuid NOT NULL REFERENCES channel_identities(id) ON DELETE CASCADE,
          brief_kind text NOT NULL,
          assembly_version text NOT NULL,
          summary jsonb NOT NULL DEFAULT '{}'::jsonb,
          brief_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          message_text text NOT NULL,
          compiled_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT continuity_briefs_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT continuity_briefs_kind_check
            CHECK (brief_kind IN ('daily_brief'))
        )
        """,
    (
        "CREATE INDEX continuity_briefs_workspace_compiled_idx "
        "ON continuity_briefs (workspace_id, channel_type, compiled_at DESC, id DESC)"
    ),
    """
        CREATE TABLE daily_brief_jobs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_type text NOT NULL,
          channel_identity_id uuid NOT NULL REFERENCES channel_identities(id) ON DELETE CASCADE,
          job_kind text NOT NULL,
          prompt_kind text NULL,
          prompt_id text NULL,
          continuity_object_id uuid NULL REFERENCES continuity_objects(id) ON DELETE SET NULL,
          continuity_brief_id uuid NULL REFERENCES continuity_briefs(id) ON DELETE SET NULL,
          schedule_slot text NOT NULL,
          idempotency_key text NOT NULL,
          due_at timestamptz NOT NULL,
          status text NOT NULL,
          suppression_reason text NULL,
          attempt_count integer NOT NULL DEFAULT 0,
          delivery_receipt_id uuid NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          result_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          attempted_at timestamptz NULL,
          completed_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT daily_brief_jobs_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT daily_brief_jobs_kind_check
            CHECK (job_kind IN ('daily_brief', 'open_loop_prompt')),
          CONSTRAINT daily_brief_jobs_prompt_kind_check
            CHECK (prompt_kind IS NULL OR prompt_kind IN ('waiting_for', 'stale')),
          CONSTRAINT daily_brief_jobs_status_check
            CHECK (
              status IN (
                'scheduled',
                'delivered',
                'simulated',
                'suppressed_quiet_hours',
                'suppressed_disabled',
                'suppressed_outside_window',
                'failed'
              )
            ),
          CONSTRAINT daily_brief_jobs_attempt_count_check
            CHECK (attempt_count >= 0),
          CONSTRAINT daily_brief_jobs_prompt_required_for_open_loop_check
            CHECK (
              (job_kind = 'daily_brief' AND prompt_id IS NULL)
              OR
              (job_kind = 'open_loop_prompt' AND prompt_id IS NOT NULL)
            ),
          CONSTRAINT daily_brief_jobs_workspace_idempotency_unique
            UNIQUE (workspace_id, channel_type, idempotency_key)
        )
        """,
    (
        "CREATE INDEX daily_brief_jobs_workspace_due_idx "
        "ON daily_brief_jobs (workspace_id, channel_type, due_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX daily_brief_jobs_workspace_status_due_idx "
        "ON daily_brief_jobs (workspace_id, channel_type, status, due_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX daily_brief_jobs_workspace_prompt_slot_idx "
        "ON daily_brief_jobs (workspace_id, prompt_id, schedule_slot, created_at DESC, id DESC)"
    ),
    "ALTER TABLE channel_delivery_receipts DROP CONSTRAINT IF EXISTS channel_delivery_receipts_status_check",
    """
        ALTER TABLE channel_delivery_receipts
        ADD CONSTRAINT channel_delivery_receipts_status_check
        CHECK (status IN ('delivered', 'failed', 'simulated', 'suppressed'))
        """,
    """
        ALTER TABLE channel_delivery_receipts
        ADD COLUMN scheduled_job_id uuid NULL REFERENCES daily_brief_jobs(id) ON DELETE SET NULL,
        ADD COLUMN scheduler_job_kind text NULL,
        ADD COLUMN scheduled_for timestamptz NULL,
        ADD COLUMN schedule_slot text NULL,
        ADD COLUMN notification_policy jsonb NOT NULL DEFAULT '{}'::jsonb
        """,
    """
        ALTER TABLE channel_delivery_receipts
        ADD CONSTRAINT channel_delivery_receipts_scheduler_job_kind_check
        CHECK (scheduler_job_kind IS NULL OR scheduler_job_kind IN ('daily_brief', 'open_loop_prompt'))
        """,
    (
        "CREATE INDEX channel_delivery_receipts_workspace_scheduler_idx "
        "ON channel_delivery_receipts (workspace_id, scheduled_for DESC, id DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON notification_subscriptions TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON continuity_briefs TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON daily_brief_jobs TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS channel_delivery_receipts_workspace_scheduler_idx",
    "ALTER TABLE channel_delivery_receipts DROP CONSTRAINT IF EXISTS channel_delivery_receipts_scheduler_job_kind_check",
    """
        ALTER TABLE channel_delivery_receipts
        DROP COLUMN IF EXISTS notification_policy,
        DROP COLUMN IF EXISTS schedule_slot,
        DROP COLUMN IF EXISTS scheduled_for,
        DROP COLUMN IF EXISTS scheduler_job_kind,
        DROP COLUMN IF EXISTS scheduled_job_id
        """,
    "ALTER TABLE channel_delivery_receipts DROP CONSTRAINT IF EXISTS channel_delivery_receipts_status_check",
    """
        UPDATE channel_delivery_receipts
        SET status = 'failed',
            failure_code = COALESCE(failure_code, 'suppressed_status_downgrade'),
            failure_detail = COALESCE(failure_detail, 'suppressed receipt downgraded during migration rollback')
        WHERE status = 'suppressed'
        """,
    """
        ALTER TABLE channel_delivery_receipts
        ADD CONSTRAINT channel_delivery_receipts_status_check
        CHECK (status IN ('delivered', 'failed', 'simulated'))
        """,
    "DROP INDEX IF EXISTS daily_brief_jobs_workspace_prompt_slot_idx",
    "DROP INDEX IF EXISTS daily_brief_jobs_workspace_status_due_idx",
    "DROP INDEX IF EXISTS daily_brief_jobs_workspace_due_idx",
    "DROP TABLE IF EXISTS daily_brief_jobs",
    "DROP INDEX IF EXISTS continuity_briefs_workspace_compiled_idx",
    "DROP TABLE IF EXISTS continuity_briefs",
    "DROP INDEX IF EXISTS notification_subscriptions_workspace_updated_idx",
    "DROP TABLE IF EXISTS notification_subscriptions",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
