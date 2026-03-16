# BUILD_REPORT

## sprint objective

Implement Sprint 5O: a narrow read-only Gmail connector seam that can persist user-scoped Gmail account metadata and ingest one explicitly selected Gmail message into the existing task artifact and RFC822 chunk pipeline, without adding search, sync, attachments, write actions, Calendar, compile changes, runner work, or UI.

## completed work

- Added a new `gmail_accounts` table and migration with user-scoped row-level security and deterministic listing order.
- Added stable Gmail contracts for:
  - account connect
  - account list
  - account detail
  - single-message ingestion
- Implemented `apps/api/src/alicebot_api/gmail.py` with:
  - Gmail account persistence
  - deterministic account serialization
  - a single explicit Gmail read-only fetch path using `users/me/messages/{message_id}?format=raw`
  - pre-ingestion RFC822 validation against the existing artifact rules
  - deterministic Gmail-message-to-artifact path generation
  - duplicate artifact-path rejection before any Gmail fetch or filesystem write
  - workspace artifact locking aligned with the normal artifact registration seam so duplicate detection, file checks, and write attempts occur inside the same serialized critical section
  - reuse of existing `register_task_artifact_record()` and `ingest_task_artifact_record()`
- Added API endpoints for:
  - `POST /v0/gmail-accounts`
  - `GET /v0/gmail-accounts`
  - `GET /v0/gmail-accounts/{gmail_account_id}`
  - `POST /v0/gmail-accounts/{gmail_account_id}/messages/{provider_message_id}/ingest`
- Added a reusable byte-level artifact extraction helper so Gmail ingestion can validate raw RFC822 content before persisting anything through the artifact seam.
- Added unit and integration coverage for:
  - Gmail account persistence
  - deterministic listing
  - stable response shapes
  - single-message ingestion through the existing artifact and chunk seam
  - sanitized path collision rejection without overwriting the existing `.eml`
  - cross-user workspace rejection
  - missing Gmail message rejection
  - unsupported Gmail message rejection

## exact Gmail account and single-message ingestion contract changes introduced

- Gmail account connect request:
  - `user_id: UUID`
  - `provider_account_id: str`
  - `email_address: str`
  - `display_name: str | null`
  - `scope: "https://www.googleapis.com/auth/gmail.readonly"`
  - `access_token: str`
- Gmail account record response:
  - `id: str`
  - `provider: "gmail"`
  - `auth_kind: "oauth_access_token"`
  - `provider_account_id: str`
  - `email_address: str`
  - `display_name: str | null`
  - `scope: "https://www.googleapis.com/auth/gmail.readonly"`
  - `created_at: str`
  - `updated_at: str`
- Gmail account list response:
  - `items: GmailAccountRecord[]`
  - `summary: { total_count, order }`
- Gmail account detail response:
  - `account: GmailAccountRecord`
- Single-message ingestion request:
  - path params: `gmail_account_id`, `provider_message_id`
  - body: `user_id: UUID`, `task_workspace_id: UUID`
- Single-message ingestion response:
  - `account: GmailAccountRecord`
  - `message: { provider_message_id, artifact_relative_path, media_type }`
  - `artifact: TaskArtifactRecord`
  - `summary: TaskArtifactChunkListSummary`

## Gmail message-to-artifact conversion rule used

- Fetch Gmail message raw bytes from the read-only Gmail API path using the stored access token.
- Require Gmail to return RFC822 `raw` content.
- Validate the raw bytes against the existing `message/rfc822` artifact extraction rules before registration.
- Materialize the message inside the selected visible task workspace at:
  - `gmail/<sanitized-provider-account-id>/<sanitized-provider-message-id>.eml`
- Register that `.eml` file as a `message/rfc822` task artifact.
- Ingest it through the existing artifact pipeline so chunks land in `task_artifact_chunks`.

## incomplete work

- None inside Sprint 5O scope.

## files changed

- `apps/api/alembic/versions/20260316_0026_gmail_accounts.py`
- `ARCHITECTURE.md`
- `apps/api/src/alicebot_api/artifacts.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/gmail.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/integration/test_gmail_accounts_api.py`
- `tests/unit/test_20260316_0026_gmail_accounts.py`
- `tests/unit/test_gmail.py`
- `tests/unit/test_gmail_main.py`
- `BUILD_REPORT.md`

## exact commands run

- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_main.py tests/unit/test_20260316_0026_gmail_accounts.py`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py`
- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_main.py`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py`
- `./.venv/bin/python -m pytest tests/unit`
- `./.venv/bin/python -m pytest tests/integration`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_main.py tests/unit/test_20260316_0026_gmail_accounts.py`
  - Result: `14 passed in 0.57s`
- `./.venv/bin/python -m pytest tests/unit/test_gmail.py tests/unit/test_gmail_main.py`
  - Result: `12 passed in 0.28s`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py`
  - Result: `4 passed in 1.47s`
- `./.venv/bin/python -m pytest tests/integration/test_gmail_accounts_api.py`
  - Result: `5 passed in 1.62s`
- `./.venv/bin/python -m pytest tests/unit`
  - Result: `409 passed in 0.67s`
- `./.venv/bin/python -m pytest tests/integration`
  - Result: `132 passed in 39.29s`

## unit and integration test results

- Full unit suite passed.
- Full integration suite passed.
- Gmail-specific unit and integration coverage passed independently before the full-suite runs.

## one example Gmail account response

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

## one example single-message ingestion response

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
    "total_characters": 90,
    "media_type": "message/rfc822",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- No code blockers remained.
- Full integration verification required local Postgres access outside the default sandbox.

## what remains intentionally deferred to later milestones

- Gmail search
- mailbox sync or backfill jobs
- attachment ingestion
- write-capable Gmail actions
- Calendar connector scope
- OAuth UX or callback UI
- compile-contract changes
- runner-style orchestration
- UI work

## recommended next step

Open a follow-up sprint for credential hardening and a fuller Gmail auth lifecycle if the product needs more than this narrow single-message read-only ingestion path.
