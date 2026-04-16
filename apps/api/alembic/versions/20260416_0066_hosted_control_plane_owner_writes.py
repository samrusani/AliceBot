"""Restrict hosted control-plane writes to workspace owners."""

from __future__ import annotations

from alembic import op


revision = "20260416_0066"
down_revision = "20260416_0065"
branch_labels = None
depends_on = None

_UPGRADE_DROP_STATEMENTS = (
    "DROP POLICY IF EXISTS workspace_model_pack_bindings_workspace_access ON workspace_model_pack_bindings",
    "DROP POLICY IF EXISTS model_packs_workspace_access ON model_packs",
    "DROP POLICY IF EXISTS provider_capabilities_workspace_access ON provider_capabilities",
    "DROP POLICY IF EXISTS model_providers_workspace_access ON model_providers",
)

_UPGRADE_CREATE_STATEMENTS = (
    """
        CREATE POLICY model_providers_select_access ON model_providers
          FOR SELECT
          USING (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_providers_insert_owner_access ON model_providers
          FOR INSERT
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_providers_update_owner_access ON model_providers
          FOR UPDATE
          USING (app.hosted_workspace_owner_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_providers_delete_owner_access ON model_providers
          FOR DELETE
          USING (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY provider_capabilities_select_access ON provider_capabilities
          FOR SELECT
          USING (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY provider_capabilities_insert_owner_access ON provider_capabilities
          FOR INSERT
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY provider_capabilities_update_owner_access ON provider_capabilities
          FOR UPDATE
          USING (app.hosted_workspace_owner_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY provider_capabilities_delete_owner_access ON provider_capabilities
          FOR DELETE
          USING (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_packs_select_access ON model_packs
          FOR SELECT
          USING (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_packs_insert_owner_access ON model_packs
          FOR INSERT
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_packs_update_owner_access ON model_packs
          FOR UPDATE
          USING (app.hosted_workspace_owner_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_packs_delete_owner_access ON model_packs
          FOR DELETE
          USING (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY workspace_model_pack_bindings_select_access ON workspace_model_pack_bindings
          FOR SELECT
          USING (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY workspace_model_pack_bindings_insert_owner_access ON workspace_model_pack_bindings
          FOR INSERT
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY workspace_model_pack_bindings_update_owner_access ON workspace_model_pack_bindings
          FOR UPDATE
          USING (app.hosted_workspace_owner_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_owner_allowed(workspace_id));
        """,
    """
        CREATE POLICY workspace_model_pack_bindings_delete_owner_access ON workspace_model_pack_bindings
          FOR DELETE
          USING (app.hosted_workspace_owner_allowed(workspace_id));
        """,
)

_DOWNGRADE_DROP_STATEMENTS = (
    "DROP POLICY IF EXISTS workspace_model_pack_bindings_delete_owner_access ON workspace_model_pack_bindings",
    "DROP POLICY IF EXISTS workspace_model_pack_bindings_update_owner_access ON workspace_model_pack_bindings",
    "DROP POLICY IF EXISTS workspace_model_pack_bindings_insert_owner_access ON workspace_model_pack_bindings",
    "DROP POLICY IF EXISTS workspace_model_pack_bindings_select_access ON workspace_model_pack_bindings",
    "DROP POLICY IF EXISTS model_packs_delete_owner_access ON model_packs",
    "DROP POLICY IF EXISTS model_packs_update_owner_access ON model_packs",
    "DROP POLICY IF EXISTS model_packs_insert_owner_access ON model_packs",
    "DROP POLICY IF EXISTS model_packs_select_access ON model_packs",
    "DROP POLICY IF EXISTS provider_capabilities_delete_owner_access ON provider_capabilities",
    "DROP POLICY IF EXISTS provider_capabilities_update_owner_access ON provider_capabilities",
    "DROP POLICY IF EXISTS provider_capabilities_insert_owner_access ON provider_capabilities",
    "DROP POLICY IF EXISTS provider_capabilities_select_access ON provider_capabilities",
    "DROP POLICY IF EXISTS model_providers_delete_owner_access ON model_providers",
    "DROP POLICY IF EXISTS model_providers_update_owner_access ON model_providers",
    "DROP POLICY IF EXISTS model_providers_insert_owner_access ON model_providers",
    "DROP POLICY IF EXISTS model_providers_select_access ON model_providers",
)

_DOWNGRADE_CREATE_STATEMENTS = (
    """
        CREATE POLICY model_providers_workspace_access ON model_providers
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY provider_capabilities_workspace_access ON provider_capabilities
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY model_packs_workspace_access ON model_packs
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY workspace_model_pack_bindings_workspace_access ON workspace_model_pack_bindings
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_DROP_STATEMENTS)
    _execute_statements(_UPGRADE_CREATE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_DROP_STATEMENTS)
    _execute_statements(_DOWNGRADE_CREATE_STATEMENTS)
