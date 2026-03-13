"""Add stable tool registry storage for deterministic allowlist evaluation."""

from __future__ import annotations

from alembic import op


revision = "20260312_0010"
down_revision = "20260312_0009"
branch_labels = None
depends_on = None

_RLS_TABLES = ("tools",)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE tools (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          tool_key text NOT NULL,
          name text NOT NULL,
          description text NOT NULL,
          version text NOT NULL,
          metadata_version text NOT NULL,
          active boolean NOT NULL DEFAULT TRUE,
          tags jsonb NOT NULL DEFAULT '[]'::jsonb,
          action_hints jsonb NOT NULL DEFAULT '[]'::jsonb,
          scope_hints jsonb NOT NULL DEFAULT '[]'::jsonb,
          domain_hints jsonb NOT NULL DEFAULT '[]'::jsonb,
          risk_hints jsonb NOT NULL DEFAULT '[]'::jsonb,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, tool_key, version),
          CONSTRAINT tools_key_length_check
            CHECK (char_length(tool_key) BETWEEN 1 AND 200),
          CONSTRAINT tools_name_length_check
            CHECK (char_length(name) BETWEEN 1 AND 200),
          CONSTRAINT tools_description_length_check
            CHECK (char_length(description) BETWEEN 1 AND 500),
          CONSTRAINT tools_version_length_check
            CHECK (char_length(version) BETWEEN 1 AND 100),
          CONSTRAINT tools_metadata_version_check
            CHECK (metadata_version = 'tool_metadata_v0'),
          CONSTRAINT tools_tags_array_check
            CHECK (jsonb_typeof(tags) = 'array'),
          CONSTRAINT tools_action_hints_array_check
            CHECK (jsonb_typeof(action_hints) = 'array'),
          CONSTRAINT tools_scope_hints_array_check
            CHECK (jsonb_typeof(scope_hints) = 'array'),
          CONSTRAINT tools_domain_hints_array_check
            CHECK (jsonb_typeof(domain_hints) = 'array'),
          CONSTRAINT tools_risk_hints_array_check
            CHECK (jsonb_typeof(risk_hints) = 'array'),
          CONSTRAINT tools_metadata_object_check
            CHECK (jsonb_typeof(metadata) = 'object')
        );

        CREATE INDEX tools_user_active_key_version_created_idx
          ON tools (user_id, active, tool_key, version, created_at, id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON tools TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY tools_is_owner ON tools
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS tools",
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
