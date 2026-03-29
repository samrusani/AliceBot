from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from alicebot_api.continuity_objects import (
    create_continuity_object_record,
    get_continuity_object_for_capture_event,
    list_continuity_objects_for_capture_events,
)
from alicebot_api.contracts import (
    CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
    CONTINUITY_CAPTURE_LIST_ORDER,
    DEFAULT_CONTINUITY_CAPTURE_LIMIT,
    MAX_CONTINUITY_CAPTURE_LIMIT,
    ContinuityCaptureCreateInput,
    ContinuityCaptureCreateResponse,
    ContinuityCaptureDetailResponse,
    ContinuityCaptureEventRecord,
    ContinuityCaptureInboxItem,
    ContinuityCaptureInboxResponse,
)
from alicebot_api.store import ContinuityCaptureEventRow, ContinuityStore, JsonObject


class ContinuityCaptureValidationError(ValueError):
    """Raised when a continuity capture request is invalid."""


class ContinuityCaptureNotFoundError(LookupError):
    """Raised when a continuity capture event is not visible in scope."""


@dataclass(frozen=True, slots=True)
class DerivedObjectDecision:
    object_type: str
    normalized_text: str
    confidence: float
    admission_reason: str


_EXPLICIT_SIGNAL_TO_OBJECT_TYPE: dict[str, str] = {
    "remember_this": "MemoryFact",
    "task": "NextAction",
    "decision": "Decision",
    "commitment": "Commitment",
    "waiting_for": "WaitingFor",
    "blocker": "Blocker",
    "next_action": "NextAction",
    "note": "Note",
}

_HIGH_CONFIDENCE_PREFIXES: tuple[tuple[str, str, str], ...] = (
    ("decision:", "Decision", "high_confidence_prefix_decision"),
    ("task:", "NextAction", "high_confidence_prefix_task"),
    ("todo:", "NextAction", "high_confidence_prefix_todo"),
    ("next:", "NextAction", "high_confidence_prefix_next_action"),
    ("commitment:", "Commitment", "high_confidence_prefix_commitment"),
    ("waiting for:", "WaitingFor", "high_confidence_prefix_waiting_for"),
    ("blocker:", "Blocker", "high_confidence_prefix_blocker"),
    ("remember:", "MemoryFact", "high_confidence_prefix_remember"),
    ("fact:", "MemoryFact", "high_confidence_prefix_fact"),
    ("note:", "Note", "high_confidence_prefix_note"),
)


def _normalize_content(raw_content: str) -> str:
    return re.sub(r"\s+", " ", raw_content).strip()


def _truncate(value: str, *, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _title_for_object_type(object_type: str, normalized_text: str) -> str:
    if object_type == "Decision":
        prefix = "Decision"
    elif object_type == "Commitment":
        prefix = "Commitment"
    elif object_type == "WaitingFor":
        prefix = "Waiting For"
    elif object_type == "Blocker":
        prefix = "Blocker"
    elif object_type == "NextAction":
        prefix = "Next Action"
    elif object_type == "MemoryFact":
        prefix = "Memory Fact"
    else:
        prefix = "Note"
    return _truncate(f"{prefix}: {normalized_text}", max_length=280)


def _body_for_object_type(
    *,
    object_type: str,
    normalized_text: str,
    raw_content: str,
    explicit_signal: str | None,
) -> JsonObject:
    key_by_type = {
        "Note": "body",
        "MemoryFact": "fact_text",
        "Decision": "decision_text",
        "Commitment": "commitment_text",
        "WaitingFor": "waiting_for_text",
        "Blocker": "blocking_reason",
        "NextAction": "action_text",
    }
    value_key = key_by_type[object_type]
    payload: JsonObject = {
        value_key: normalized_text,
        "raw_content": raw_content,
    }
    payload["explicit_signal"] = explicit_signal
    return payload


def _resolve_explicit_signal_decision(
    *,
    explicit_signal: str,
    normalized_text: str,
) -> DerivedObjectDecision:
    object_type = _EXPLICIT_SIGNAL_TO_OBJECT_TYPE[explicit_signal]
    return DerivedObjectDecision(
        object_type=object_type,
        normalized_text=normalized_text,
        confidence=1.0,
        admission_reason=f"explicit_signal_{explicit_signal}",
    )


def _resolve_high_confidence_decision(normalized_text: str) -> DerivedObjectDecision | None:
    lower = normalized_text.casefold()

    for prefix, object_type, reason in _HIGH_CONFIDENCE_PREFIXES:
        if not lower.startswith(prefix):
            continue

        stripped = _normalize_content(normalized_text[len(prefix) :])
        if not stripped:
            return None

        return DerivedObjectDecision(
            object_type=object_type,
            normalized_text=stripped,
            confidence=0.95,
            admission_reason=reason,
        )

    return None


def _serialize_capture_event(row: ContinuityCaptureEventRow) -> ContinuityCaptureEventRecord:
    return {
        "id": str(row["id"]),
        "raw_content": row["raw_content"],
        "explicit_signal": row["explicit_signal"],
        "admission_posture": row["admission_posture"],
        "admission_reason": row["admission_reason"],
        "created_at": row["created_at"].isoformat(),
    }


def _build_inbox_item(
    capture_event: ContinuityCaptureEventRecord,
    derived_object: dict[str, object] | None,
) -> ContinuityCaptureInboxItem:
    return {
        "capture_event": capture_event,
        "derived_object": derived_object,
    }


def _validate_capture_limit(limit: int) -> None:
    if limit < 1 or limit > MAX_CONTINUITY_CAPTURE_LIMIT:
        raise ContinuityCaptureValidationError(
            f"limit must be between 1 and {MAX_CONTINUITY_CAPTURE_LIMIT}"
        )


def capture_continuity_input(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContinuityCaptureCreateInput,
) -> ContinuityCaptureCreateResponse:
    del user_id

    normalized_text = _normalize_content(request.raw_content)
    if not normalized_text:
        raise ContinuityCaptureValidationError("raw_content must not be empty")

    explicit_signal = request.explicit_signal
    if explicit_signal is not None and explicit_signal not in CONTINUITY_CAPTURE_EXPLICIT_SIGNALS:
        allowed = ", ".join(CONTINUITY_CAPTURE_EXPLICIT_SIGNALS)
        raise ContinuityCaptureValidationError(
            f"explicit_signal must be one of: {allowed}"
        )

    decision: DerivedObjectDecision | None = None
    admission_posture = "TRIAGE"
    admission_reason = "ambiguous_capture_requires_triage"

    if explicit_signal is not None:
        decision = _resolve_explicit_signal_decision(
            explicit_signal=explicit_signal,
            normalized_text=normalized_text,
        )
        admission_posture = "DERIVED"
        admission_reason = decision.admission_reason
    else:
        decision = _resolve_high_confidence_decision(normalized_text)
        if decision is not None:
            admission_posture = "DERIVED"
            admission_reason = decision.admission_reason

    capture_event_row = store.create_continuity_capture_event(
        raw_content=normalized_text,
        explicit_signal=explicit_signal,
        admission_posture=admission_posture,
        admission_reason=admission_reason,
    )

    serialized_capture = _serialize_capture_event(capture_event_row)
    derived_object = None

    if decision is not None:
        provenance: JsonObject = {
            "capture_event_id": str(capture_event_row["id"]),
            "source_kind": "continuity_capture_event",
            "admission_reason": decision.admission_reason,
            "explicit_signal": explicit_signal,
        }
        derived_object = create_continuity_object_record(
            store,
            user_id=UUID(str(capture_event_row["user_id"])),
            capture_event_id=capture_event_row["id"],
            object_type=decision.object_type,
            status="active",
            title=_title_for_object_type(decision.object_type, decision.normalized_text),
            body=_body_for_object_type(
                object_type=decision.object_type,
                normalized_text=decision.normalized_text,
                raw_content=normalized_text,
                explicit_signal=explicit_signal,
            ),
            provenance=provenance,
            confidence=decision.confidence,
        )

    return {
        "capture": _build_inbox_item(serialized_capture, derived_object),
    }


def list_continuity_capture_inbox(
    store: ContinuityStore,
    *,
    user_id: UUID,
    limit: int = DEFAULT_CONTINUITY_CAPTURE_LIMIT,
) -> ContinuityCaptureInboxResponse:
    _validate_capture_limit(limit)

    events = store.list_continuity_capture_events(limit=limit)
    event_ids = [row["id"] for row in events]
    object_map = list_continuity_objects_for_capture_events(
        store,
        user_id=user_id,
        capture_event_ids=event_ids,
    )

    items: list[ContinuityCaptureInboxItem] = []
    triage_count = 0

    for event in events:
        serialized_capture = _serialize_capture_event(event)
        if serialized_capture["admission_posture"] == "TRIAGE":
            triage_count += 1
        items.append(
            _build_inbox_item(
                serialized_capture,
                object_map.get(str(event["id"])),
            )
        )

    total_count = store.count_continuity_capture_events()
    derived_count = len(items) - triage_count

    return {
        "items": items,
        "summary": {
            "limit": limit,
            "returned_count": len(items),
            "total_count": total_count,
            "derived_count": derived_count,
            "triage_count": triage_count,
            "order": list(CONTINUITY_CAPTURE_LIST_ORDER),
        },
    }


def get_continuity_capture_detail(
    store: ContinuityStore,
    *,
    user_id: UUID,
    capture_event_id: UUID,
) -> ContinuityCaptureDetailResponse:
    del user_id

    event = store.get_continuity_capture_event_optional(capture_event_id)
    if event is None:
        raise ContinuityCaptureNotFoundError(
            f"continuity capture event {capture_event_id} was not found"
        )

    serialized_event = _serialize_capture_event(event)
    derived_object = get_continuity_object_for_capture_event(
        store,
        user_id=UUID(str(event["user_id"])),
        capture_event_id=capture_event_id,
    )

    return {
        "capture": _build_inbox_item(serialized_event, derived_object),
    }


__all__ = [
    "ContinuityCaptureNotFoundError",
    "ContinuityCaptureValidationError",
    "capture_continuity_input",
    "get_continuity_capture_detail",
    "list_continuity_capture_inbox",
]
