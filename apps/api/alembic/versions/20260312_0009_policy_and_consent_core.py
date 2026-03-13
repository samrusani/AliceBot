"""Add user-scoped consents and deterministic policy storage."""

from __future__ import annotations

from alembic import op


revision = "20260312_0009"
down_revision = "20260312_0008"
branch_labels = None
depends_on = None

_RLS_TABLES = ("consents", "policies")

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE consents (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          consent_key text NOT NULL,
          status text NOT NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, consent_key),
          CONSTRAINT consents_key_length_check
            CHECK (char_length(consent_key) BETWEEN 1 AND 200),
          CONSTRAINT consents_status_check
            CHECK (status IN ('granted', 'revoked')),
          CONSTRAINT consents_metadata_object_check
            CHECK (jsonb_typeof(metadata) = 'object')
        );

        CREATE INDEX consents_user_key_created_idx
          ON consents (user_id, consent_key, created_at, id);

        CREATE TABLE policies (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          name text NOT NULL,
          action text NOT NULL,
          scope text NOT NULL,
          effect text NOT NULL,
          priority integer NOT NULL,
          active boolean NOT NULL DEFAULT TRUE,
          conditions jsonb NOT NULL DEFAULT '{}'::jsonb,
          required_consents jsonb NOT NULL DEFAULT '[]'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT policies_name_length_check
            CHECK (char_length(name) BETWEEN 1 AND 200),
          CONSTRAINT policies_action_length_check
            CHECK (char_length(action) BETWEEN 1 AND 100),
          CONSTRAINT policies_scope_length_check
            CHECK (char_length(scope) BETWEEN 1 AND 200),
          CONSTRAINT policies_effect_check
            CHECK (effect IN ('allow', 'deny', 'require_approval')),
          CONSTRAINT policies_priority_check
            CHECK (priority >= 0),
          CONSTRAINT policies_conditions_object_check
            CHECK (jsonb_typeof(conditions) = 'object'),
          CONSTRAINT policies_required_consents_array_check
            CHECK (jsonb_typeof(required_consents) = 'array')
        );

        CREATE INDEX policies_user_active_priority_created_idx
          ON policies (user_id, active, priority, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON consents TO alicebot_app",
    "GRANT SELECT, INSERT ON policies TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY consents_is_owner ON consents
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY policies_is_owner ON policies
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS policies",
    "DROP TABLE IF EXISTS consents",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
