from __future__ import annotations

from datetime import datetime
from uuid import UUID

from alicebot_api.contracts import (
    AdmissionDecisionOutput,
    DEFAULT_MEMORY_CONFIRMATION_STATUS,
    DEFAULT_MEMORY_TYPE,
    DEFAULT_MEMORY_REVIEW_LIMIT,
    DEFAULT_OPEN_LOOP_LIMIT,
    MEMORY_CONFIRMATION_STATUSES,
    OPEN_LOOP_REVIEW_ORDER,
    OPEN_LOOP_STATUSES,
    MEMORY_REVIEW_LABEL_ORDER,
    MEMORY_REVIEW_LABEL_VALUES,
    MEMORY_REVIEW_QUEUE_ORDER,
    MEMORY_REVISION_REVIEW_ORDER,
    MEMORY_REVIEW_ORDER,
    MEMORY_TYPES,
    MemoryCandidateInput,
    MemoryEvaluationSummary,
    MemoryEvaluationSummaryResponse,
    MemoryReviewLabelCounts,
    MemoryReviewLabelCreateResponse,
    MemoryReviewLabelListResponse,
    MemoryReviewLabelRecord,
    MemoryReviewLabelSummary,
    MemoryReviewLabelValue,
    MemoryReviewQueueItem,
    MemoryReviewQueueResponse,
    MemoryReviewQueueSummary,
    MemoryRevisionReviewListResponse,
    MemoryRevisionReviewListSummary,
    MemoryRevisionReviewRecord,
    MemoryReviewDetailResponse,
    MemoryReviewListResponse,
    MemoryReviewListSummary,
    MemoryReviewRecord,
    MemoryReviewStatusFilter,
    OpenLoopCreateInput,
    OpenLoopCreateResponse,
    OpenLoopDetailResponse,
    OpenLoopListResponse,
    OpenLoopListSummary,
    OpenLoopRecord,
    OpenLoopStatusFilter,
    OpenLoopStatusUpdateInput,
    OpenLoopStatusUpdateResponse,
    PersistedMemoryRecord,
    PersistedMemoryRevisionRecord,
    isoformat_or_none,
)
from alicebot_api.store import (
    ContinuityStore,
    JsonObject,
    LabelCountRow,
    MemoryReviewLabelRow,
    MemoryRevisionRow,
    MemoryRow,
    OpenLoopRow,
)


class MemoryAdmissionValidationError(ValueError):
    """Raised when an admission request fails explicit candidate validation."""


class MemoryReviewNotFoundError(LookupError):
    """Raised when a requested memory is not visible inside the current user scope."""


class OpenLoopValidationError(ValueError):
    """Raised when an open-loop request fails explicit lifecycle validation."""


class OpenLoopNotFoundError(LookupError):
    """Raised when a requested open loop is not visible inside the current user scope."""


def _serialize_typed_memory_metadata(memory: MemoryRow) -> JsonObject:
    payload: JsonObject = {}

    if "memory_type" in memory:
        payload["memory_type"] = memory["memory_type"]
    if "confidence" in memory:
        payload["confidence"] = memory["confidence"]
    if "salience" in memory:
        payload["salience"] = memory["salience"]
    if "confirmation_status" in memory:
        payload["confirmation_status"] = memory["confirmation_status"]
    if "valid_from" in memory:
        payload["valid_from"] = isoformat_or_none(memory["valid_from"])
    if "valid_to" in memory:
        payload["valid_to"] = isoformat_or_none(memory["valid_to"])
    if "last_confirmed_at" in memory:
        payload["last_confirmed_at"] = isoformat_or_none(memory["last_confirmed_at"])

    return payload


def _serialize_memory(memory: MemoryRow) -> PersistedMemoryRecord:
    payload: PersistedMemoryRecord = {
        "id": str(memory["id"]),
        "user_id": str(memory["user_id"]),
        "memory_key": memory["memory_key"],
        "value": memory["value"],
        "status": memory["status"],
        "source_event_ids": memory["source_event_ids"],
        "created_at": memory["created_at"].isoformat(),
        "updated_at": memory["updated_at"].isoformat(),
        "deleted_at": isoformat_or_none(memory["deleted_at"]),
    }
    payload.update(_serialize_typed_memory_metadata(memory))
    return payload


def _serialize_memory_revision(revision: MemoryRevisionRow) -> PersistedMemoryRevisionRecord:
    return {
        "id": str(revision["id"]),
        "user_id": str(revision["user_id"]),
        "memory_id": str(revision["memory_id"]),
        "sequence_no": revision["sequence_no"],
        "action": revision["action"],
        "memory_key": revision["memory_key"],
        "previous_value": revision["previous_value"],
        "new_value": revision["new_value"],
        "source_event_ids": revision["source_event_ids"],
        "candidate": revision["candidate"],
        "created_at": revision["created_at"].isoformat(),
    }


def _serialize_memory_review(memory: MemoryRow) -> MemoryReviewRecord:
    payload: MemoryReviewRecord = {
        "id": str(memory["id"]),
        "memory_key": memory["memory_key"],
        "value": memory["value"],
        "status": memory["status"],
        "source_event_ids": memory["source_event_ids"],
        "created_at": memory["created_at"].isoformat(),
        "updated_at": memory["updated_at"].isoformat(),
        "deleted_at": isoformat_or_none(memory["deleted_at"]),
    }
    payload.update(_serialize_typed_memory_metadata(memory))
    return payload


def _serialize_memory_review_queue_item(memory: MemoryRow) -> MemoryReviewQueueItem:
    payload: MemoryReviewQueueItem = {
        "id": str(memory["id"]),
        "memory_key": memory["memory_key"],
        "value": memory["value"],
        "status": memory["status"],
        "source_event_ids": memory["source_event_ids"],
        "created_at": memory["created_at"].isoformat(),
        "updated_at": memory["updated_at"].isoformat(),
    }
    payload.update(_serialize_typed_memory_metadata(memory))
    return payload


def _serialize_memory_revision_review(revision: MemoryRevisionRow) -> MemoryRevisionReviewRecord:
    return {
        "id": str(revision["id"]),
        "memory_id": str(revision["memory_id"]),
        "sequence_no": revision["sequence_no"],
        "action": revision["action"],
        "memory_key": revision["memory_key"],
        "previous_value": revision["previous_value"],
        "new_value": revision["new_value"],
        "source_event_ids": revision["source_event_ids"],
        "created_at": revision["created_at"].isoformat(),
    }


def _serialize_memory_review_label(label: MemoryReviewLabelRow) -> MemoryReviewLabelRecord:
    return {
        "id": str(label["id"]),
        "memory_id": str(label["memory_id"]),
        "reviewer_user_id": str(label["user_id"]),
        "label": label["label"],
        "note": label["note"],
        "created_at": label["created_at"].isoformat(),
    }


def _empty_memory_review_label_counts() -> MemoryReviewLabelCounts:
    return {
        "correct": 0,
        "incorrect": 0,
        "outdated": 0,
        "insufficient_evidence": 0,
    }


def _summarize_memory_review_label_counts(rows: list[LabelCountRow]) -> MemoryReviewLabelCounts:
    counts = _empty_memory_review_label_counts()
    for row in rows:
        label = row["label"]
        if label in counts:
            counts[label] = row["count"]
    return counts


def _build_memory_review_label_summary(
    *,
    memory_id: UUID,
    counts: MemoryReviewLabelCounts,
) -> MemoryReviewLabelSummary:
    return {
        "memory_id": str(memory_id),
        "total_count": sum(counts.values()),
        "counts_by_label": counts,
        "order": list(MEMORY_REVIEW_LABEL_ORDER),
    }


def _normalize_memory_status_filter(status: MemoryReviewStatusFilter) -> str | None:
    if status == "all":
        return None
    return status


def list_memory_review_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    status: MemoryReviewStatusFilter = "active",
    limit: int = DEFAULT_MEMORY_REVIEW_LIMIT,
) -> MemoryReviewListResponse:
    del user_id

    normalized_status = _normalize_memory_status_filter(status)
    total_count = store.count_memories(status=normalized_status)
    memories = store.list_review_memories(status=normalized_status, limit=limit)
    items = [_serialize_memory_review(memory) for memory in memories]
    summary: MemoryReviewListSummary = {
        "status": status,
        "limit": limit,
        "returned_count": len(items),
        "total_count": total_count,
        "has_more": len(items) < total_count,
        "order": list(MEMORY_REVIEW_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def list_memory_review_queue_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    limit: int = DEFAULT_MEMORY_REVIEW_LIMIT,
) -> MemoryReviewQueueResponse:
    del user_id

    total_count = store.count_unlabeled_review_memories()
    memories = store.list_unlabeled_review_memories(limit=limit)
    items = [_serialize_memory_review_queue_item(memory) for memory in memories]
    summary: MemoryReviewQueueSummary = {
        "memory_status": "active",
        "review_state": "unlabeled",
        "limit": limit,
        "returned_count": len(items),
        "total_count": total_count,
        "has_more": len(items) < total_count,
        "order": list(MEMORY_REVIEW_QUEUE_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_memory_review_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    memory_id: UUID,
) -> MemoryReviewDetailResponse:
    del user_id

    memory = store.get_memory_optional(memory_id)
    if memory is None:
        raise MemoryReviewNotFoundError(f"memory {memory_id} was not found")

    return {
        "memory": _serialize_memory_review(memory),
    }


def list_memory_revision_review_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    memory_id: UUID,
    limit: int = DEFAULT_MEMORY_REVIEW_LIMIT,
) -> MemoryRevisionReviewListResponse:
    del user_id

    memory = store.get_memory_optional(memory_id)
    if memory is None:
        raise MemoryReviewNotFoundError(f"memory {memory_id} was not found")

    total_count = store.count_memory_revisions(memory_id)
    revisions = store.list_memory_revisions(memory_id, limit=limit)
    items = [_serialize_memory_revision_review(revision) for revision in revisions]
    summary: MemoryRevisionReviewListSummary = {
        "memory_id": str(memory["id"]),
        "limit": limit,
        "returned_count": len(items),
        "total_count": total_count,
        "has_more": len(items) < total_count,
        "order": list(MEMORY_REVISION_REVIEW_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def create_memory_review_label_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    memory_id: UUID,
    label: MemoryReviewLabelValue,
    note: str | None,
) -> MemoryReviewLabelCreateResponse:
    del user_id

    memory = store.get_memory_optional(memory_id)
    if memory is None:
        raise MemoryReviewNotFoundError(f"memory {memory_id} was not found")

    created_label = store.create_memory_review_label(
        memory_id=memory_id,
        label=label,
        note=note,
    )
    counts = _summarize_memory_review_label_counts(store.list_memory_review_label_counts(memory_id))
    return {
        "label": _serialize_memory_review_label(created_label),
        "summary": _build_memory_review_label_summary(memory_id=memory_id, counts=counts),
    }


def list_memory_review_label_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    memory_id: UUID,
) -> MemoryReviewLabelListResponse:
    del user_id

    memory = store.get_memory_optional(memory_id)
    if memory is None:
        raise MemoryReviewNotFoundError(f"memory {memory_id} was not found")

    items = [_serialize_memory_review_label(label) for label in store.list_memory_review_labels(memory_id)]
    counts = _summarize_memory_review_label_counts(store.list_memory_review_label_counts(memory_id))
    return {
        "items": items,
        "summary": _build_memory_review_label_summary(memory_id=memory_id, counts=counts),
    }


def get_memory_evaluation_summary(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> MemoryEvaluationSummaryResponse:
    del user_id

    total_memory_count = store.count_memories()
    active_memory_count = store.count_memories(status="active")
    deleted_memory_count = store.count_memories(status="deleted")
    labeled_memory_count = store.count_labeled_memories()
    unlabeled_memory_count = store.count_unlabeled_memories()
    label_row_counts = _summarize_memory_review_label_counts(store.list_all_memory_review_label_counts())
    summary: MemoryEvaluationSummary = {
        "total_memory_count": total_memory_count,
        "active_memory_count": active_memory_count,
        "deleted_memory_count": deleted_memory_count,
        "labeled_memory_count": labeled_memory_count,
        "unlabeled_memory_count": unlabeled_memory_count,
        "total_label_row_count": sum(label_row_counts.values()),
        "label_row_counts_by_value": label_row_counts,
        "label_value_order": list(MEMORY_REVIEW_LABEL_VALUES),
    }
    return {
        "summary": summary,
    }


def _serialize_open_loop(open_loop: OpenLoopRow) -> OpenLoopRecord:
    return {
        "id": str(open_loop["id"]),
        "memory_id": None if open_loop["memory_id"] is None else str(open_loop["memory_id"]),
        "title": open_loop["title"],
        "status": open_loop["status"],
        "opened_at": open_loop["opened_at"].isoformat(),
        "due_at": isoformat_or_none(open_loop["due_at"]),
        "resolved_at": isoformat_or_none(open_loop["resolved_at"]),
        "resolution_note": open_loop["resolution_note"],
        "created_at": open_loop["created_at"].isoformat(),
        "updated_at": open_loop["updated_at"].isoformat(),
    }


def _normalize_open_loop_status_filter(status: OpenLoopStatusFilter) -> str | None:
    if status == "all":
        return None
    return status


def _normalize_open_loop_title(
    title: str,
    *,
    error_prefix: str,
    error_type: type[ValueError],
) -> str:
    normalized = title.strip()
    if not normalized:
        raise error_type(f"{error_prefix} must be a non-empty string")
    if len(normalized) > 280:
        raise error_type(f"{error_prefix} must be 280 characters or fewer")
    return normalized


def _normalize_open_loop_resolution_note(note: str | None) -> str | None:
    if note is None:
        return None
    normalized = note.strip()
    if not normalized:
        raise OpenLoopValidationError("resolution_note must be a non-empty string when provided")
    if len(normalized) > 2000:
        raise OpenLoopValidationError("resolution_note must be 2000 characters or fewer")
    return normalized


def _validate_open_loop_status(status: str) -> str:
    if status not in OPEN_LOOP_STATUSES:
        allowed_values = ", ".join(OPEN_LOOP_STATUSES)
        raise OpenLoopValidationError(f"status must be one of: {allowed_values}")
    return status


def list_open_loop_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    status: OpenLoopStatusFilter = "open",
    limit: int = DEFAULT_OPEN_LOOP_LIMIT,
) -> OpenLoopListResponse:
    del user_id

    normalized_status = _normalize_open_loop_status_filter(status)
    total_count = store.count_open_loops(status=normalized_status)
    open_loops = store.list_open_loops(status=normalized_status, limit=limit)
    items = [_serialize_open_loop(open_loop) for open_loop in open_loops]
    summary: OpenLoopListSummary = {
        "status": status,
        "limit": limit,
        "returned_count": len(items),
        "total_count": total_count,
        "has_more": len(items) < total_count,
        "order": list(OPEN_LOOP_REVIEW_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_open_loop_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    open_loop_id: UUID,
) -> OpenLoopDetailResponse:
    del user_id

    open_loop = store.get_open_loop_optional(open_loop_id)
    if open_loop is None:
        raise OpenLoopNotFoundError(f"open loop {open_loop_id} was not found")
    return {
        "open_loop": _serialize_open_loop(open_loop),
    }


def create_open_loop_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    open_loop: OpenLoopCreateInput,
) -> OpenLoopCreateResponse:
    del user_id

    if open_loop.memory_id is not None:
        memory = store.get_memory_optional(open_loop.memory_id)
        if memory is None:
            raise OpenLoopValidationError(
                "memory_id must reference an existing memory owned by the user"
            )

    created = store.create_open_loop(
        memory_id=open_loop.memory_id,
        title=_normalize_open_loop_title(
            open_loop.title,
            error_prefix="title",
            error_type=OpenLoopValidationError,
        ),
        status="open",
        opened_at=None,
        due_at=open_loop.due_at,
        resolved_at=None,
        resolution_note=None,
    )
    return {
        "open_loop": _serialize_open_loop(created),
    }


def update_open_loop_status_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    open_loop_id: UUID,
    request: OpenLoopStatusUpdateInput,
) -> OpenLoopStatusUpdateResponse:
    del user_id

    existing = store.get_open_loop_optional(open_loop_id)
    if existing is None:
        raise OpenLoopNotFoundError(f"open loop {open_loop_id} was not found")

    normalized_status = _validate_open_loop_status(request.status)
    if normalized_status == "open":
        raise OpenLoopValidationError("status transition must be resolved or dismissed")
    if existing["status"] != "open":
        raise OpenLoopValidationError("open loop status can only transition from open")

    updated = store.update_open_loop_status_optional(
        open_loop_id=open_loop_id,
        status=normalized_status,
        resolved_at=None,
        resolution_note=_normalize_open_loop_resolution_note(request.resolution_note),
    )
    if updated is None:
        raise OpenLoopNotFoundError(f"open loop {open_loop_id} was not found")

    return {
        "open_loop": _serialize_open_loop(updated),
    }


def _dedupe_source_event_ids(source_event_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    deduped: list[UUID] = []
    seen: set[UUID] = set()
    for source_event_id in source_event_ids:
        if source_event_id in seen:
            continue
        seen.add(source_event_id)
        deduped.append(source_event_id)
    return tuple(deduped)


def _validate_source_events(store: ContinuityStore, source_event_ids: tuple[UUID, ...]) -> list[str]:
    normalized_event_ids = _dedupe_source_event_ids(source_event_ids)
    if not normalized_event_ids:
        raise MemoryAdmissionValidationError(
            "source_event_ids must include at least one existing event owned by the user"
        )
    source_events = store.list_events_by_ids(list(normalized_event_ids))
    found_event_ids = {event["id"] for event in source_events}
    missing_event_ids = [
        str(source_event_id)
        for source_event_id in normalized_event_ids
        if source_event_id not in found_event_ids
    ]
    if missing_event_ids:
        raise MemoryAdmissionValidationError(
            "source_event_ids must all reference existing events owned by the user: "
            + ", ".join(missing_event_ids)
        )
    return [str(source_event_id) for source_event_id in normalized_event_ids]


def _candidate_payload(candidate: MemoryCandidateInput) -> JsonObject:
    return candidate.as_payload()


def _create_open_loop_for_memory(
    store: ContinuityStore,
    *,
    candidate: MemoryCandidateInput,
    memory: MemoryRow,
) -> OpenLoopRecord | None:
    if candidate.open_loop is None:
        return None

    created = store.create_open_loop(
        memory_id=memory["id"],
        title=_normalize_open_loop_title(
            candidate.open_loop.title,
            error_prefix="open_loop.title",
            error_type=MemoryAdmissionValidationError,
        ),
        status="open",
        opened_at=None,
        due_at=candidate.open_loop.due_at,
        resolved_at=None,
        resolution_note=None,
    )
    return _serialize_open_loop(created)


def _validate_memory_type(memory_type: str | None) -> str | None:
    if memory_type is None:
        return None
    if memory_type not in MEMORY_TYPES:
        allowed_values = ", ".join(MEMORY_TYPES)
        raise MemoryAdmissionValidationError(f"memory_type must be one of: {allowed_values}")
    return memory_type


def _validate_confirmation_status(confirmation_status: str | None) -> str | None:
    if confirmation_status is None:
        return None
    if confirmation_status not in MEMORY_CONFIRMATION_STATUSES:
        allowed_values = ", ".join(MEMORY_CONFIRMATION_STATUSES)
        raise MemoryAdmissionValidationError(
            f"confirmation_status must be one of: {allowed_values}"
        )
    return confirmation_status


def _validate_score(name: str, score: float | None) -> float | None:
    if score is None:
        return None
    normalized = float(score)
    if normalized < 0.0 or normalized > 1.0:
        raise MemoryAdmissionValidationError(f"{name} must be between 0.0 and 1.0")
    return normalized


def _validate_temporal_range(valid_from: datetime | None, valid_to: datetime | None) -> None:
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise MemoryAdmissionValidationError("valid_to must be greater than or equal to valid_from")


def _resolve_memory_typed_metadata(
    *,
    existing_memory: MemoryRow | None,
    candidate: MemoryCandidateInput,
) -> dict[str, object]:
    memory_type = _validate_memory_type(candidate.memory_type)
    confirmation_status = _validate_confirmation_status(candidate.confirmation_status)
    confidence = _validate_score("confidence", candidate.confidence)
    salience = _validate_score("salience", candidate.salience)
    _validate_temporal_range(candidate.valid_from, candidate.valid_to)

    if existing_memory is None:
        return {
            "memory_type": memory_type or DEFAULT_MEMORY_TYPE,
            "confidence": confidence,
            "salience": salience,
            "confirmation_status": confirmation_status or DEFAULT_MEMORY_CONFIRMATION_STATUS,
            "valid_from": candidate.valid_from,
            "valid_to": candidate.valid_to,
            "last_confirmed_at": candidate.last_confirmed_at,
        }

    return {
        "memory_type": memory_type if memory_type is not None else existing_memory.get("memory_type", DEFAULT_MEMORY_TYPE),
        "confidence": confidence if confidence is not None else existing_memory.get("confidence"),
        "salience": salience if salience is not None else existing_memory.get("salience"),
        "confirmation_status": (
            confirmation_status
            if confirmation_status is not None
            else existing_memory.get("confirmation_status", DEFAULT_MEMORY_CONFIRMATION_STATUS)
        ),
        "valid_from": candidate.valid_from if candidate.valid_from is not None else existing_memory.get("valid_from"),
        "valid_to": candidate.valid_to if candidate.valid_to is not None else existing_memory.get("valid_to"),
        "last_confirmed_at": (
            candidate.last_confirmed_at
            if candidate.last_confirmed_at is not None
            else existing_memory.get("last_confirmed_at")
        ),
    }


def admit_memory_candidate(
    store: ContinuityStore,
    *,
    user_id: UUID,
    candidate: MemoryCandidateInput,
) -> AdmissionDecisionOutput:
    del user_id

    source_event_ids = _validate_source_events(store, candidate.source_event_ids)
    existing_memory = store.get_memory_by_key(candidate.memory_key)
    resolved_metadata = _resolve_memory_typed_metadata(
        existing_memory=existing_memory,
        candidate=candidate,
    )

    noop_decision = AdmissionDecisionOutput(
        action="NOOP",
        reason="candidate_default_noop",
        memory=None,
        revision=None,
    )

    if candidate.delete_requested:
        if existing_memory is None or existing_memory["status"] == "deleted":
            return AdmissionDecisionOutput(
                action=noop_decision.action,
                reason="memory_not_found_for_delete",
                memory=None if existing_memory is None else _serialize_memory(existing_memory),
                revision=None,
            )

        memory = store.update_memory(
            memory_id=existing_memory["id"],
            value=existing_memory["value"],
            status="deleted",
            source_event_ids=source_event_ids,
            memory_type=resolved_metadata["memory_type"],
            confidence=resolved_metadata["confidence"],
            salience=resolved_metadata["salience"],
            confirmation_status=resolved_metadata["confirmation_status"],
            valid_from=resolved_metadata["valid_from"],
            valid_to=resolved_metadata["valid_to"],
            last_confirmed_at=resolved_metadata["last_confirmed_at"],
        )
        revision = store.append_memory_revision(
            memory_id=memory["id"],
            action="DELETE",
            memory_key=memory["memory_key"],
            previous_value=existing_memory["value"],
            new_value=None,
            source_event_ids=source_event_ids,
            candidate=_candidate_payload(candidate),
        )
        return AdmissionDecisionOutput(
            action="DELETE",
            reason="source_backed_delete",
            memory=_serialize_memory(memory),
            revision=_serialize_memory_revision(revision),
        )

    if candidate.value is None:
        return AdmissionDecisionOutput(
            action=noop_decision.action,
            reason="candidate_value_missing",
            memory=None if existing_memory is None else _serialize_memory(existing_memory),
            revision=None,
        )

    if existing_memory is None:
        memory = store.create_memory(
            memory_key=candidate.memory_key,
            value=candidate.value,
            status="active",
            source_event_ids=source_event_ids,
            memory_type=resolved_metadata["memory_type"],
            confidence=resolved_metadata["confidence"],
            salience=resolved_metadata["salience"],
            confirmation_status=resolved_metadata["confirmation_status"],
            valid_from=resolved_metadata["valid_from"],
            valid_to=resolved_metadata["valid_to"],
            last_confirmed_at=resolved_metadata["last_confirmed_at"],
        )
        revision = store.append_memory_revision(
            memory_id=memory["id"],
            action="ADD",
            memory_key=memory["memory_key"],
            previous_value=None,
            new_value=candidate.value,
            source_event_ids=source_event_ids,
            candidate=_candidate_payload(candidate),
        )
        return AdmissionDecisionOutput(
            action="ADD",
            reason="source_backed_add",
            memory=_serialize_memory(memory),
            revision=_serialize_memory_revision(revision),
            open_loop=_create_open_loop_for_memory(
                store,
                candidate=candidate,
                memory=memory,
            ),
        )

    metadata_changed = any(
        existing_memory.get(field_name) != resolved_metadata[field_name]
        for field_name in (
            "memory_type",
            "confidence",
            "salience",
            "confirmation_status",
            "valid_from",
            "valid_to",
            "last_confirmed_at",
        )
    )

    if existing_memory["status"] == "active" and existing_memory["value"] == candidate.value and not metadata_changed:
        return AdmissionDecisionOutput(
            action=noop_decision.action,
            reason="memory_unchanged",
            memory=_serialize_memory(existing_memory),
            revision=None,
            open_loop=_create_open_loop_for_memory(
                store,
                candidate=candidate,
                memory=existing_memory,
            ),
        )

    memory = store.update_memory(
        memory_id=existing_memory["id"],
        value=candidate.value,
        status="active",
        source_event_ids=source_event_ids,
        memory_type=resolved_metadata["memory_type"],
        confidence=resolved_metadata["confidence"],
        salience=resolved_metadata["salience"],
        confirmation_status=resolved_metadata["confirmation_status"],
        valid_from=resolved_metadata["valid_from"],
        valid_to=resolved_metadata["valid_to"],
        last_confirmed_at=resolved_metadata["last_confirmed_at"],
    )
    revision = store.append_memory_revision(
        memory_id=memory["id"],
        action="UPDATE",
        memory_key=memory["memory_key"],
        previous_value=existing_memory["value"],
        new_value=candidate.value,
        source_event_ids=source_event_ids,
        candidate=_candidate_payload(candidate),
    )
    return AdmissionDecisionOutput(
        action="UPDATE",
        reason="source_backed_update",
        memory=_serialize_memory(memory),
        revision=_serialize_memory_revision(revision),
        open_loop=_create_open_loop_for_memory(
            store,
            candidate=candidate,
            memory=memory,
        ),
    )
