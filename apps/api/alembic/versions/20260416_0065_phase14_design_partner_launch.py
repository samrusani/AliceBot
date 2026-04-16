"""Add Phase 14 design-partner launch tracking tables."""

from __future__ import annotations

from alembic import op


revision = "20260416_0065"
down_revision = "20260416_0064"
branch_labels = None
depends_on = None

_RLS_TABLES = (
    "design_partners",
    "design_partner_workspaces",
    "design_partner_feedback",
)

_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE design_partners (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          partner_key text NOT NULL UNIQUE,
          name text NOT NULL,
          lifecycle_stage text NOT NULL DEFAULT 'onboarding',
          onboarding_status text NOT NULL DEFAULT 'pending',
          support_status text NOT NULL DEFAULT 'green',
          instrumentation_status text NOT NULL DEFAULT 'not_ready',
          case_study_status text NOT NULL DEFAULT 'not_started',
          target_outcome text NULL,
          launch_notes text NULL,
          onboarding_checklist jsonb NOT NULL DEFAULT '{}'::jsonb,
          support_checklist jsonb NOT NULL DEFAULT '{}'::jsonb,
          success_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT design_partners_partner_key_length_check
            CHECK (char_length(partner_key) >= 1 AND char_length(partner_key) <= 120),
          CONSTRAINT design_partners_name_length_check
            CHECK (char_length(name) >= 1 AND char_length(name) <= 160),
          CONSTRAINT design_partners_lifecycle_stage_check
            CHECK (lifecycle_stage IN ('onboarding', 'pilot', 'active', 'paused', 'completed')),
          CONSTRAINT design_partners_onboarding_status_check
            CHECK (onboarding_status IN ('pending', 'in_progress', 'completed', 'blocked')),
          CONSTRAINT design_partners_support_status_check
            CHECK (support_status IN ('green', 'watch', 'needs_attention', 'blocked')),
          CONSTRAINT design_partners_instrumentation_status_check
            CHECK (instrumentation_status IN ('not_ready', 'partial', 'ready')),
          CONSTRAINT design_partners_case_study_status_check
            CHECK (case_study_status IN ('not_started', 'candidate', 'drafting', 'approved', 'published'))
        )
        """,
    (
        "CREATE INDEX design_partners_updated_idx "
        "ON design_partners (updated_at DESC, id DESC)"
    ),
    """
        CREATE TABLE design_partner_workspaces (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          design_partner_id uuid NOT NULL REFERENCES design_partners(id) ON DELETE CASCADE,
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          linked_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          linkage_status text NOT NULL DEFAULT 'pilot',
          environment_label text NOT NULL DEFAULT 'pilot',
          instrumentation_ready boolean NOT NULL DEFAULT false,
          notes text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (design_partner_id, workspace_id),
          UNIQUE (workspace_id),
          CONSTRAINT design_partner_workspaces_linkage_status_check
            CHECK (linkage_status IN ('pilot', 'active', 'paused')),
          CONSTRAINT design_partner_workspaces_environment_label_length_check
            CHECK (char_length(environment_label) >= 1 AND char_length(environment_label) <= 80)
        )
        """,
    (
        "CREATE INDEX design_partner_workspaces_partner_created_idx "
        "ON design_partner_workspaces (design_partner_id, created_at ASC, id ASC)"
    ),
    """
        CREATE TABLE design_partner_feedback (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          design_partner_id uuid NOT NULL REFERENCES design_partners(id) ON DELETE CASCADE,
          workspace_id uuid NULL REFERENCES workspaces(id) ON DELETE SET NULL,
          captured_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          source_kind text NOT NULL,
          category text NOT NULL,
          sentiment text NOT NULL,
          urgency text NOT NULL,
          feedback_status text NOT NULL DEFAULT 'new',
          case_study_signal boolean NOT NULL DEFAULT false,
          summary text NOT NULL,
          detail text NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT design_partner_feedback_source_kind_check
            CHECK (source_kind IN ('partner_call', 'email', 'slack', 'operator_note', 'survey', 'support_review')),
          CONSTRAINT design_partner_feedback_category_check
            CHECK (category IN ('bug', 'ux', 'capability_gap', 'onboarding', 'support', 'win')),
          CONSTRAINT design_partner_feedback_sentiment_check
            CHECK (sentiment IN ('positive', 'neutral', 'negative')),
          CONSTRAINT design_partner_feedback_urgency_check
            CHECK (urgency IN ('low', 'medium', 'high')),
          CONSTRAINT design_partner_feedback_status_check
            CHECK (feedback_status IN ('new', 'triaged', 'actioned', 'closed')),
          CONSTRAINT design_partner_feedback_summary_length_check
            CHECK (char_length(summary) >= 1 AND char_length(summary) <= 400)
        )
        """,
    (
        "CREATE INDEX design_partner_feedback_partner_created_idx "
        "ON design_partner_feedback (design_partner_id, created_at DESC, id DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON design_partners TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON design_partner_workspaces TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON design_partner_feedback TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENTS = (
    """
        CREATE POLICY design_partners_admin_access ON design_partners
          FOR ALL
          USING (app.hosted_access_bypass())
          WITH CHECK (app.hosted_access_bypass());
        """,
    """
        CREATE POLICY design_partner_workspaces_admin_access ON design_partner_workspaces
          FOR ALL
          USING (app.hosted_access_bypass())
          WITH CHECK (app.hosted_access_bypass());
        """,
    """
        CREATE POLICY design_partner_feedback_admin_access ON design_partner_feedback
          FOR ALL
          USING (app.hosted_access_bypass())
          WITH CHECK (app.hosted_access_bypass());
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS design_partner_feedback",
    "DROP TABLE IF EXISTS design_partner_workspaces",
    "DROP TABLE IF EXISTS design_partners",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    _execute_statements(_UPGRADE_POLICY_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)

