# BUILD_REPORT

## sprint objective

Implement Sprint 6H by exposing narrow user-scoped continuity APIs over the shipped continuity store:

- `POST /v0/threads`
- `GET /v0/threads`
- `GET /v0/threads/{thread_id}`
- `GET /v0/threads/{thread_id}/sessions`
- `GET /v0/threads/{thread_id}/events`

The work stays inside backend continuity scope and does not widen response generation, task orchestration, Gmail, or UI behavior.

## completed work

- added continuity response contracts and ordering metadata in `apps/api/src/alicebot_api/contracts.py`
- introduced `ThreadCreateInput`
- introduced `ThreadRecord`
- introduced `ThreadCreateResponse`
- introduced `ThreadListSummary`
- introduced `ThreadListResponse`
- introduced `ThreadDetailResponse`
- introduced `ThreadSessionRecord`
- introduced `ThreadSessionListSummary`
- introduced `ThreadSessionListResponse`
- introduced `ThreadEventRecord`
- introduced `ThreadEventListSummary`
- introduced `ThreadEventListResponse`
- introduced continuity ordering constants:
  - `THREAD_LIST_ORDER`
  - `THREAD_SESSION_LIST_ORDER`
  - `THREAD_EVENT_LIST_ORDER`
- added deterministic thread listing support in `apps/api/src/alicebot_api/store.py` with `list_threads()`
- implemented the five scoped continuity endpoints in `apps/api/src/alicebot_api/main.py`
- kept continuity reads user-scoped by reusing the existing RLS-backed `ContinuityStore`
- added unit coverage for create/list/detail/session/event response shape, ordering, and invisible-thread handling
- added Postgres-backed integration coverage for create/list/detail/session/event behavior and cross-user isolation
- added a migration guard asserting the shipped thread created-time index remains present for deterministic continuity review queries

## exact ordering rules

- thread list order: `created_at DESC`, then `id DESC`
- thread session list order: `started_at ASC`, then `created_at ASC`, then `id ASC`
- thread event list order: `sequence_no ASC`

## incomplete work

- no in-scope code deliverables remain incomplete
- intentionally not added:
  - thread rename
  - thread archive
  - session mutation APIs
  - event mutation or deletion behavior
  - thread search, pagination, or filtering
  - `/chat` UI thread selection or thread creation UX

## files changed

- `ARCHITECTURE.md`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/main.py`
- `tests/unit/test_20260310_0001_foundation_continuity.py`
- `tests/unit/test_events.py`
- `tests/integration/test_continuity_api.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_events.py tests/unit/test_20260310_0001_foundation_continuity.py tests/integration/test_continuity_api.py`
  - result: partial pass, then blocked by sandbox-local Postgres access for integration setup
- `./.venv/bin/python -m pytest tests/unit/test_main.py -q`
  - result: PASS (`41` passed)
- `./.venv/bin/python -m pytest tests/integration/test_continuity_api.py`
  - result: PASS (`2` passed)
- `./.venv/bin/python -m pytest tests/unit`
  - result: PASS (`454` passed)
- `./.venv/bin/python -m pytest tests/integration`
  - result: PASS (`145` passed)

## example thread create response

```json
{
  "thread": {
    "id": "30000000-0000-4000-8000-000000000003",
    "title": "Gamma thread",
    "created_at": "2026-03-17T10:00:00+00:00",
    "updated_at": "2026-03-17T10:00:00+00:00"
  }
}
```

## example thread list response

```json
{
  "items": [
    {
      "id": "30000000-0000-4000-8000-000000000003",
      "title": "Gamma thread",
      "created_at": "2026-03-17T10:00:00+00:00",
      "updated_at": "2026-03-17T10:00:00+00:00"
    },
    {
      "id": "00000000-0000-4000-8000-000000000002",
      "title": "Beta thread",
      "created_at": "2026-03-17T09:00:00+00:00",
      "updated_at": "2026-03-17T09:00:00+00:00"
    },
    {
      "id": "00000000-0000-4000-8000-000000000001",
      "title": "Alpha thread",
      "created_at": "2026-03-17T09:00:00+00:00",
      "updated_at": "2026-03-17T09:00:00+00:00"
    }
  ],
  "summary": {
    "total_count": 3,
    "order": ["created_at_desc", "id_desc"]
  }
}
```

## example thread detail response

```json
{
  "thread": {
    "id": "00000000-0000-4000-8000-000000000002",
    "title": "Beta thread",
    "created_at": "2026-03-17T09:00:00+00:00",
    "updated_at": "2026-03-17T09:00:00+00:00"
  }
}
```

## example thread-session list response

```json
{
  "items": [
    {
      "id": "10000000-0000-4000-8000-000000000001",
      "thread_id": "00000000-0000-4000-8000-000000000002",
      "status": "completed",
      "started_at": "2026-03-17T09:00:00+00:00",
      "ended_at": "2026-03-17T09:05:00+00:00",
      "created_at": "2026-03-17T09:00:00+00:00"
    },
    {
      "id": "10000000-0000-4000-8000-000000000002",
      "thread_id": "00000000-0000-4000-8000-000000000002",
      "status": "active",
      "started_at": "2026-03-17T10:00:00+00:00",
      "ended_at": null,
      "created_at": "2026-03-17T10:00:00+00:00"
    }
  ],
  "summary": {
    "thread_id": "00000000-0000-4000-8000-000000000002",
    "total_count": 2,
    "order": ["started_at_asc", "created_at_asc", "id_asc"]
  }
}
```

## example thread-event list response

```json
{
  "items": [
    {
      "id": "20000000-0000-4000-8000-000000000002",
      "thread_id": "00000000-0000-4000-8000-000000000002",
      "session_id": "10000000-0000-4000-8000-000000000002",
      "sequence_no": 1,
      "kind": "message.user",
      "payload": {"text": "Hello"},
      "created_at": "2026-03-17T10:00:00+00:00"
    },
    {
      "id": "20000000-0000-4000-8000-000000000001",
      "thread_id": "00000000-0000-4000-8000-000000000002",
      "session_id": "10000000-0000-4000-8000-000000000002",
      "sequence_no": 2,
      "kind": "message.assistant",
      "payload": {"text": "Hello back"},
      "created_at": "2026-03-17T10:01:00+00:00"
    }
  ],
  "summary": {
    "thread_id": "00000000-0000-4000-8000-000000000002",
    "total_count": 2,
    "order": ["sequence_no_asc"]
  }
}
```

## blockers/issues

- no remaining code blockers inside sprint scope
- local sandbox execution initially blocked localhost Postgres access for integration setup; rerunning the Postgres-backed suite with unrestricted execution resolved verification
- `ARCHITECTURE.md` was updated after review so the documented runtime/API inventory matches the shipped `/v0/threads*` continuity surface

## recommended next step

Use these continuity endpoints in a follow-up `/chat` sprint so the operator can create a thread, browse visible threads, and load thread history without typing raw thread ids manually.

## intentionally deferred after this sprint

- all UI work for thread selection, thread creation, and session history presentation
- any new session write endpoint
- any event rewrite, delete, or archive behavior
- any broader chat orchestration changes
- any Gmail, Calendar, auth, approval, task, execution, or runner scope expansion
