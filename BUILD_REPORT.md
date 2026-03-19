# BUILD_REPORT.md

## Sprint Objective
Implement Sprint 6U: add a narrow read-only Calendar connector seam that supports user-scoped calendar account connection metadata and explicit single-event ingestion into existing task artifact/chunk seams.

## Completed Work
- Added Calendar schema + migration support:
  - `calendar_accounts`
  - `calendar_account_credentials`
  - RLS, owner policies, and runtime grants aligned with existing connector patterns.
- Added Calendar protected credential storage path with file-based external secret manager semantics:
  - secret ref format: `users/{user_id}/calendar-account-credentials/{calendar_account_id}.json`
  - credential metadata persisted in `calendar_account_credentials`
  - credential payload externalized (`credential_blob` remains `NULL`)
- Added stable Calendar contracts:
  - account connect input/response
  - account list/detail responses
  - selected-event ingestion input/response
- Added Calendar store seams:
  - create/list/detail account methods
  - credential create/read methods
- Added Calendar service seam (`calendar.py`):
  - deterministic create/list/detail account behavior
  - explicit event fetch by provider event id only
  - event conversion into `text/plain` artifact content
  - registration + ingestion through existing task artifact/chunk pipeline
  - deterministic error surfaces for not-found/unsupported/credential/fetch cases
- Added Calendar secret manager module mirroring existing connector secret-manager rules.
- Added Calendar API endpoints:
  - `POST /v0/calendar-accounts`
  - `GET /v0/calendar-accounts`
  - `GET /v0/calendar-accounts/{calendar_account_id}`
  - `POST /v0/calendar-accounts/{calendar_account_id}/events/{provider_event_id}/ingest`
- Added unit and integration tests for persistence, deterministic listing, ingestion routing, stable response shape, cross-user isolation, and deterministic missing/unsupported failures.
- Synced docs to implemented state so Calendar is no longer described as future/absent:
  - `ARCHITECTURE.md`
  - `README.md`

## Exact Contract Changes Introduced
- New constants in `apps/api/src/alicebot_api/contracts.py`:
  - `CALENDAR_ACCOUNT_LIST_ORDER = ["created_at_asc", "id_asc"]`
  - `CALENDAR_PROVIDER = "google_calendar"`
  - `CALENDAR_AUTH_KIND_OAUTH_ACCESS_TOKEN = "oauth_access_token"`
  - `CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"`
  - `CALENDAR_PROTECTED_CREDENTIAL_KIND = "calendar_oauth_access_token_v1"`
- New dataclasses:
  - `CalendarAccountConnectInput`
  - `CalendarEventIngestInput`
- New typed responses/records:
  - `CalendarAccountRecord`
  - `CalendarAccountConnectResponse`
  - `CalendarAccountListSummary`
  - `CalendarAccountListResponse`
  - `CalendarAccountDetailResponse`
  - `CalendarEventIngestionRecord`
  - `CalendarEventIngestionResponse`

## Calendar Event-to-Artifact Conversion Rule
- Fetch one explicit provider event id from Google Calendar events API (`/calendar/v3/calendars/primary/events/{event_id}`).
- Require event shape to include:
  - non-empty `id`
  - `start.dateTime` or `start.date`
  - `end.dateTime` or `end.date`
- If shape is missing required fields, fail deterministically with:
  - `calendar event {provider_event_id} is not supported for ingestion`
- Convert event payload into normalized UTF-8 `text/plain` document containing deterministic labeled lines:
  - provider metadata
  - requested/source event ids
  - status/summary/location/start/end/organizer/html link
  - description block
- Persist to workspace path:
  - `calendar/{sanitized_provider_account_id}/{sanitized_provider_event_id}.txt`
- Register and ingest through existing `task_artifacts` and `task_artifact_chunks` seams.

## Incomplete Work
- None for the scoped Sprint 6U deliverables.

## Files Changed
- `apps/api/alembic/versions/20260319_0030_calendar_accounts_and_credentials.py`
- `ARCHITECTURE.md`
- `README.md`
- `apps/api/src/alicebot_api/calendar.py`
- `apps/api/src/alicebot_api/calendar_secret_manager.py`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/integration/test_calendar_accounts_api.py`
- `tests/integration/test_migrations.py`
- `tests/unit/test_20260319_0030_calendar_accounts_and_credentials.py`
- `tests/unit/test_calendar.py`
- `tests/unit/test_calendar_main.py`
- `tests/unit/test_calendar_secret_manager.py`
- `tests/unit/test_config.py`
- `BUILD_REPORT.md`

## Tests Run
### Exact Commands
- `./.venv/bin/python -m pytest tests/unit/test_calendar.py tests/unit/test_calendar_main.py tests/unit/test_calendar_secret_manager.py tests/unit/test_20260319_0030_calendar_accounts_and_credentials.py tests/unit/test_config.py -q`
- `./.venv/bin/python -m pytest tests/unit`
- `./.venv/bin/python -m pytest tests/integration`

### Results
- Targeted unit tests: PASS (`28 passed`)
- Full unit suite: PASS (`478 passed`)
- Full integration suite: PASS (`150 passed`)

## Example Calendar Account Response
```json
{
  "account": {
    "id": "3e4c7d67-cf56-4cd5-a8c0-8d4d18e7f1f2",
    "provider": "google_calendar",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/calendar.readonly",
    "created_at": "2026-03-19T10:00:00+00:00",
    "updated_at": "2026-03-19T10:00:00+00:00"
  }
}
```

## Example Selected-Event Ingestion Response
```json
{
  "account": {
    "id": "3e4c7d67-cf56-4cd5-a8c0-8d4d18e7f1f2",
    "provider": "google_calendar",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/calendar.readonly",
    "created_at": "2026-03-19T10:00:00+00:00",
    "updated_at": "2026-03-19T10:00:00+00:00"
  },
  "event": {
    "provider_event_id": "evt-001",
    "artifact_relative_path": "calendar/acct-owner-001/evt-001.txt",
    "media_type": "text/plain"
  },
  "artifact": {
    "id": "6fd2c8f1-a3a1-4272-8e46-7900f8f6d2c9",
    "task_id": "fb3f9ab8-55ce-4237-b43e-f393dcb5a6d2",
    "task_workspace_id": "c6b542ff-7d67-42ed-a7ea-cf0a6f3b0366",
    "status": "registered",
    "ingestion_status": "ingested",
    "relative_path": "calendar/acct-owner-001/evt-001.txt",
    "media_type_hint": "text/plain",
    "created_at": "2026-03-19T10:00:00+00:00",
    "updated_at": "2026-03-19T10:00:01+00:00"
  },
  "summary": {
    "total_count": 1,
    "total_characters": 312,
    "media_type": "text/plain",
    "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## Blockers / Issues
- No functional implementation blockers.
- Note: integration tests require reachable local Postgres; once available, full integration suite passes.

## Intentionally Deferred Scope
- Calendar UI.
- Calendar search/list-events APIs.
- Recurring event expansion.
- Background sync/backfill.
- Write-capable calendar actions.
- Gmail scope expansion.
- Compile contract changes.
- Runner orchestration changes.
- Auth redesign.

## Recommended Next Step
Proceed to reviewer verification focused on sprint-scope boundaries and deterministic isolation behavior, then open the sprint PR for Control Tower approval.
