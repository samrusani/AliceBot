# BUILD_REPORT

## sprint objective

Implement Sprint 5R: extend the existing Gmail refresh path so single-message ingestion can persist and use a provider-rotated refresh token without exposing secrets in Gmail account reads or expanding into broader Gmail, Calendar, secret-manager, runner, compile-contract, or UI scope.

## completed work

- Added rotation-aware Gmail refresh handling in `apps/api/src/alicebot_api/gmail.py`.
- Changed the refresh helper to capture an optional provider-returned replacement `refresh_token` alongside the renewed access token and expiry.
- Applied the protected-credential replacement rule:
  - if Google returns a non-empty `refresh_token`, persist that replacement token
  - otherwise keep the existing stored `refresh_token`
- Kept renewal writes inside the existing `gmail_account_credentials` seam and continued using the existing single-message ingestion path after a successful protected-credential update.
- Added a deterministic Gmail-specific persistence failure when renewed protected credentials cannot be written back, and mapped that failure to the existing `409` error envelope in `apps/api/src/alicebot_api/main.py`.
- Preserved secret-free Gmail account reads; no secret fields were added to list/detail/connect/ingest responses.
- Added unit coverage for:
  - renewal without refresh-token rotation
  - renewal with refresh-token rotation
  - deterministic failure when protected-credential persistence fails
  - raw refresh helper parsing of provider-returned rotated refresh tokens
- Added integration coverage for:
  - renewal success without refresh-token rotation
  - renewal success with refresh-token rotation
  - deterministic failure when rotated credentials cannot be persisted
  - unchanged secret-free response shape during the rotation-capable path

## incomplete work

- None inside Sprint 5R scope.

## files changed

- `apps/api/src/alicebot_api/gmail.py`
- `apps/api/src/alicebot_api/main.py`
- `tests/unit/test_gmail.py`
- `tests/unit/test_gmail_main.py`
- `tests/unit/test_gmail_refresh.py`
- `tests/integration/test_gmail_accounts_api.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit`
  - Result: `437 passed in 0.64s`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `139 passed in 45.52s`

## exact commands run

- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_refresh.py tests/unit/test_gmail_main.py`
- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_refresh.py tests/unit/test_gmail_main.py tests/integration/test_gmail_accounts_api.py -k 'gmail'`
- `./.venv/bin/python -m pytest tests/unit`
- `./.venv/bin/python -m pytest tests/integration`

## unit and integration test results

- Gmail-focused unit tests passed after updating the remaining stale test double to the new refresh return shape.
- One intermediate sandboxed combined Gmail run could not reach the local Postgres fixture on `localhost:5432`; this was an environment restriction, not an application test failure.
- Required final verification passed:
  - `tests/unit`: `437 passed in 0.64s`
  - `tests/integration`: `139 passed in 45.52s`

## one example Gmail account response proving secret-free reads remain intact

```json
{
  "account": {
    "id": "<gmail-account-id>",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-rotated-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  }
}
```

## one example Gmail ingestion response through the rotation-capable path

```json
{
  "account": {
    "id": "<gmail-account-id>",
    "provider": "gmail",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-rotated-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/gmail.readonly",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "message": {
    "provider_message_id": "msg-001",
    "artifact_relative_path": "gmail/acct-owner-rotated-001/msg-001.eml",
    "media_type": "message/rfc822"
  },
  "artifact": {
    "id": "<task-artifact-id>",
    "task_id": "<task-id>",
    "task_workspace_id": "<task-workspace-id>",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "gmail/acct-owner-rotated-001/msg-001.eml",
    "media_type_hint": "message/rfc822",
    "created_at": "<created-at>",
    "updated_at": "<updated-at>"
  },
  "summary": {
    "total_count": "<chunk-count>",
    "total_characters": "<character-count>",
    "media_type": "message/rfc822",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No remaining implementation blockers.
- Integration verification required elevated access because the default sandbox blocked connections to the local Postgres test fixture on `localhost:5432`.

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

## recommended next step

Keep the next Gmail sprint narrow around one adjacent auth seam only, such as external secret-manager integration for the existing protected credential store, without combining it with search, sync, Calendar, or UI expansion.
