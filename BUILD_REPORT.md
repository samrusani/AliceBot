# BUILD_REPORT

## sprint objective

Implement Sprint 5P: harden the existing narrow Gmail connector seam so Gmail access tokens are no longer stored on the normal `gmail_accounts` table surface, Gmail account reads never expose secrets, and the existing single-message Gmail ingestion path continues to work through an explicit protected credential lookup.

## completed work

- Added migration `20260316_0027_gmail_account_credentials.py` to move Gmail tokens out of `gmail_accounts`.
- Introduced a protected Gmail credential table with:
  - row-level security
  - `gmail_account_id` ownership binding
  - a checked credential blob shape
  - backfill from existing `gmail_accounts.access_token`
- Removed plaintext `access_token` storage from the normal `gmail_accounts` table surface by dropping the column in the new migration.
- Kept the Gmail connect write contract narrow:
  - connect still accepts `access_token` on write
  - account list/detail responses still return the same stable metadata shape without secret material
- Updated the Gmail service seam to:
  - persist account metadata and protected credentials separately
  - resolve the access token through the protected credential lookup during ingestion
  - fail deterministically when protected credentials are missing or malformed
  - fail before Gmail fetches, artifact registration, or filesystem writes when credentials are unusable
- Added unit and integration coverage for:
  - protected credential persistence
  - secret removal from Gmail account responses
  - hardened single-message ingestion success
  - deterministic missing/invalid credential failures
  - per-user isolation
  - stable response shape

## exact Gmail credential contract and schema changes introduced

- Gmail account connect request remains:
  - `user_id: UUID`
  - `provider_account_id: str`
  - `email_address: str`
  - `display_name: str | null`
  - `scope: "https://www.googleapis.com/auth/gmail.readonly"`
  - `access_token: str`
- Gmail account read responses remain secret-free:
  - `id`
  - `provider`
  - `auth_kind`
  - `provider_account_id`
  - `email_address`
  - `display_name`
  - `scope`
  - `created_at`
  - `updated_at`
- `gmail_accounts` schema change:
  - dropped plaintext column `access_token`
- New `gmail_account_credentials` schema:
  - `gmail_account_id uuid primary key references gmail_accounts(id) on delete cascade`
  - `user_id uuid not null`
  - `auth_kind text not null check = 'oauth_access_token'`
  - `credential_blob jsonb not null`
  - `created_at timestamptz not null`
  - `updated_at timestamptz not null`
  - composite ownership FK to `gmail_accounts (id, user_id)`
  - RLS owner policy
- Protected credential blob shape:
  - `{"credential_kind": "gmail_oauth_access_token_v1", "access_token": "<token>"}` 

## protected credential storage mechanism used

Gmail credentials are now stored in a dedicated `gmail_account_credentials` table guarded by row-level security and ownership checks, with the Gmail account record carrying only non-secret metadata. The ingestion path resolves the token through that separate protected table instead of reading it from `gmail_accounts`.

## incomplete work

- None inside Sprint 5P scope.

## files changed

- `apps/api/alembic/versions/20260316_0027_gmail_account_credentials.py`
- `ARCHITECTURE.md`
- `RULES.md`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/gmail.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/integration/test_gmail_accounts_api.py`
- `tests/integration/test_migrations.py`
- `tests/unit/test_20260316_0027_gmail_account_credentials.py`
- `tests/unit/test_gmail.py`
- `tests/unit/test_gmail_main.py`
- `BUILD_REPORT.md`

## exact commands run

- `./.venv/bin/python -m pytest tests/unit/test_gmail.py`
- `./.venv/bin/python -m pytest tests/unit/test_gmail_main.py tests/unit/test_20260316_0026_gmail_accounts.py tests/unit/test_20260316_0027_gmail_account_credentials.py`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py`
- `./.venv/bin/python -m pytest tests/integration/test_migrations.py`
- `./.venv/bin/python -m pytest tests/unit`
- `./.venv/bin/python -m pytest tests/integration`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_gmail.py`
  - Result: `12 passed in 0.11s`
- `./.venv/bin/python -m pytest tests/unit/test_gmail_main.py tests/unit/test_20260316_0026_gmail_accounts.py tests/unit/test_20260316_0027_gmail_account_credentials.py`
  - Result: `11 passed in 0.55s`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py`
  - Result: `6 passed in 2.10s`
- `./.venv/bin/python -m pytest tests/integration/test_migrations.py`
  - Result: `3 passed in 1.35s`
- `./.venv/bin/python -m pytest tests/unit`
  - Result: `417 passed in 0.67s`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `134 passed in 41.74s`

## unit and integration test results

- Required unit suite passed.
- Required integration suite passed.
- Gmail-focused unit and integration coverage passed independently before the full-suite runs.
- Migration round-trip coverage now explicitly verifies Gmail credential backfill on upgrade and token restoration on downgrade for revision `20260316_0027`.

## one example Gmail account response proving secret removal

```json
{
  "account": {
    "id": "<gmail-account-id>",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  }
}
```

## one example Gmail ingestion response through the hardened path

```json
{
  "account": {
    "id": "<gmail-account-id>",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "message": {
    "provider_message_id": "msg-001",
    "artifact_relative_path": "gmail/acct-owner-001/msg-001.eml",
    "media_type": "message/rfc822"
  },
  "artifact": {
    "id": "<task-artifact-id>",
    "task_id": "<task-id>",
    "task_workspace_id": "<task-workspace-id>",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "gmail/acct-owner-001/msg-001.eml",
    "media_type_hint": "message/rfc822",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "summary": {
    "total_count": 1,
    "total_characters": 19,
    "media_type": "message/rfc822",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No remaining code blockers.
- Integration verification required local Postgres access outside the default sandbox.

## what remains intentionally deferred to later milestones

- Gmail search
- mailbox sync or backfill jobs
- attachment ingestion
- write-capable Gmail actions
- Calendar connector scope
- OAuth UI or callback handling
- refresh-token lifecycle work
- compile-contract changes
- runner orchestration
- UI work

## recommended next step

Add the next narrow Gmail auth milestone only if needed: refresh-token or external secret-manager support, without broadening into search, sync, Calendar, or UI in the same change.
