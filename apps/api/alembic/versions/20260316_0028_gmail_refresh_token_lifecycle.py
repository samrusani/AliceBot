"""Allow Gmail protected credentials to store refresh-token lifecycle data."""

from __future__ import annotations

from alembic import op


revision = "20260316_0028"
down_revision = "20260316_0027"
branch_labels = None
depends_on = None

GMAIL_PROTECTED_CREDENTIAL_KIND = "gmail_oauth_access_token_v1"
GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND = "gmail_oauth_refresh_token_v2"

_UPGRADE_STATEMENTS = (
    "ALTER TABLE gmail_account_credentials DROP CONSTRAINT gmail_account_credentials_blob_shape_check",
    f"""
        ALTER TABLE gmail_account_credentials
        ADD CONSTRAINT gmail_account_credentials_blob_shape_check
          CHECK (
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
    """,
    "GRANT UPDATE ON gmail_account_credentials TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    """
        UPDATE gmail_account_credentials
        SET credential_blob = jsonb_build_object(
          'credential_kind', 'gmail_oauth_access_token_v1',
          'access_token', credential_blob ->> 'access_token'
        )
        WHERE credential_blob ->> 'credential_kind' = 'gmail_oauth_refresh_token_v2'
    """,
    "REVOKE UPDATE ON gmail_account_credentials FROM alicebot_app",
    "ALTER TABLE gmail_account_credentials DROP CONSTRAINT gmail_account_credentials_blob_shape_check",
    f"""
        ALTER TABLE gmail_account_credentials
        ADD CONSTRAINT gmail_account_credentials_blob_shape_check
          CHECK (
            jsonb_typeof(credential_blob) = 'object'
            AND credential_blob ? 'credential_kind'
            AND credential_blob ? 'access_token'
            AND credential_blob ->> 'credential_kind' = '{GMAIL_PROTECTED_CREDENTIAL_KIND}'
            AND jsonb_typeof(credential_blob -> 'access_token') = 'string'
            AND length(credential_blob ->> 'access_token') > 0
          )
    """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
