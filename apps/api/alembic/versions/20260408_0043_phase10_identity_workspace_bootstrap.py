"""Add Phase 10 Sprint 1 hosted identity/workspace bootstrap control-plane tables."""

from __future__ import annotations

from alembic import op


revision = "20260408_0043"
down_revision = "20260330_0042"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE beta_cohorts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          cohort_key text NOT NULL UNIQUE,
          description text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT beta_cohorts_key_length_check
            CHECK (char_length(cohort_key) >= 1 AND char_length(cohort_key) <= 120)
        )
        """,
    """
        CREATE TABLE feature_flags (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          flag_key text NOT NULL,
          cohort_key text NULL REFERENCES beta_cohorts(cohort_key) ON DELETE SET NULL,
          enabled boolean NOT NULL DEFAULT false,
          description text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT feature_flags_key_length_check
            CHECK (char_length(flag_key) >= 1 AND char_length(flag_key) <= 120)
        )
        """,
    (
        "CREATE UNIQUE INDEX feature_flags_global_key_uidx "
        "ON feature_flags (flag_key) WHERE cohort_key IS NULL"
    ),
    (
        "CREATE UNIQUE INDEX feature_flags_scoped_key_uidx "
        "ON feature_flags (flag_key, cohort_key) WHERE cohort_key IS NOT NULL"
    ),
    (
        "CREATE INDEX feature_flags_enabled_idx "
        "ON feature_flags (enabled, flag_key, cohort_key)"
    ),
    """
        CREATE TABLE user_accounts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          email text NOT NULL UNIQUE,
          display_name text NULL,
          beta_cohort_key text NULL REFERENCES beta_cohorts(cohort_key) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT user_accounts_email_length_check
            CHECK (char_length(email) >= 3 AND char_length(email) <= 320)
        )
        """,
    """
        CREATE TABLE workspaces (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          owner_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          slug text NOT NULL UNIQUE,
          name text NOT NULL,
          bootstrap_status text NOT NULL DEFAULT 'pending',
          bootstrapped_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT workspaces_slug_length_check
            CHECK (char_length(slug) >= 3 AND char_length(slug) <= 120),
          CONSTRAINT workspaces_name_length_check
            CHECK (char_length(name) >= 1 AND char_length(name) <= 160),
          CONSTRAINT workspaces_bootstrap_status_check
            CHECK (bootstrap_status IN ('pending', 'ready'))
        )
        """,
    (
        "CREATE INDEX workspaces_owner_created_idx "
        "ON workspaces (owner_user_account_id, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE workspace_members (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          role text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (workspace_id, user_account_id),
          CONSTRAINT workspace_members_role_check
            CHECK (role IN ('owner', 'member'))
        )
        """,
    (
        "CREATE UNIQUE INDEX workspace_members_single_owner_uidx "
        "ON workspace_members (workspace_id) WHERE role = 'owner'"
    ),
    (
        "CREATE INDEX workspace_members_user_created_idx "
        "ON workspace_members (user_account_id, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE magic_link_challenges (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          email text NOT NULL,
          challenge_token_hash text NOT NULL UNIQUE,
          status text NOT NULL,
          expires_at timestamptz NOT NULL,
          consumed_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT magic_link_challenges_status_check
            CHECK (status IN ('pending', 'consumed', 'expired'))
        )
        """,
    (
        "CREATE INDEX magic_link_challenges_email_status_idx "
        "ON magic_link_challenges (email, status, expires_at DESC, created_at DESC)"
    ),
    """
        CREATE TABLE devices (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          workspace_id uuid NULL REFERENCES workspaces(id) ON DELETE SET NULL,
          device_key text NOT NULL,
          device_label text NOT NULL,
          status text NOT NULL DEFAULT 'active',
          last_seen_at timestamptz NULL,
          revoked_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (user_account_id, device_key),
          CONSTRAINT devices_status_check CHECK (status IN ('active', 'revoked')),
          CONSTRAINT devices_label_length_check
            CHECK (char_length(device_label) >= 1 AND char_length(device_label) <= 120)
        )
        """,
    (
        "CREATE INDEX devices_user_workspace_status_idx "
        "ON devices (user_account_id, workspace_id, status, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE device_link_challenges (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          workspace_id uuid NULL REFERENCES workspaces(id) ON DELETE SET NULL,
          device_key text NOT NULL,
          device_label text NOT NULL,
          challenge_token_hash text NOT NULL UNIQUE,
          status text NOT NULL,
          expires_at timestamptz NOT NULL,
          confirmed_at timestamptz NULL,
          device_id uuid NULL REFERENCES devices(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT device_link_challenges_status_check
            CHECK (status IN ('pending', 'confirmed', 'expired')),
          CONSTRAINT device_link_challenges_label_length_check
            CHECK (char_length(device_label) >= 1 AND char_length(device_label) <= 120)
        )
        """,
    (
        "CREATE INDEX device_link_challenges_user_device_status_idx "
        "ON device_link_challenges (user_account_id, device_key, status, expires_at DESC, created_at DESC)"
    ),
    """
        CREATE TABLE auth_sessions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          workspace_id uuid NULL REFERENCES workspaces(id) ON DELETE SET NULL,
          device_id uuid NULL REFERENCES devices(id) ON DELETE SET NULL,
          session_token_hash text NOT NULL UNIQUE,
          status text NOT NULL DEFAULT 'active',
          expires_at timestamptz NOT NULL,
          revoked_at timestamptz NULL,
          last_seen_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT auth_sessions_status_check
            CHECK (status IN ('active', 'revoked', 'expired'))
        )
        """,
    (
        "CREATE INDEX auth_sessions_user_status_idx "
        "ON auth_sessions (user_account_id, status, expires_at DESC, created_at DESC)"
    ),
    """
        CREATE TABLE user_preferences (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_account_id uuid NOT NULL UNIQUE REFERENCES user_accounts(id) ON DELETE CASCADE,
          timezone text NOT NULL DEFAULT 'UTC',
          brief_preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
          quiet_hours jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT user_preferences_timezone_length_check
            CHECK (char_length(timezone) >= 1 AND char_length(timezone) <= 120)
        )
        """,
    "INSERT INTO beta_cohorts (cohort_key, description) VALUES ('p10-beta', 'Phase 10 hosted beta cohort') ON CONFLICT (cohort_key) DO NOTHING",
    """
        INSERT INTO feature_flags (flag_key, cohort_key, enabled, description)
        VALUES
          ('hosted_onboarding', NULL, true, 'Hosted onboarding surface foundation'),
          ('hosted_settings', NULL, true, 'Hosted settings surface foundation'),
          ('telegram_linking', 'p10-beta', false, 'Reserved for P10-S2 Telegram linkage')
        ON CONFLICT DO NOTHING
        """,
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON beta_cohorts TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON feature_flags TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON user_accounts TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON workspaces TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON workspace_members TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON magic_link_challenges TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON devices TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON device_link_challenges TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON auth_sessions TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS user_preferences",
    "DROP TABLE IF EXISTS auth_sessions",
    "DROP TABLE IF EXISTS device_link_challenges",
    "DROP TABLE IF EXISTS devices",
    "DROP TABLE IF EXISTS magic_link_challenges",
    "DROP INDEX IF EXISTS workspace_members_single_owner_uidx",
    "DROP TABLE IF EXISTS workspace_members",
    "DROP TABLE IF EXISTS workspaces",
    "DROP TABLE IF EXISTS user_accounts",
    "DROP INDEX IF EXISTS feature_flags_scoped_key_uidx",
    "DROP INDEX IF EXISTS feature_flags_global_key_uidx",
    "DROP TABLE IF EXISTS feature_flags",
    "DROP TABLE IF EXISTS beta_cohorts",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
