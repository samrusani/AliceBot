"""Add Phase 10 Sprint 5 beta hardening telemetry and evidence fields."""

from __future__ import annotations

from alembic import op


revision = "20260409_0047"
down_revision = "20260408_0046"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE chat_telemetry (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          workspace_id uuid NULL REFERENCES workspaces(id) ON DELETE SET NULL,
          channel_message_id uuid NULL REFERENCES channel_messages(id) ON DELETE SET NULL,
          daily_brief_job_id uuid NULL REFERENCES daily_brief_jobs(id) ON DELETE SET NULL,
          delivery_receipt_id uuid NULL REFERENCES channel_delivery_receipts(id) ON DELETE SET NULL,
          flow_kind text NOT NULL,
          event_kind text NOT NULL,
          status text NOT NULL,
          route_path text NOT NULL,
          rollout_flag_key text NULL,
          rollout_flag_state text NULL,
          rate_limit_key text NULL,
          rate_limit_window_seconds integer NULL,
          rate_limit_max_requests integer NULL,
          retry_after_seconds integer NULL,
          abuse_signal text NULL,
          evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chat_telemetry_flow_kind_check
            CHECK (flow_kind IN ('chat_handle', 'scheduler_daily_brief', 'scheduler_open_loop_prompt')),
          CONSTRAINT chat_telemetry_event_kind_check
            CHECK (event_kind IN ('attempt', 'result', 'rollout_block', 'rate_limited', 'abuse_block', 'incident')),
          CONSTRAINT chat_telemetry_status_check
            CHECK (
              status IN (
                'ok',
                'failed',
                'blocked_rollout',
                'rate_limited',
                'abuse_blocked',
                'suppressed',
                'simulated',
                'delivered'
              )
            ),
          CONSTRAINT chat_telemetry_route_path_length_check
            CHECK (char_length(route_path) >= 1 AND char_length(route_path) <= 200),
          CONSTRAINT chat_telemetry_rate_limit_window_positive_check
            CHECK (rate_limit_window_seconds IS NULL OR rate_limit_window_seconds > 0),
          CONSTRAINT chat_telemetry_rate_limit_max_positive_check
            CHECK (rate_limit_max_requests IS NULL OR rate_limit_max_requests > 0),
          CONSTRAINT chat_telemetry_retry_after_non_negative_check
            CHECK (retry_after_seconds IS NULL OR retry_after_seconds >= 0)
        )
        """,
    (
        "CREATE INDEX chat_telemetry_workspace_created_idx "
        "ON chat_telemetry (workspace_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX chat_telemetry_flow_status_created_idx "
        "ON chat_telemetry (flow_kind, status, created_at DESC, id DESC)"
    ),
    """
        ALTER TABLE workspaces
        ADD COLUMN support_status text NOT NULL DEFAULT 'healthy',
        ADD COLUMN support_notes jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN onboarding_last_error_code text NULL,
        ADD COLUMN onboarding_last_error_detail text NULL,
        ADD COLUMN onboarding_last_error_at timestamptz NULL,
        ADD COLUMN onboarding_error_count integer NOT NULL DEFAULT 0,
        ADD COLUMN rollout_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN rate_limit_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN incident_evidence jsonb NOT NULL DEFAULT '{}'::jsonb
        """,
    """
        ALTER TABLE workspaces
        ADD CONSTRAINT workspaces_support_status_check
          CHECK (support_status IN ('healthy', 'needs_attention', 'blocked'))
        """,
    """
        ALTER TABLE workspaces
        ADD CONSTRAINT workspaces_onboarding_error_count_non_negative_check
          CHECK (onboarding_error_count >= 0)
        """,
    (
        "CREATE INDEX workspaces_support_status_updated_idx "
        "ON workspaces (support_status, updated_at DESC, id DESC)"
    ),
    """
        ALTER TABLE channel_delivery_receipts
        ADD COLUMN rollout_flag_state text NOT NULL DEFAULT 'enabled',
        ADD COLUMN support_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN rate_limit_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN incident_evidence jsonb NOT NULL DEFAULT '{}'::jsonb
        """,
    """
        ALTER TABLE channel_delivery_receipts
        ADD CONSTRAINT channel_delivery_receipts_rollout_flag_state_check
          CHECK (rollout_flag_state IN ('enabled', 'blocked'))
        """,
    (
        "CREATE INDEX channel_delivery_receipts_rollout_recorded_idx "
        "ON channel_delivery_receipts (rollout_flag_state, recorded_at DESC, id DESC)"
    ),
    """
        ALTER TABLE daily_brief_jobs
        ADD COLUMN rollout_flag_state text NOT NULL DEFAULT 'enabled',
        ADD COLUMN support_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN rate_limit_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN incident_evidence jsonb NOT NULL DEFAULT '{}'::jsonb
        """,
    """
        ALTER TABLE daily_brief_jobs
        ADD CONSTRAINT daily_brief_jobs_rollout_flag_state_check
          CHECK (rollout_flag_state IN ('enabled', 'blocked'))
        """,
    (
        "CREATE INDEX daily_brief_jobs_rollout_due_idx "
        "ON daily_brief_jobs (rollout_flag_state, due_at DESC, id DESC)"
    ),
    """
        INSERT INTO beta_cohorts (cohort_key, description)
        VALUES ('p10-ops', 'Phase 10 hosted beta operator cohort')
        ON CONFLICT (cohort_key) DO NOTHING
        """,
    """
        INSERT INTO feature_flags (flag_key, cohort_key, enabled, description)
        VALUES
          ('hosted_admin_read', 'p10-beta', true, 'Hosted admin visibility for beta operations'),
          ('hosted_chat_handle_enabled', 'p10-beta', true, 'Rollout gate for hosted telegram chat handling'),
          ('hosted_scheduler_delivery_enabled', 'p10-beta', true, 'Rollout gate for hosted scheduler-driven deliveries'),
          ('hosted_abuse_controls_enabled', 'p10-beta', true, 'Enable hosted abuse controls for chat and scheduler paths'),
          ('hosted_rate_limits_enabled', 'p10-beta', true, 'Enable hosted rate limiting controls'),
          ('hosted_admin_read', 'p10-ops', true, 'Hosted admin visibility for beta operators'),
          ('hosted_admin_operator', 'p10-ops', true, 'Hosted admin operator authorization'),
          ('hosted_chat_handle_enabled', 'p10-ops', true, 'Rollout gate for hosted telegram chat handling'),
          ('hosted_scheduler_delivery_enabled', 'p10-ops', true, 'Rollout gate for hosted scheduler-driven deliveries'),
          ('hosted_abuse_controls_enabled', 'p10-ops', true, 'Enable hosted abuse controls for chat and scheduler paths'),
          ('hosted_rate_limits_enabled', 'p10-ops', true, 'Enable hosted rate limiting controls')
        ON CONFLICT DO NOTHING
        """,
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON chat_telemetry TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS daily_brief_jobs_rollout_due_idx",
    "ALTER TABLE daily_brief_jobs DROP CONSTRAINT IF EXISTS daily_brief_jobs_rollout_flag_state_check",
    """
        ALTER TABLE daily_brief_jobs
        DROP COLUMN IF EXISTS incident_evidence,
        DROP COLUMN IF EXISTS rate_limit_evidence,
        DROP COLUMN IF EXISTS support_evidence,
        DROP COLUMN IF EXISTS rollout_flag_state
        """,
    "DROP INDEX IF EXISTS channel_delivery_receipts_rollout_recorded_idx",
    "ALTER TABLE channel_delivery_receipts DROP CONSTRAINT IF EXISTS channel_delivery_receipts_rollout_flag_state_check",
    """
        ALTER TABLE channel_delivery_receipts
        DROP COLUMN IF EXISTS incident_evidence,
        DROP COLUMN IF EXISTS rate_limit_evidence,
        DROP COLUMN IF EXISTS support_evidence,
        DROP COLUMN IF EXISTS rollout_flag_state
        """,
    "DROP INDEX IF EXISTS workspaces_support_status_updated_idx",
    "ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS workspaces_onboarding_error_count_non_negative_check",
    "ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS workspaces_support_status_check",
    """
        ALTER TABLE workspaces
        DROP COLUMN IF EXISTS incident_evidence,
        DROP COLUMN IF EXISTS rate_limit_evidence,
        DROP COLUMN IF EXISTS rollout_evidence,
        DROP COLUMN IF EXISTS onboarding_error_count,
        DROP COLUMN IF EXISTS onboarding_last_error_at,
        DROP COLUMN IF EXISTS onboarding_last_error_detail,
        DROP COLUMN IF EXISTS onboarding_last_error_code,
        DROP COLUMN IF EXISTS support_notes,
        DROP COLUMN IF EXISTS support_status
        """,
    "DROP INDEX IF EXISTS chat_telemetry_flow_status_created_idx",
    "DROP INDEX IF EXISTS chat_telemetry_workspace_created_idx",
    "DROP TABLE IF EXISTS chat_telemetry",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
