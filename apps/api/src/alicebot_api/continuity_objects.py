from __future__ import annotations

from uuid import UUID

from alicebot_api.contracts import (
    CONTINUITY_OBJECT_TYPES,
    ContinuityObjectRecord,
)
from alicebot_api.store import ContinuityObjectRow, ContinuityStore, JsonObject


class ContinuityObjectValidationError(ValueError):
    """Raised when a continuity object request is invalid."""


def _serialize_continuity_object(record: ContinuityObjectRow) -> ContinuityObjectRecord:
    return {
        "id": str(record["id"]),
        "capture_event_id": str(record["capture_event_id"]),
        "object_type": record["object_type"],
        "status": record["status"],
        "title": record["title"],
        "body": record["body"],
        "provenance": record["provenance"],
        "confidence": record["confidence"],
        "created_at": record["created_at"].isoformat(),
        "updated_at": record["updated_at"].isoformat(),
    }


def _validate_object_type(object_type: str) -> None:
    if object_type not in CONTINUITY_OBJECT_TYPES:
        allowed = ", ".join(CONTINUITY_OBJECT_TYPES)
        raise ContinuityObjectValidationError(
            f"object_type must be one of: {allowed}"
        )


def _validate_title(title: str) -> None:
    normalized = title.strip()
    if not normalized:
        raise ContinuityObjectValidationError("title must not be empty")
    if len(normalized) > 280:
        raise ContinuityObjectValidationError("title must be 280 characters or fewer")


def _validate_confidence(confidence: float) -> None:
    if confidence < 0.0 or confidence > 1.0:
        raise ContinuityObjectValidationError("confidence must be between 0.0 and 1.0")


def create_continuity_object_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    capture_event_id: UUID,
    object_type: str,
    title: str,
    body: JsonObject,
    provenance: JsonObject,
    confidence: float,
    status: str = "active",
) -> ContinuityObjectRecord:
    del user_id

    _validate_object_type(object_type)
    _validate_title(title)
    _validate_confidence(confidence)

    row = store.create_continuity_object(
        capture_event_id=capture_event_id,
        object_type=object_type,
        status=status,
        title=title.strip(),
        body=body,
        provenance=provenance,
        confidence=confidence,
    )
    return _serialize_continuity_object(row)


def get_continuity_object_for_capture_event(
    store: ContinuityStore,
    *,
    user_id: UUID,
    capture_event_id: UUID,
) -> ContinuityObjectRecord | None:
    del user_id

    row = store.get_continuity_object_by_capture_event_optional(capture_event_id)
    if row is None:
        return None
    return _serialize_continuity_object(row)


def list_continuity_objects_for_capture_events(
    store: ContinuityStore,
    *,
    user_id: UUID,
    capture_event_ids: list[UUID],
) -> dict[str, ContinuityObjectRecord]:
    del user_id

    rows = store.list_continuity_objects_for_capture_events(capture_event_ids)
    serialized = [_serialize_continuity_object(row) for row in rows]
    return {item["capture_event_id"]: item for item in serialized}
