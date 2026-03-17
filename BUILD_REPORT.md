# BUILD_REPORT

## sprint objective

Implement Sprint 6D by exposing deterministic user-scoped read-only trace review APIs for:

- `GET /v0/traces`
- `GET /v0/traces/{trace_id}`
- `GET /v0/traces/{trace_id}/events`

The sprint stayed limited to explain-why trace reads over existing persisted `traces` and `trace_events` data.

## completed work

- introduced stable trace review contracts in `apps/api/src/alicebot_api/contracts.py`
  - `TraceReviewSummaryRecord`
  - `TraceReviewRecord`
  - `TraceReviewListSummary`
  - `TraceReviewListResponse`
  - `TraceReviewDetailResponse`
  - `TraceReviewEventRecord`
  - `TraceReviewEventListSummary`
  - `TraceReviewEventListResponse`
  - `TRACE_REVIEW_LIST_ORDER`
  - `TRACE_REVIEW_EVENT_LIST_ORDER`
- added a narrow trace review module in `apps/api/src/alicebot_api/traces.py`
  - `list_trace_records()`
  - `get_trace_record()`
  - `list_trace_event_records()`
  - `TraceNotFoundError`
- extended `apps/api/src/alicebot_api/store.py` with read-only trace review queries
  - `list_trace_reviews()`
  - `get_trace_review_optional()`
  - deterministic list SQL with trace-event counts
  - deterministic trace-event SQL ordering
- added FastAPI endpoints in `apps/api/src/alicebot_api/main.py`
  - `GET /v0/traces`
  - `GET /v0/traces/{trace_id}`
  - `GET /v0/traces/{trace_id}/events`
- added unit coverage in `tests/unit/test_traces.py` for
  - deterministic list ordering
  - stable detail shape
  - stable event-list shape
  - invisible-trace not-found behavior
  - endpoint translation and 404 mapping
- added Postgres-backed integration coverage in `tests/integration/test_traces_api.py` for
  - deterministic trace list ordering
  - trace detail reads
  - ordered trace-event reads
  - cross-user isolation
  - invisible-trace 404 behavior

## incomplete work

- none inside the sprint’s scoped backend deliverables
- no UI migration from fixture-backed `/traces`
- no trace creation or mutation changes
- no filtering, search, or expanded explainability surface beyond the three read endpoints

## files changed

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/traces.py`
- `tests/unit/test_traces.py`
- `tests/integration/test_traces_api.py`
- `BUILD_REPORT.md`

## exact ordering rules

- trace list reads use `created_at DESC, id DESC`
- trace-event reads use `sequence_no ASC, id ASC`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_traces.py`
  - PASS
  - `5` tests passed
- `./.venv/bin/python -m pytest tests/integration/test_traces_api.py`
  - initial sandboxed run could not reach local Postgres on `localhost:5432`
  - rerun as part of the full integration suite below passed
- `./.venv/bin/python -m pytest tests/unit`
  - PASS
  - `451` tests passed
- `./.venv/bin/python -m pytest tests/integration`
  - PASS
  - `143` tests passed

## unit and integration test results

- unit result: PASS
  - trace review module coverage and endpoint translation coverage passed
- integration result: PASS
  - live Postgres-backed trace review list/detail/event and isolation coverage passed

## example trace list response

```json
{
  "items": [
    {
      "id": "00000000-0000-4000-8000-000000000002",
      "thread_id": "11111111-1111-4111-8111-111111111111",
      "kind": "tool.proxy.execute",
      "compiler_version": "response_generation_v0",
      "status": "completed",
      "created_at": "2026-03-17T09:00:00+00:00",
      "trace_event_count": 2
    },
    {
      "id": "00000000-0000-4000-8000-000000000001",
      "thread_id": "11111111-1111-4111-8111-111111111111",
      "kind": "context.compile",
      "compiler_version": "continuity_v0",
      "status": "completed",
      "created_at": "2026-03-17T09:00:00+00:00",
      "trace_event_count": 1
    }
  ],
  "summary": {
    "total_count": 2,
    "order": ["created_at_desc", "id_desc"]
  }
}
```

## example trace detail response

```json
{
  "trace": {
    "id": "00000000-0000-4000-8000-000000000002",
    "thread_id": "11111111-1111-4111-8111-111111111111",
    "kind": "tool.proxy.execute",
    "compiler_version": "response_generation_v0",
    "status": "completed",
    "limits": {
      "max_sessions": 1,
      "max_events": 2
    },
    "created_at": "2026-03-17T09:00:00+00:00",
    "trace_event_count": 2
  }
}
```

## example trace-event list response

```json
{
  "items": [
    {
      "id": "10000000-0000-4000-8000-000000000002",
      "trace_id": "00000000-0000-4000-8000-000000000002",
      "sequence_no": 1,
      "kind": "tool.proxy.execute.request",
      "payload": {
        "approval_id": "approval-2"
      },
      "created_at": "2026-03-17T09:00:00+00:00"
    },
    {
      "id": "10000000-0000-4000-8000-000000000001",
      "trace_id": "00000000-0000-4000-8000-000000000002",
      "sequence_no": 2,
      "kind": "tool.proxy.execute.summary",
      "payload": {
        "approval_id": "approval-2"
      },
      "created_at": "2026-03-17T09:00:00+00:00"
    }
  ],
  "summary": {
    "trace_id": "00000000-0000-4000-8000-000000000002",
    "total_count": 2,
    "order": ["sequence_no_asc", "id_asc"]
  }
}
```

## blockers/issues

- no remaining product-scope blockers
- one execution-time environment issue occurred during verification
  - sandboxed integration setup could not connect to local Postgres on `localhost:5432`
  - rerunning the required integration suite with local database access resolved verification

## recommended next step

Hook the existing `/traces` web surface off these live endpoints in a separate sprint, while preserving the same narrow persisted-data-only contract.

## intentionally deferred after this sprint

- any UI changes
- any trace mutation endpoints
- any new trace production behavior
- any connector, Gmail, Calendar, approval-flow, or execution-scope expansion
- any search, filtering, pagination, or explainability enrichment beyond persisted trace and trace-event reads
