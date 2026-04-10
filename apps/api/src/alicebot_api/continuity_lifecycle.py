from __future__ import annotations

from uuid import UUID

from alicebot_api.continuity_objects import serialize_continuity_lifecycle_state_from_record
from alicebot_api.contracts import (
    CONTINUITY_LIFECYCLE_LIST_ORDER,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    MAX_CONTINUITY_LIFECYCLE_LIMIT,
    ContinuityLifecycleDetailResponse,
    ContinuityLifecycleListResponse,
    ContinuityLifecycleQueryInput,
    ContinuityReviewObjectRecord,
    isoformat_or_none,
)
from alicebot_api.store import ContinuityObjectRow, ContinuityRecallCandidateRow, ContinuityStore


class ContinuityLifecycleValidationError(ValueError):
    """Raised when a continuity lifecycle inspection request is invalid."""


class ContinuityLifecycleNotFoundError(LookupError):
    """Raised when a continuity object is not visible in scope."""


def _serialize_object(record: ContinuityObjectRow | ContinuityRecallCandidateRow) -> ContinuityReviewObjectRecord:
    return {
        "id": str(record["id"]),
        "capture_event_id": str(record["capture_event_id"]),
        "object_type": record["object_type"],  # type: ignore[typeddict-item]
        "status": record["status"],
        "lifecycle": serialize_continuity_lifecycle_state_from_record(record),
        "title": record["title"],
        "body": record["body"],
        "provenance": record["provenance"],
        "confidence": float(record["confidence"]),
        "last_confirmed_at": isoformat_or_none(record["last_confirmed_at"]),
        "supersedes_object_id": (
            None if record["supersedes_object_id"] is None else str(record["supersedes_object_id"])
        ),
        "superseded_by_object_id": (
            None if record["superseded_by_object_id"] is None else str(record["superseded_by_object_id"])
        ),
        "created_at": (
            record["object_created_at"].isoformat()
            if "object_created_at" in record
            else record["created_at"].isoformat()
        ),
        "updated_at": (
            record["object_updated_at"].isoformat()
            if "object_updated_at" in record
            else record["updated_at"].isoformat()
        ),
    }


def _validate_limit(limit: int) -> None:
    if limit < 1 or limit > MAX_CONTINUITY_LIFECYCLE_LIMIT:
        raise ContinuityLifecycleValidationError(
            f"limit must be between 1 and {MAX_CONTINUITY_LIFECYCLE_LIMIT}"
        )


def list_continuity_lifecycle_state(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContinuityLifecycleQueryInput,
) -> ContinuityLifecycleListResponse:
    del user_id

    _validate_limit(request.limit)
    rows = sorted(
        store.list_continuity_recall_candidates(),
        key=lambda row: (row["object_updated_at"], str(row["id"])),
        reverse=True,
    )
    items = [_serialize_object(row) for row in rows[: request.limit]]
    total_count = len(rows)
    searchable_count = sum(1 for row in rows if row["is_searchable"])
    promotable_count = sum(1 for row in rows if row["is_promotable"])

    return {
        "items": items,
        "summary": {
            "limit": request.limit,
            "returned_count": len(items),
            "total_count": total_count,
            "counts": {
                "preserved_count": sum(1 for row in rows if row["is_preserved"]),
                "searchable_count": searchable_count,
                "promotable_count": promotable_count,
                "not_searchable_count": total_count - searchable_count,
                "not_promotable_count": total_count - promotable_count,
            },
            "order": list(CONTINUITY_LIFECYCLE_LIST_ORDER),
        },
    }


def get_continuity_lifecycle_state(
    store: ContinuityStore,
    *,
    user_id: UUID,
    continuity_object_id: UUID,
) -> ContinuityLifecycleDetailResponse:
    del user_id

    record = store.get_continuity_object_optional(continuity_object_id)
    if record is None:
        raise ContinuityLifecycleNotFoundError(
            f"continuity object {continuity_object_id} was not found"
        )
    return {
        "continuity_object": _serialize_object(record),
    }


def build_default_continuity_lifecycle_query() -> ContinuityLifecycleQueryInput:
    return ContinuityLifecycleQueryInput(limit=DEFAULT_CONTINUITY_LIFECYCLE_LIMIT)
