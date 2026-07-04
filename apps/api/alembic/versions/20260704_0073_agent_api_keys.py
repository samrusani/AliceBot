"""Add per-agent API keys for real agent authentication.

Agent identity was previously self-asserted by callers. This table stores
one sha256 hash per issued key (never the raw key) so the HTTP surface can
resolve agent_id and permission_profile from the key record instead of
trusting the request payload.
"""

from __future__ import annotations

from alembic import op


revision = "20260704_0073"
down_revision = "20260704_0072"
branch_labels = None
depends_on = None


# Mirrors PERMISSION_PROFILES in alicebot_api.vnext_agent_control.
PERMISSION_PROFILES = (
    "read_only_agent",
    "project_scoped_agent",
    "trusted_local_agent",
    "memory_proposal_agent",
    "admin_agent",
)

_PERMISSION_PROFILES_SQL = ", ".join(f"'{value}'" for value in PERMISSION_PROFILES)

_UPGRADE_SCHEMA = f"""
        CREATE TABLE agent_api_keys (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          agent_id text NOT NULL,
          permission_profile text NOT NULL,
          key_hash text NOT NULL UNIQUE,
          key_prefix text NOT NULL,
          label text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          revoked_at timestamptz NULL,
          last_used_at timestamptz NULL,
          UNIQUE (id, user_id),
          CONSTRAINT agent_api_keys_permission_profile_check
            CHECK (permission_profile IN ({_PERMISSION_PROFILES_SQL}))
        );

        CREATE INDEX agent_api_keys_user_agent_idx
          ON agent_api_keys (user_id, agent_id);
        """

_GRANTS = ("GRANT SELECT, INSERT, UPDATE ON agent_api_keys TO alicebot_app",)

_POLICIES = """
        CREATE POLICY agent_api_keys_is_owner ON agent_api_keys
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE = (
    "DROP TABLE IF EXISTS agent_api_keys",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA)
    _execute_statements(_GRANTS)
    op.execute("ALTER TABLE agent_api_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_api_keys FORCE ROW LEVEL SECURITY")
    op.execute(_POLICIES)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE)
