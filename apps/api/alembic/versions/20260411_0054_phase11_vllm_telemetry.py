"""Add vLLM adapter options and provider invocation telemetry."""

from __future__ import annotations

from alembic import op


revision = "20260411_0054"
down_revision = "20260411_0053"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    "ALTER TABLE model_providers ADD COLUMN adapter_options jsonb NOT NULL DEFAULT '{}'::jsonb",
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_adapter_options_object_check "
        "CHECK (jsonb_typeof(adapter_options) = 'object')"
    ),
    """
        CREATE TABLE provider_invocation_telemetry (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          provider_id uuid NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
          invoked_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          flow_kind text NOT NULL,
          adapter_key text NOT NULL,
          runtime_provider text NOT NULL,
          provider_model text NOT NULL,
          status text NOT NULL,
          error_message text NULL,
          latency_ms integer NOT NULL,
          input_tokens integer NULL,
          output_tokens integer NULL,
          total_tokens integer NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT provider_invocation_telemetry_flow_kind_check
            CHECK (flow_kind IN ('provider_test', 'runtime_invoke')),
          CONSTRAINT provider_invocation_telemetry_adapter_key_length_check
            CHECK (char_length(adapter_key) >= 1 AND char_length(adapter_key) <= 80),
          CONSTRAINT provider_invocation_telemetry_runtime_provider_length_check
            CHECK (char_length(runtime_provider) >= 1 AND char_length(runtime_provider) <= 100),
          CONSTRAINT provider_invocation_telemetry_provider_model_length_check
            CHECK (char_length(provider_model) >= 1 AND char_length(provider_model) <= 200),
          CONSTRAINT provider_invocation_telemetry_status_check
            CHECK (status IN ('completed', 'failed')),
          CONSTRAINT provider_invocation_telemetry_latency_non_negative_check
            CHECK (latency_ms >= 0),
          CONSTRAINT provider_invocation_telemetry_input_tokens_non_negative_check
            CHECK (input_tokens IS NULL OR input_tokens >= 0),
          CONSTRAINT provider_invocation_telemetry_output_tokens_non_negative_check
            CHECK (output_tokens IS NULL OR output_tokens >= 0),
          CONSTRAINT provider_invocation_telemetry_total_tokens_non_negative_check
            CHECK (total_tokens IS NULL OR total_tokens >= 0)
        )
        """,
    (
        "CREATE INDEX provider_invocation_telemetry_provider_created_idx "
        "ON provider_invocation_telemetry (provider_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX provider_invocation_telemetry_workspace_created_idx "
        "ON provider_invocation_telemetry (workspace_id, created_at DESC, id DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON provider_invocation_telemetry TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS provider_invocation_telemetry",
    "ALTER TABLE model_providers DROP CONSTRAINT IF EXISTS model_providers_adapter_options_object_check",
    "ALTER TABLE model_providers DROP COLUMN IF EXISTS adapter_options",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
