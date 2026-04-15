"""Add hosted control-plane row-level-security backstops."""

from __future__ import annotations

from alembic import op


revision = "20260415_0062"
down_revision = "20260414_0061"
branch_labels = None
depends_on = None

_RLS_TABLES = (
    "workspaces",
    "workspace_members",
    "user_preferences",
    "channel_identities",
    "channel_link_challenges",
    "channel_threads",
    "channel_messages",
    "chat_intents",
    "channel_delivery_receipts",
    "notification_subscriptions",
    "continuity_briefs",
    "daily_brief_jobs",
    "approval_challenges",
    "open_loop_reviews",
    "chat_telemetry",
    "model_providers",
    "provider_capabilities",
    "model_packs",
    "workspace_model_pack_bindings",
)

_UPGRADE_FUNCTION_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.current_user_account_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
          SELECT NULLIF(current_setting('app.current_user_account_id', true), '')::uuid
        $$;
        """,
    """
        CREATE OR REPLACE FUNCTION app.hosted_admin_bypass()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
          SELECT COALESCE(NULLIF(current_setting('app.hosted_admin_bypass', true), ''), 'false')::boolean
        $$;
        """,
    """
        CREATE OR REPLACE FUNCTION app.hosted_service_bypass()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
          SELECT COALESCE(NULLIF(current_setting('app.hosted_service_bypass', true), ''), 'false')::boolean
        $$;
        """,
    """
        CREATE OR REPLACE FUNCTION app.hosted_access_bypass()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
          SELECT app.hosted_admin_bypass() OR app.hosted_service_bypass()
        $$;
        """,
    """
        CREATE OR REPLACE FUNCTION app.hosted_workspace_access_allowed(target_workspace_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
          SELECT
            app.hosted_access_bypass()
            OR (
              target_workspace_id IS NOT NULL
              AND app.current_user_account_id() IS NOT NULL
              AND EXISTS (
                SELECT 1
                FROM workspace_members AS wm
                WHERE wm.workspace_id = target_workspace_id
                  AND wm.user_account_id = app.current_user_account_id()
              )
            )
        $$;
        """,
    """
        CREATE OR REPLACE FUNCTION app.hosted_workspace_owner_allowed(target_workspace_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
          SELECT
            app.hosted_access_bypass()
            OR (
              target_workspace_id IS NOT NULL
              AND app.current_user_account_id() IS NOT NULL
              AND EXISTS (
                SELECT 1
                FROM workspaces AS w
                WHERE w.id = target_workspace_id
                  AND w.owner_user_account_id = app.current_user_account_id()
              )
            )
        $$;
        """,
)

_UPGRADE_POLICY_STATEMENTS = (
    """
        CREATE POLICY workspaces_select_access ON workspaces
          FOR SELECT
          USING (
            app.hosted_access_bypass()
            OR owner_user_account_id = app.current_user_account_id()
            OR app.hosted_workspace_access_allowed(id)
          );
        """,
    """
        CREATE POLICY workspaces_insert_access ON workspaces
          FOR INSERT
          WITH CHECK (
            app.hosted_access_bypass()
            OR owner_user_account_id = app.current_user_account_id()
          );
        """,
    """
        CREATE POLICY workspaces_update_access ON workspaces
          FOR UPDATE
          USING (
            app.hosted_access_bypass()
            OR owner_user_account_id = app.current_user_account_id()
          )
          WITH CHECK (
            app.hosted_access_bypass()
            OR owner_user_account_id = app.current_user_account_id()
          );
        """,
    """
        CREATE POLICY workspaces_delete_access ON workspaces
          FOR DELETE
          USING (
            app.hosted_access_bypass()
            OR owner_user_account_id = app.current_user_account_id()
          );
        """,
    """
        CREATE POLICY workspace_members_select_access ON workspace_members
          FOR SELECT
          USING (
            app.hosted_access_bypass()
            OR user_account_id = app.current_user_account_id()
          );
        """,
    """
        CREATE POLICY workspace_members_insert_access ON workspace_members
          FOR INSERT
          WITH CHECK (
            app.hosted_access_bypass()
            OR (
              user_account_id = app.current_user_account_id()
              AND app.hosted_workspace_owner_allowed(workspace_id)
            )
          );
        """,
    """
        CREATE POLICY workspace_members_update_access ON workspace_members
          FOR UPDATE
          USING (
            app.hosted_access_bypass()
            OR user_account_id = app.current_user_account_id()
          )
          WITH CHECK (
            app.hosted_access_bypass()
            OR (
              user_account_id = app.current_user_account_id()
              AND app.hosted_workspace_owner_allowed(workspace_id)
            )
          );
        """,
    """
        CREATE POLICY workspace_members_delete_access ON workspace_members
          FOR DELETE
          USING (
            app.hosted_access_bypass()
            OR user_account_id = app.current_user_account_id()
          );
        """,
    """
        CREATE POLICY user_preferences_access ON user_preferences
          FOR ALL
          USING (
            app.hosted_access_bypass()
            OR user_account_id = app.current_user_account_id()
          )
          WITH CHECK (
            app.hosted_access_bypass()
            OR user_account_id = app.current_user_account_id()
          );
        """,
    """
        CREATE POLICY channel_identities_access ON channel_identities
          FOR ALL
          USING (
            app.hosted_access_bypass()
            OR (
              user_account_id = app.current_user_account_id()
              AND app.hosted_workspace_access_allowed(workspace_id)
            )
          )
          WITH CHECK (
            app.hosted_access_bypass()
            OR (
              user_account_id = app.current_user_account_id()
              AND app.hosted_workspace_access_allowed(workspace_id)
            )
          );
        """,
    """
        CREATE POLICY channel_link_challenges_access ON channel_link_challenges
          FOR ALL
          USING (
            app.hosted_access_bypass()
            OR (
              user_account_id = app.current_user_account_id()
              AND app.hosted_workspace_access_allowed(workspace_id)
            )
          )
          WITH CHECK (
            app.hosted_access_bypass()
            OR (
              user_account_id = app.current_user_account_id()
              AND app.hosted_workspace_access_allowed(workspace_id)
            )
          );
        """,
    """
        CREATE POLICY channel_threads_workspace_access ON channel_threads
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY channel_messages_workspace_access ON channel_messages
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY chat_intents_workspace_access ON chat_intents
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY channel_delivery_receipts_workspace_access ON channel_delivery_receipts
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY notification_subscriptions_workspace_access ON notification_subscriptions
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY continuity_briefs_workspace_access ON continuity_briefs
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY daily_brief_jobs_workspace_access ON daily_brief_jobs
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY approval_challenges_workspace_access ON approval_challenges
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY open_loop_reviews_workspace_access ON open_loop_reviews
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
    """
        CREATE POLICY chat_telemetry_workspace_access ON chat_telemetry
          FOR ALL
          USING (app.hosted_workspace_access_allowed(workspace_id))
          WITH CHECK (app.hosted_workspace_access_allowed(workspace_id));
        """,
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

_DOWNGRADE_POLICY_STATEMENTS = (
    "DROP POLICY IF EXISTS workspace_model_pack_bindings_workspace_access ON workspace_model_pack_bindings",
    "DROP POLICY IF EXISTS model_packs_workspace_access ON model_packs",
    "DROP POLICY IF EXISTS provider_capabilities_workspace_access ON provider_capabilities",
    "DROP POLICY IF EXISTS model_providers_workspace_access ON model_providers",
    "DROP POLICY IF EXISTS chat_telemetry_workspace_access ON chat_telemetry",
    "DROP POLICY IF EXISTS open_loop_reviews_workspace_access ON open_loop_reviews",
    "DROP POLICY IF EXISTS approval_challenges_workspace_access ON approval_challenges",
    "DROP POLICY IF EXISTS daily_brief_jobs_workspace_access ON daily_brief_jobs",
    "DROP POLICY IF EXISTS continuity_briefs_workspace_access ON continuity_briefs",
    "DROP POLICY IF EXISTS notification_subscriptions_workspace_access ON notification_subscriptions",
    "DROP POLICY IF EXISTS channel_delivery_receipts_workspace_access ON channel_delivery_receipts",
    "DROP POLICY IF EXISTS chat_intents_workspace_access ON chat_intents",
    "DROP POLICY IF EXISTS channel_messages_workspace_access ON channel_messages",
    "DROP POLICY IF EXISTS channel_threads_workspace_access ON channel_threads",
    "DROP POLICY IF EXISTS channel_link_challenges_access ON channel_link_challenges",
    "DROP POLICY IF EXISTS channel_identities_access ON channel_identities",
    "DROP POLICY IF EXISTS user_preferences_access ON user_preferences",
    "DROP POLICY IF EXISTS workspace_members_delete_access ON workspace_members",
    "DROP POLICY IF EXISTS workspace_members_update_access ON workspace_members",
    "DROP POLICY IF EXISTS workspace_members_insert_access ON workspace_members",
    "DROP POLICY IF EXISTS workspace_members_select_access ON workspace_members",
    "DROP POLICY IF EXISTS workspaces_delete_access ON workspaces",
    "DROP POLICY IF EXISTS workspaces_update_access ON workspaces",
    "DROP POLICY IF EXISTS workspaces_insert_access ON workspaces",
    "DROP POLICY IF EXISTS workspaces_select_access ON workspaces",
)

_DOWNGRADE_FUNCTION_STATEMENTS = (
    "DROP FUNCTION IF EXISTS app.hosted_workspace_owner_allowed(uuid)",
    "DROP FUNCTION IF EXISTS app.hosted_workspace_access_allowed(uuid)",
    "DROP FUNCTION IF EXISTS app.hosted_access_bypass()",
    "DROP FUNCTION IF EXISTS app.hosted_service_bypass()",
    "DROP FUNCTION IF EXISTS app.hosted_admin_bypass()",
    "DROP FUNCTION IF EXISTS app.current_user_account_id()",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def _disable_row_level_security() -> None:
    for table_name in reversed(_RLS_TABLES):
        op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_FUNCTION_STATEMENTS)
    _enable_row_level_security()
    _execute_statements(_UPGRADE_POLICY_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_POLICY_STATEMENTS)
    _disable_row_level_security()
    _execute_statements(_DOWNGRADE_FUNCTION_STATEMENTS)
