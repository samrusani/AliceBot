"""Add Phase 11 model pack catalog and workspace binding tables."""

from __future__ import annotations

from alembic import op


revision = "20260412_0054"
down_revision = "20260411_0053"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE model_packs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          created_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          pack_id text NOT NULL,
          pack_version text NOT NULL,
          display_name text NOT NULL,
          family text NOT NULL,
          description text NOT NULL DEFAULT '',
          status text NOT NULL DEFAULT 'active',
          contract jsonb NOT NULL DEFAULT '{}'::jsonb,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (workspace_id, pack_id, pack_version),
          UNIQUE (id, workspace_id),
          CONSTRAINT model_packs_pack_id_length_check
            CHECK (char_length(pack_id) >= 1 AND char_length(pack_id) <= 80),
          CONSTRAINT model_packs_pack_version_semver_check
            CHECK (pack_version ~ '^[0-9]+\\.[0-9]+\\.[0-9]+$'),
          CONSTRAINT model_packs_display_name_length_check
            CHECK (char_length(display_name) >= 1 AND char_length(display_name) <= 120),
          CONSTRAINT model_packs_family_check
            CHECK (family IN ('llama', 'qwen', 'gemma', 'gpt-oss', 'custom')),
          CONSTRAINT model_packs_status_check
            CHECK (status IN ('active')),
          CONSTRAINT model_packs_contract_object_check
            CHECK (jsonb_typeof(contract) = 'object'),
          CONSTRAINT model_packs_metadata_object_check
            CHECK (jsonb_typeof(metadata) = 'object')
        )
        """,
    (
        "CREATE INDEX model_packs_workspace_pack_created_idx "
        "ON model_packs (workspace_id, pack_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX model_packs_workspace_family_idx "
        "ON model_packs (workspace_id, family, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE workspace_model_pack_bindings (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          model_pack_id uuid NOT NULL,
          bound_by_user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE RESTRICT,
          binding_source text NOT NULL DEFAULT 'manual',
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT workspace_model_pack_bindings_workspace_pack_fk
            FOREIGN KEY (model_pack_id, workspace_id)
            REFERENCES model_packs(id, workspace_id)
            ON DELETE RESTRICT,
          CONSTRAINT workspace_model_pack_bindings_source_check
            CHECK (binding_source IN ('manual', 'runtime_override')),
          CONSTRAINT workspace_model_pack_bindings_metadata_object_check
            CHECK (jsonb_typeof(metadata) = 'object')
        )
        """,
    (
        "CREATE INDEX workspace_model_pack_bindings_workspace_created_idx "
        "ON workspace_model_pack_bindings (workspace_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX workspace_model_pack_bindings_pack_created_idx "
        "ON workspace_model_pack_bindings (model_pack_id, created_at DESC, id DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON model_packs TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON workspace_model_pack_bindings TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS workspace_model_pack_bindings",
    "DROP TABLE IF EXISTS model_packs",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
