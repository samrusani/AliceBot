"""Add local-provider configuration fields to model_providers."""

from __future__ import annotations

from alembic import op


revision = "20260411_0053"
down_revision = "20260411_0052"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    "ALTER TABLE model_providers ADD COLUMN auth_mode text NOT NULL DEFAULT 'bearer'",
    "ALTER TABLE model_providers ADD COLUMN model_list_path text NOT NULL DEFAULT ''",
    "ALTER TABLE model_providers ADD COLUMN healthcheck_path text NOT NULL DEFAULT ''",
    "ALTER TABLE model_providers ADD COLUMN invoke_path text NOT NULL DEFAULT ''",
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_auth_mode_check "
        "CHECK (auth_mode IN ('bearer', 'none'))"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_model_list_path_length_check "
        "CHECK (char_length(model_list_path) <= 200)"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_healthcheck_path_length_check "
        "CHECK (char_length(healthcheck_path) <= 200)"
    ),
    (
        "ALTER TABLE model_providers "
        "ADD CONSTRAINT model_providers_invoke_path_length_check "
        "CHECK (char_length(invoke_path) <= 200)"
    ),
)

_DOWNGRADE_STATEMENTS = (
    "ALTER TABLE model_providers DROP CONSTRAINT IF EXISTS model_providers_invoke_path_length_check",
    "ALTER TABLE model_providers DROP CONSTRAINT IF EXISTS model_providers_healthcheck_path_length_check",
    "ALTER TABLE model_providers DROP CONSTRAINT IF EXISTS model_providers_model_list_path_length_check",
    "ALTER TABLE model_providers DROP CONSTRAINT IF EXISTS model_providers_auth_mode_check",
    "ALTER TABLE model_providers DROP COLUMN IF EXISTS invoke_path",
    "ALTER TABLE model_providers DROP COLUMN IF EXISTS healthcheck_path",
    "ALTER TABLE model_providers DROP COLUMN IF EXISTS model_list_path",
    "ALTER TABLE model_providers DROP COLUMN IF EXISTS auth_mode",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
