"""Add Phase 14 provider invocation telemetry table."""

from __future__ import annotations

from alembic import op


revision = "20260415_0063"
down_revision = "20260415_0062"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE provider_invocation_telemetry (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          provider_id uuid NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
          thread_id uuid NULL REFERENCES threads(id) ON DELETE SET NULL,
          invoked_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          invocation_kind text NOT NULL,
          adapter_key text NOT NULL,
          runtime_provider text NOT NULL,
          requested_model text NOT NULL,
          response_model text NULL,
          response_id text NULL,
          status text NOT NULL,
          latency_ms integer NOT NULL,
          usage jsonb NOT NULL DEFAULT '{}'::jsonb,
          error_detail text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT provider_invocation_telemetry_kind_check
            CHECK (invocation_kind IN ('provider_test', 'runtime_invoke')),
          CONSTRAINT provider_invocation_telemetry_adapter_key_length_check
            CHECK (char_length(adapter_key) >= 1 AND char_length(adapter_key) <= 80),
          CONSTRAINT provider_invocation_telemetry_runtime_provider_length_check
            CHECK (char_length(runtime_provider) >= 1 AND char_length(runtime_provider) <= 80),
          CONSTRAINT provider_invocation_telemetry_requested_model_length_check
            CHECK (char_length(requested_model) >= 1 AND char_length(requested_model) <= 200),
          CONSTRAINT provider_invocation_telemetry_response_model_length_check
            CHECK (response_model IS NULL OR char_length(response_model) BETWEEN 1 AND 200),
          CONSTRAINT provider_invocation_telemetry_response_id_length_check
            CHECK (response_id IS NULL OR char_length(response_id) BETWEEN 1 AND 200),
          CONSTRAINT provider_invocation_telemetry_status_check
            CHECK (status IN ('succeeded', 'failed')),
          CONSTRAINT provider_invocation_telemetry_latency_ms_check
            CHECK (latency_ms >= 0)
        )
        """,
    (
        "CREATE INDEX provider_invocation_telemetry_workspace_created_idx "
        "ON provider_invocation_telemetry (workspace_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX provider_invocation_telemetry_provider_created_idx "
        "ON provider_invocation_telemetry (provider_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX provider_invocation_telemetry_thread_created_idx "
        "ON provider_invocation_telemetry (thread_id, created_at DESC, id DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON provider_invocation_telemetry TO alicebot_app",
)

_UPGRADE_RLS_STATEMENTS = (
    "ALTER TABLE provider_invocation_telemetry ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE provider_invocation_telemetry FORCE ROW LEVEL SECURITY",
)

_UPGRADE_POLICY_STATEMENTS = (
    """
        CREATE POLICY provider_invocation_telemetry_workspace_access ON provider_invocation_telemetry
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP POLICY IF EXISTS provider_invocation_telemetry_workspace_access ON provider_invocation_telemetry",
    "ALTER TABLE provider_invocation_telemetry NO FORCE ROW LEVEL SECURITY",
    "ALTER TABLE provider_invocation_telemetry DISABLE ROW LEVEL SECURITY",
    "DROP TABLE IF EXISTS provider_invocation_telemetry",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _execute_statements(_UPGRADE_RLS_STATEMENTS)
    _execute_statements(_UPGRADE_POLICY_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
