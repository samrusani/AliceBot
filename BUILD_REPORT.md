# BUILD_REPORT

## sprint objective

Implement Sprint 5T: externalize the Gmail protected-credential seam behind one explicit secret-manager adapter so `gmail_account_credentials` stores only non-secret locator metadata on the primary path, while preserving secret-free Gmail account reads and the existing single-message ingestion plus refresh/rotation flow.

## completed work

- Added `GMAIL_SECRET_MANAGER_URL` runtime config as the single explicit runtime selector for the Gmail secret-manager adapter. Runtime no longer falls back silently when it is unset.
- Added a Gmail-only external secret-manager adapter in `apps/api/src/alicebot_api/gmail_secret_manager.py`.
- Updated Gmail credential persistence so new connect writes store secrets in the configured file-backed secret manager and persist only:
  - `auth_kind`
  - `credential_kind`
  - `secret_manager_kind`
  - `secret_ref`
  - `credential_blob = NULL`
- Added migration `20260316_0029_gmail_external_secret_manager.py` to:
  - add `credential_kind`, `secret_manager_kind`, and `secret_ref` to `gmail_account_credentials`
  - make `credential_blob` nullable
  - mark pre-existing rows as `secret_manager_kind = 'legacy_db_v0'`
  - enforce that externalized rows are reference-only and legacy rows remain explicitly transitional
- Updated the Gmail service path so:
  - connect writes secrets through the adapter
  - ingestion resolves secrets through the adapter
  - expired-token refresh writes updated secrets through the adapter
  - rotated refresh tokens persist through the adapter
  - secret-resolution and secret-update failures return deterministic Gmail errors without corrupting task artifact state
- Preserved Gmail account list/detail response shape and kept those responses secret-free.
- Updated `ARCHITECTURE.md` so the implemented slice and Gmail credential description now reflect Sprint 5T.
- Restored `.ai/active/SPRINT_PACKET.md` to the Control Tower-owned version after removing the unintended builder edit.
- Added unit and integration coverage for:
  - external secret reference persistence
  - secret-free account responses and normal table reads
  - ingestion through the externalized path
  - refresh and rotation through the externalized path
  - missing external secret failure handling
  - legacy-row transition behavior

## exact Gmail credential schema and contract changes introduced

- Schema:
  - `apps/api/alembic/versions/20260316_0029_gmail_external_secret_manager.py`
  - `gmail_account_credentials` now includes:
    - `credential_kind text not null`
    - `secret_manager_kind text not null`
    - `secret_ref text null`
    - `credential_blob jsonb null`
  - Storage rule:
    - externalized rows: `secret_manager_kind = 'file_v1'`, non-empty `secret_ref`, `credential_blob IS NULL`
    - transition rows: `secret_manager_kind = 'legacy_db_v0'`, `secret_ref IS NULL`, `credential_blob` still contains the old protected payload until first credential read externalizes it
- Internal contract changes:
  - `Settings` now includes `gmail_secret_manager_url`
  - Gmail store rows and write/update methods now carry `credential_kind`, `secret_manager_kind`, and `secret_ref`
- Public API contracts:
  - no Gmail account read response fields changed
  - no Gmail ingestion response fields changed
  - no request payload shape changed

## external secret-manager adapter rule used

- Adapter selector: `GMAIL_SECRET_MANAGER_URL`
- Supported rule in this sprint: `file://<absolute-root>`
- Runtime requirement when unset: fail fast and require `GMAIL_SECRET_MANAGER_URL` to be configured explicitly
- Deterministic local fallback remains a test-only implementation detail via explicit test configuration of `file://<absolute-root>`
- Secret reference format persisted in `gmail_account_credentials.secret_ref`:
  - `users/<user_id>/gmail-account-credentials/<gmail_account_id>.json`
- Secret payload format stored outside the database:
  - same Gmail credential object previously stored in `credential_blob`
  - includes `credential_kind`, `access_token`, and refresh metadata when present

## incomplete work

- None inside Sprint 5T scope.

## files changed

- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/gmail.py`
- `apps/api/src/alicebot_api/gmail_secret_manager.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/alembic/versions/20260316_0029_gmail_external_secret_manager.py`
- `tests/unit/test_config.py`
- `tests/unit/test_gmail.py`
- `tests/unit/test_gmail_main.py`
- `tests/unit/test_gmail_secret_manager.py`
- `tests/unit/test_20260316_0029_gmail_external_secret_manager.py`
- `tests/integration/test_gmail_accounts_api.py`
- `tests/integration/test_migrations.py`
- `ARCHITECTURE.md`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_config.py tests/unit/test_gmail_secret_manager.py tests/unit/test_gmail.py tests/unit/test_gmail_main.py tests/unit/test_20260316_0029_gmail_external_secret_manager.py`
  - Result: `38 passed`
- `./.venv/bin/python -m pytest tests/unit`
  - Result: `446 passed`
- `./.venv/bin/python -m pytest tests/integration/test_migrations.py tests/integration/test_gmail_accounts_api.py`
  - Result: `16 passed`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `141 passed`
- `./.venv/bin/python -m pytest tests/unit`
  - Result after review fixes: `446 passed`
- `./.venv/bin/python -m pytest tests/integration`
  - Result after review fixes: `141 passed`
- `git diff --check -- apps/api/src/alicebot_api/config.py apps/api/src/alicebot_api/gmail.py apps/api/src/alicebot_api/main.py apps/api/src/alicebot_api/store.py apps/api/src/alicebot_api/gmail_secret_manager.py apps/api/alembic/versions/20260316_0029_gmail_external_secret_manager.py tests/unit/test_config.py tests/unit/test_gmail.py tests/unit/test_gmail_main.py tests/unit/test_gmail_secret_manager.py tests/unit/test_20260316_0029_gmail_external_secret_manager.py tests/integration/test_gmail_accounts_api.py tests/integration/test_migrations.py`
  - Result: no diff formatting errors

## one example Gmail account response proving secret-free reads remain intact

```json
{
  "account": {
    "id": "00000000-0000-0000-0000-000000000001",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "2026-03-16T10:00:00+00:00",
    "updated_at": "2026-03-16T10:00:00+00:00"
  }
}
```

- No `access_token`, `refresh_token`, `client_id`, or `client_secret` fields are present on the read surface.

## one example Gmail ingestion response through the externalized credential path

```json
{
  "account": {
    "id": "00000000-0000-0000-0000-000000000001",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-refresh-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "2026-03-16T10:00:00+00:00",
    "updated_at": "2026-03-16T10:00:00+00:00"
  },
  "message": {
    "provider_message_id": "msg-001",
    "artifact_relative_path": "gmail/acct-owner-refresh-001/msg-001.eml",
    "media_type": "message/rfc822"
  },
  "artifact": {
    "id": "00000000-0000-0000-0000-000000000123",
    "task_id": "00000000-0000-0000-0000-000000000010",
    "task_workspace_id": "00000000-0000-0000-0000-000000000020",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "gmail/acct-owner-refresh-001/msg-001.eml",
    "media_type_hint": "message/rfc822",
    "created_at": "2026-03-16T10:00:00+00:00",
    "updated_at": "2026-03-16T10:00:01+00:00"
  },
  "summary": {
    "total_count": 1,
    "total_characters": 16,
    "media_type": "message/rfc822",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No implementation blockers remained.
- Full integration verification required local Postgres access outside the default sandbox; the escalated run completed successfully.
- Transitional note: pre-Sprint-5T `gmail_account_credentials` rows are marked `legacy_db_v0` by migration and externalize on first credential read instead of through a bulk secret-export migration.

## what remains intentionally deferred to later milestones

- Gmail search
- mailbox sync or backfill jobs
- attachment ingestion
- write-capable Gmail actions
- Calendar connector scope
- OAuth UI or callback handling
- broader cross-provider secret abstraction
- compile-contract changes
- runner-style orchestration
- UI work

## recommended next step

Keep the next sprint narrow around one follow-up seam only: either remove the remaining `legacy_db_v0` transition path with a deliberate migration/export plan, or move to the next Gmail behavior slice without widening into search, sync, Calendar, runner, or UI work.
