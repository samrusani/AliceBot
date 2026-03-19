# BUILD_REPORT.md

## Sprint Objective
Implement Sprint 6X: a deterministic, user-scoped, read-only Calendar event discovery API for one connected account at `GET /v0/calendar-accounts/{calendar_account_id}/events`, with bounded filters, stable ordering metadata, and no expansion into sync/recurrence/write/UI scope.

## Completed Work
- Added Calendar event discovery contracts in `apps/api/src/alicebot_api/contracts.py`:
  - Constants:
    - `DEFAULT_CALENDAR_EVENT_LIST_LIMIT = 20`
    - `MAX_CALENDAR_EVENT_LIST_LIMIT = 50`
    - `CALENDAR_EVENT_LIST_ORDER = ["start_time_asc", "provider_event_id_asc"]`
  - Request input contract:
    - `CalendarEventListInput(calendar_account_id, limit, time_min, time_max)`
  - Response contracts:
    - `CalendarEventSummaryRecord`
    - `CalendarEventListSummary`
    - `CalendarEventListResponse`
- Implemented read-only event discovery service logic in `apps/api/src/alicebot_api/calendar.py`:
  - `fetch_calendar_event_list_payload(...)` using existing credential/secret seams.
  - `list_calendar_event_records(...)` for one account with user-scoped visibility.
  - `CalendarEventListValidationError` for invalid time windows.
  - Deterministic normalization and sorting of events.
- Added endpoint in `apps/api/src/alicebot_api/main.py`:
  - `GET /v0/calendar-accounts/{calendar_account_id}/events`
  - Query params: `user_id`, `limit`, `time_min`, `time_max`
  - Deterministic error mapping:
    - 404: missing/non-visible account
    - 409: credential missing/invalid/persistence issues
    - 400: invalid query window (`time_min > time_max`)
    - 502: upstream provider fetch failures
- Added/updated tests:
  - `tests/unit/test_calendar.py`
  - `tests/unit/test_calendar_main.py`
  - `tests/integration/test_calendar_accounts_api.py`

## Ordering And Limit Rule
- Ordering rule in response summary: `order = ["start_time_asc", "provider_event_id_asc"]`.
- Deterministic sort key applied server-side after provider fetch:
  1. `start_time` normalized to UTC datetime ascending (all-day `date` values normalize to midnight UTC)
  2. `provider_event_id` ascending
- Limit behavior:
  - Default `limit=20`
  - Hard max `limit=50`
  - Response summary always returns applied `limit`.

## Example Calendar Event List Response
```json
{
  "account": {
    "id": "2f90c8ea-6f04-4d7f-9e5e-b8e7cbfd4b3e",
    "provider": "google_calendar",
    "auth_kind": "oauth_access_token",
    "provider_account_id": "acct-owner-001",
    "email_address": "owner@gmail.example",
    "display_name": "Owner",
    "scope": "https://www.googleapis.com/auth/calendar.readonly",
    "created_at": "2026-03-19T11:02:10.100000+00:00",
    "updated_at": "2026-03-19T11:02:10.100000+00:00"
  },
  "items": [
    {
      "provider_event_id": "evt-a",
      "status": "tentative",
      "summary": "First",
      "start_time": "2026-03-20",
      "end_time": "2026-03-21",
      "html_link": null,
      "updated_at": "2026-03-19T09:00:00+00:00"
    },
    {
      "provider_event_id": "evt-b",
      "status": "confirmed",
      "summary": "Second",
      "start_time": "2026-03-25T09:00:00+00:00",
      "end_time": "2026-03-25T09:45:00+00:00",
      "html_link": null,
      "updated_at": "2026-03-24T08:30:00+00:00"
    }
  ],
  "summary": {
    "total_count": 2,
    "limit": 2,
    "order": ["start_time_asc", "provider_event_id_asc"],
    "time_min": "2026-03-20T00:00:00+00:00",
    "time_max": "2026-03-27T00:00:00+00:00"
  }
}
```

## Incomplete Work
- None within Sprint 6X scope.

## Files Changed
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/calendar.py`
- `apps/api/src/alicebot_api/main.py`
- `tests/unit/test_calendar.py`
- `tests/unit/test_calendar_main.py`
- `tests/integration/test_calendar_accounts_api.py`
- `BUILD_REPORT.md`

## Tests Run
- `./.venv/bin/python -m pytest tests/unit/test_calendar.py tests/unit/test_calendar_main.py tests/integration/test_calendar_accounts_api.py` -> PASS (`30 passed`)
- `./.venv/bin/python -m pytest tests/unit` -> PASS (`484 passed`)
- `./.venv/bin/python -m pytest tests/integration` -> PASS (`153 passed`)

## Blockers / Issues
- No implementation blockers.
- Integration tests required DB access outside sandbox to reach local Postgres (`localhost:5432`), then passed with escalated execution.
- Existing unrelated pre-existing modifications remained untouched in:
  - `.ai/active/SPRINT_PACKET.md`
  - `REVIEW_REPORT.md`

## Intentionally Deferred After This Sprint
- UI changes.
- Event ingestion behavior changes.
- Recurring event expansion.
- Background sync/backfill.
- Write-capable calendar actions.
- Gmail scope expansion.
- Auth redesign.
- Runner orchestration.

## Recommended Next Step
Proceed to reviewer validation focused on deterministic event discovery behavior (ordering/limits/isolation/error mapping), then merge if review is PASS.
