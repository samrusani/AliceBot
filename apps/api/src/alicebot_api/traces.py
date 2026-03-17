from __future__ import annotations

from uuid import UUID

from alicebot_api.contracts import (
    TRACE_REVIEW_EVENT_LIST_ORDER,
    TRACE_REVIEW_LIST_ORDER,
    TraceReviewDetailResponse,
    TraceReviewEventListResponse,
    TraceReviewEventListSummary,
    TraceReviewEventRecord,
    TraceReviewListResponse,
    TraceReviewListSummary,
    TraceReviewRecord,
    TraceReviewSummaryRecord,
)
from alicebot_api.store import ContinuityStore, TraceEventRow, TraceReviewRow


class TraceNotFoundError(LookupError):
    """Raised when a requested trace is not visible inside the current user scope."""


def _serialize_trace_summary(trace: TraceReviewRow) -> TraceReviewSummaryRecord:
    return {
        "id": str(trace["id"]),
        "thread_id": str(trace["thread_id"]),
        "kind": trace["kind"],
        "compiler_version": trace["compiler_version"],
        "status": trace["status"],
        "created_at": trace["created_at"].isoformat(),
        "trace_event_count": trace["trace_event_count"],
    }


def _serialize_trace(trace: TraceReviewRow) -> TraceReviewRecord:
    summary = _serialize_trace_summary(trace)
    return {
        **summary,
        "limits": trace["limits"],
    }


def _serialize_trace_event(trace_event: TraceEventRow) -> TraceReviewEventRecord:
    return {
        "id": str(trace_event["id"]),
        "trace_id": str(trace_event["trace_id"]),
        "sequence_no": trace_event["sequence_no"],
        "kind": trace_event["kind"],
        "payload": trace_event["payload"],
        "created_at": trace_event["created_at"].isoformat(),
    }


def list_trace_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> TraceReviewListResponse:
    del user_id

    items = [_serialize_trace_summary(trace) for trace in store.list_trace_reviews()]
    summary: TraceReviewListSummary = {
        "total_count": len(items),
        "order": list(TRACE_REVIEW_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_trace_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    trace_id: UUID,
) -> TraceReviewDetailResponse:
    del user_id

    trace = store.get_trace_review_optional(trace_id)
    if trace is None:
        raise TraceNotFoundError(f"trace {trace_id} was not found")

    return {"trace": _serialize_trace(trace)}


def list_trace_event_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    trace_id: UUID,
) -> TraceReviewEventListResponse:
    del user_id

    trace = store.get_trace_review_optional(trace_id)
    if trace is None:
        raise TraceNotFoundError(f"trace {trace_id} was not found")

    items = [_serialize_trace_event(trace_event) for trace_event in store.list_trace_events(trace_id)]
    summary: TraceReviewEventListSummary = {
        "trace_id": str(trace["id"]),
        "total_count": len(items),
        "order": list(TRACE_REVIEW_EVENT_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }
