# BUILD_REPORT

## sprint objective

Implement Sprint 5Q: extend the protected Gmail credential seam so the existing single-message ingestion path can renew an expired access token from refresh-token-backed credentials, while keeping Gmail account reads secret-free and leaving broader Gmail and Calendar scope deferred.

## completed work

- Added refresh-token-capable Gmail connect writes with an all-or-none refresh bundle:
  - `refresh_token`
  - `client_id`
  - `client_secret`
  - `access_token_expires_at`
- Extended the protected Gmail credential blob to support two narrow shapes:
  - `gmail_oauth_access_token_v1`
  - `gmail_oauth_refresh_token_v2`
- Added one explicit Gmail token-refresh path using `https://oauth2.googleapis.com/token`.
- Updated Gmail credential resolution so ingestion:
  - uses the stored access token directly when the credential is still usable
  - renews first when a refresh-capable credential is expired
  - persists the refreshed access token and new expiry back into `gmail_account_credentials`
- Added a narrow protected-credential update store method for deterministic renewal writes.
- Added migration `20260316_0028_gmail_refresh_token_lifecycle.py` to:
  - allow the new refreshable credential blob shape
  - grant runtime `UPDATE` on `gmail_account_credentials`
  - downgrade refreshable blobs back to the v1 access-token-only shape
- Kept Gmail account list/detail/connect responses secret-free on reads.
- Added unit and integration coverage for:
  - refresh-token credential persistence
  - successful renewal before single-message ingestion
  - deterministic invalid refresh-credential failure
  - secret-free account responses
  - per-user isolation
  - migration upgrade/downgrade compatibility
- Added direct unit coverage for the raw `refresh_gmail_access_token()` helper, including success, `400/401` rejection mapping, and malformed or transport refresh failures.
- Updated `ARCHITECTURE.md` so the implemented slice and Gmail connector flow reflect Sprint 5Q refresh-token lifecycle behavior.

## exact Gmail refresh-token credential changes introduced

- `GmailAccountConnectInput` now accepts optional `refresh_token`, `client_id`, `client_secret`, and `access_token_expires_at`.
- `ConnectGmailAccountRequest` enforces that those four refresh fields are all present together or all absent.
- Protected credential v1 remains:

```json
{
  "credential_kind": "gmail_oauth_access_token_v1",
  "access_token": "<token>"
}
```

- New protected credential v2 is:

```json
{
  "credential_kind": "gmail_oauth_refresh_token_v2",
  "access_token": "<token>",
  "refresh_token": "<refresh-token>",
  "client_id": "<oauth-client-id>",
  "client_secret": "<oauth-client-secret>",
  "access_token_expires_at": "<iso8601>"
}
```

- `gmail_account_credentials` now allows both v1 and v2 blobs and runtime `UPDATE` so renewal can rewrite the protected record in place.

## token-renewal rule and renewal trigger used

- Renewal trigger: if the protected credential kind is `gmail_oauth_refresh_token_v2` and `access_token_expires_at <= now(UTC)` during Gmail message ingestion.
- Renewal path: POST once to Google’s OAuth token endpoint with `client_id`, `client_secret`, `refresh_token`, and `grant_type=refresh_token`.
- Success behavior: store the new `access_token` plus a recalculated `access_token_expires_at`, then continue the existing single-message Gmail fetch with that refreshed token.
- Non-renewal behavior: if the credential is v1 or the v2 token has not yet expired, use the stored access token directly.
- Deterministic failure behavior:
  - malformed local protected credentials -> `409`
  - Google refresh rejection (`400`/`401`) -> `409`
  - non-deterministic refresh transport/response failures -> `502`
- Failure guardrail: these failures occur before artifact registration, chunk ingestion, or filesystem writes for the Gmail message.

## incomplete work

- None inside Sprint 5Q scope.

## files changed

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/gmail.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/alembic/versions/20260316_0028_gmail_refresh_token_lifecycle.py`
- `ARCHITECTURE.md`
- `tests/unit/test_gmail.py`
- `tests/unit/test_gmail_main.py`
- `tests/unit/test_gmail_refresh.py`
- `tests/unit/test_20260316_0028_gmail_refresh_token_lifecycle.py`
- `tests/integration/test_gmail_accounts_api.py`
- `tests/integration/test_migrations.py`
- `BUILD_REPORT.md`

## exact commands run

- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_main.py tests/unit/test_20260316_0028_gmail_refresh_token_lifecycle.py`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py tests/integration/test_migrations.py`
- `./.venv/bin/python -m pytest tests/unit/test_gmail_refresh.py tests/unit/test_gmail.py tests/unit/test_gmail_main.py`
- `./.venv/bin/python -m pytest tests/unit`
- `./.venv/bin/python -m pytest tests/integration`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_main.py tests/unit/test_20260316_0028_gmail_refresh_token_lifecycle.py`
  - Result: `27 passed in 0.52s`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py tests/integration/test_migrations.py`
  - Result: `12 passed in 4.35s`
- `./.venv/bin/python -m pytest tests/unit/test_gmail_refresh.py tests/unit/test_gmail.py tests/unit/test_gmail_main.py`
  - Result: `31 passed in 0.29s`
- `./.venv/bin/python -m pytest tests/unit`
  - Result: `434 passed in 0.67s`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `137 passed in 41.99s`

## unit and integration test results

- Required unit suite passed.
- Required integration suite passed.
- Gmail-focused unit and integration coverage passed before the full packet-level runs.
- Direct unit coverage now pins the raw Gmail token-refresh helper’s success and error mapping behavior.
- Migration coverage now verifies both:
  - the original Gmail credential hardening round trip
  - the new refresh-token lifecycle migration round trip back to a downgrade-safe v1 blob

## one example Gmail account response proving secret-free reads remain intact

```json
{
  "account": {
    "id": "<gmail-account-id>",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-refresh-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  }
}
```

## one example Gmail ingestion response through the renewal-capable path

```json
{
  "account": {
    "id": "<gmail-account-id>",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-refresh-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "message": {
    "provider_message_id": "msg-001",
    "artifact_relative_path": "gmail/acct-owner-refresh-001/msg-001.eml",
    "media_type": "message/rfc822"
  },
  "artifact": {
    "id": "<task-artifact-id>",
    "task_id": "<task-id>",
    "task_workspace_id": "<task-workspace-id>",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "gmail/acct-owner-refresh-001/msg-001.eml",
    "media_type_hint": "message/rfc822",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "summary": {
    "total_count": 1,
    "total_characters": 18,
    "media_type": "message/rfc822",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No remaining implementation blockers.
- Integration verification required local Postgres access outside the default sandbox.

## what remains intentionally deferred to later milestones

- Gmail search
- mailbox sync or backfill jobs
- attachment ingestion
- write-capable Gmail actions
- Calendar connector scope
- OAuth UI or callback handling
- external secret-manager integration
- compile-contract changes
- runner-style orchestration
- UI work
- refresh-token rotation beyond the single explicit renewal path

## recommended next step

Keep the next Gmail milestone equally narrow: either add refresh-token rotation handling or move the protected Gmail secret seam into an external secret manager, but do not combine that work with search, sync, Calendar, or UI expansion.
