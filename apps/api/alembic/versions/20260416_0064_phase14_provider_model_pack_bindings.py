"""Add provider-aware workspace model-pack bindings for Phase 14 model packs."""

from __future__ import annotations

from alembic import op


revision = "20260416_0064"
down_revision = "20260415_0063"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    (
        "ALTER TABLE workspace_model_pack_bindings "
        "ADD COLUMN provider_id uuid NULL REFERENCES model_providers(id) ON DELETE CASCADE"
    ),
    (
        "CREATE INDEX workspace_model_pack_bindings_workspace_provider_created_idx "
        "ON workspace_model_pack_bindings (workspace_id, provider_id, created_at DESC, id DESC)"
    ),
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS workspace_model_pack_bindings_workspace_provider_created_idx",
    "ALTER TABLE workspace_model_pack_bindings DROP COLUMN IF EXISTS provider_id",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
