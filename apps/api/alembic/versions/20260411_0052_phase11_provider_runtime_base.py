"""Add Phase 11 provider registry and capability snapshot tables."""

from __future__ import annotations

from alembic import op


revision = "20260411_0052"
down_revision = "20260410_0051"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE model_providers (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          created_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          provider_key text NOT NULL,
          model_provider text NOT NULL DEFAULT 'openai_responses',
          display_name text NOT NULL,
          base_url text NOT NULL,
          api_key text NOT NULL,
          default_model text NOT NULL,
          status text NOT NULL DEFAULT 'active',
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (workspace_id, display_name),
          CONSTRAINT model_providers_provider_key_length_check
            CHECK (char_length(provider_key) >= 1 AND char_length(provider_key) <= 80),
          CONSTRAINT model_providers_model_provider_check
            CHECK (model_provider IN ('openai_responses')),
          CONSTRAINT model_providers_display_name_length_check
            CHECK (char_length(display_name) >= 1 AND char_length(display_name) <= 120),
          CONSTRAINT model_providers_base_url_length_check
            CHECK (char_length(base_url) >= 1 AND char_length(base_url) <= 500),
          CONSTRAINT model_providers_api_key_length_check
            CHECK (char_length(api_key) >= 1 AND char_length(api_key) <= 8000),
          CONSTRAINT model_providers_default_model_length_check
            CHECK (char_length(default_model) >= 1 AND char_length(default_model) <= 200),
          CONSTRAINT model_providers_status_check
            CHECK (status IN ('active'))
        )
        """,
    (
        "CREATE INDEX model_providers_workspace_created_idx "
        "ON model_providers (workspace_id, created_at ASC, id ASC)"
    ),
    (
        "CREATE INDEX model_providers_workspace_provider_idx "
        "ON model_providers (workspace_id, provider_key, model_provider, id)"
    ),
    """
        CREATE TABLE provider_capabilities (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          provider_id uuid NOT NULL UNIQUE REFERENCES model_providers(id) ON DELETE CASCADE,
          discovered_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          adapter_key text NOT NULL,
          discovery_status text NOT NULL,
          capability_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
          discovery_error text NULL,
          discovered_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT provider_capabilities_adapter_key_length_check
            CHECK (char_length(adapter_key) >= 1 AND char_length(adapter_key) <= 80),
          CONSTRAINT provider_capabilities_status_check
            CHECK (discovery_status IN ('ready', 'failed'))
        )
        """,
    (
        "CREATE INDEX provider_capabilities_workspace_discovered_idx "
        "ON provider_capabilities (workspace_id, discovered_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX provider_capabilities_provider_status_idx "
        "ON provider_capabilities (provider_id, discovery_status, discovered_at DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON model_providers TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON provider_capabilities TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS provider_capabilities",
    "DROP TABLE IF EXISTS model_providers",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
