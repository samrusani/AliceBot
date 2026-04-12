"""Add Azure provider configuration and secret-ref fields."""

from __future__ import annotations

from alembic import op


revision = "20260412_0055"
down_revision = "20260412_0054"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    "ALTER TABLE model_providers ADD COLUMN azure_api_version text NOT NULL DEFAULT ''",
    "ALTER TABLE model_providers ADD COLUMN azure_auth_secret_ref text NOT NULL DEFAULT ''",
    "ALTER TABLE model_providers DROP CONSTRAINT IF EXISTS model_providers_auth_mode_check",
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_auth_mode_check "
        "CHECK (auth_mode IN ('bearer', 'none', 'azure_api_key', 'azure_ad_token'))"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_azure_api_version_length_check "
        "CHECK (char_length(azure_api_version) <= 40)"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_azure_auth_secret_ref_length_check "
        "CHECK (char_length(azure_auth_secret_ref) <= 400)"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_azure_api_version_required_for_azure_auth_check "
        "CHECK ("
        "(auth_mode IN ('azure_api_key', 'azure_ad_token') AND char_length(azure_api_version) >= 1) "
        "OR (auth_mode IN ('bearer', 'none'))"
        ")"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_azure_secret_ref_required_for_azure_auth_check "
        "CHECK ("
        "(auth_mode IN ('azure_api_key', 'azure_ad_token') AND char_length(azure_auth_secret_ref) >= 1) "
        "OR (auth_mode IN ('bearer', 'none'))"
        ")"
    ),
)

_DOWNGRADE_STATEMENTS = (
    (
        "ALTER TABLE model_providers "
        "DROP CONSTRAINT IF EXISTS model_providers_azure_secret_ref_required_for_azure_auth_check"
    ),
    (
        "ALTER TABLE model_providers "
        "DROP CONSTRAINT IF EXISTS model_providers_azure_api_version_required_for_azure_auth_check"
    ),
    (
        "ALTER TABLE model_providers "
        "DROP CONSTRAINT IF EXISTS model_providers_azure_auth_secret_ref_length_check"
    ),
    (
        "ALTER TABLE model_providers "
        "DROP CONSTRAINT IF EXISTS model_providers_azure_api_version_length_check"
    ),
    "ALTER TABLE model_providers DROP CONSTRAINT IF EXISTS model_providers_auth_mode_check",
    (
        "UPDATE model_providers "
        "SET auth_mode = 'bearer' "
        "WHERE auth_mode IN ('azure_api_key', 'azure_ad_token')"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_auth_mode_check "
        "CHECK (auth_mode IN ('bearer', 'none'))"
    ),
    "ALTER TABLE model_providers DROP COLUMN IF EXISTS azure_auth_secret_ref",
    "ALTER TABLE model_providers DROP COLUMN IF EXISTS azure_api_version",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
