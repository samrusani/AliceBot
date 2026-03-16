"""Add external secret-manager references for Gmail protected credentials."""

from __future__ import annotations

from alembic import op


revision = "20260316_0029"
down_revision = "20260316_0028"
branch_labels = None
depends_on = None

GMAIL_PROTECTED_CREDENTIAL_KIND = "gmail_oauth_access_token_v1"
GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND = "gmail_oauth_refresh_token_v2"
GMAIL_SECRET_MANAGER_KIND_FILE_V1 = "file_v1"
GMAIL_SECRET_MANAGER_KIND_LEGACY_DB_V0 = "legacy_db_v0"

_CREDENTIAL_BLOB_SHAPE_CHECK = f"""
        (
          jsonb_typeof(credential_blob) = 'object'
          AND credential_blob ? 'credential_kind'
          AND credential_blob ? 'access_token'
          AND jsonb_typeof(credential_blob -> 'access_token') = 'string'
          AND length(credential_blob ->> 'access_token') > 0
          AND (
            (
              credential_blob ->> 'credential_kind' = '{GMAIL_PROTECTED_CREDENTIAL_KIND}'
            )
            OR
            (
              credential_blob ->> 'credential_kind' = '{GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND}'
              AND credential_blob ? 'refresh_token'
              AND credential_blob ? 'client_id'
              AND credential_blob ? 'client_secret'
              AND credential_blob ? 'access_token_expires_at'
              AND jsonb_typeof(credential_blob -> 'refresh_token') = 'string'
              AND jsonb_typeof(credential_blob -> 'client_id') = 'string'
              AND jsonb_typeof(credential_blob -> 'client_secret') = 'string'
              AND jsonb_typeof(credential_blob -> 'access_token_expires_at') = 'string'
              AND length(credential_blob ->> 'refresh_token') > 0
              AND length(credential_blob ->> 'client_id') > 0
              AND length(credential_blob ->> 'client_secret') > 0
              AND length(credential_blob ->> 'access_token_expires_at') > 0
            )
          )
        )
"""

_UPGRADE_STATEMENTS = (
    "ALTER TABLE gmail_account_credentials DROP CONSTRAINT gmail_account_credentials_blob_shape_check",
    "ALTER TABLE gmail_account_credentials ADD COLUMN credential_kind text",
    "ALTER TABLE gmail_account_credentials ADD COLUMN secret_manager_kind text",
    "ALTER TABLE gmail_account_credentials ADD COLUMN secret_ref text",
    "ALTER TABLE gmail_account_credentials ALTER COLUMN credential_blob DROP NOT NULL",
    """
        UPDATE gmail_account_credentials
        SET credential_kind = credential_blob ->> 'credential_kind',
            secret_manager_kind = 'legacy_db_v0'
    """,
    "ALTER TABLE gmail_account_credentials ALTER COLUMN credential_kind SET NOT NULL",
    "ALTER TABLE gmail_account_credentials ALTER COLUMN secret_manager_kind SET NOT NULL",
    f"""
        ALTER TABLE gmail_account_credentials
        ADD CONSTRAINT gmail_account_credentials_storage_shape_check
          CHECK (
            credential_kind IN (
              '{GMAIL_PROTECTED_CREDENTIAL_KIND}',
              '{GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND}'
            )
            AND (
              (
                secret_manager_kind = '{GMAIL_SECRET_MANAGER_KIND_LEGACY_DB_V0}'
                AND secret_ref IS NULL
                AND {_CREDENTIAL_BLOB_SHAPE_CHECK}
              )
              OR
              (
                secret_manager_kind = '{GMAIL_SECRET_MANAGER_KIND_FILE_V1}'
                AND secret_ref IS NOT NULL
                AND length(secret_ref) > 0
                AND credential_blob IS NULL
              )
            )
          )
    """,
)

_DOWNGRADE_STATEMENTS = (
    """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM gmail_account_credentials
            WHERE secret_manager_kind = 'file_v1'
          ) THEN
            RAISE EXCEPTION
              'cannot downgrade gmail_account_credentials while external Gmail secrets are present';
          END IF;
        END
        $$;
    """,
    "ALTER TABLE gmail_account_credentials DROP CONSTRAINT gmail_account_credentials_storage_shape_check",
    "ALTER TABLE gmail_account_credentials ALTER COLUMN credential_blob SET NOT NULL",
    "ALTER TABLE gmail_account_credentials DROP COLUMN secret_ref",
    "ALTER TABLE gmail_account_credentials DROP COLUMN secret_manager_kind",
    "ALTER TABLE gmail_account_credentials DROP COLUMN credential_kind",
    f"""
        ALTER TABLE gmail_account_credentials
        ADD CONSTRAINT gmail_account_credentials_blob_shape_check
          CHECK {_CREDENTIAL_BLOB_SHAPE_CHECK}
    """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
