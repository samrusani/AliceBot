from __future__ import annotations

from uuid import UUID

from alicebot_api.contracts import (
    AdmissionDecisionOutput,
    DEFAULT_MEMORY_REVIEW_LIMIT,
    MEMORY_REVIEW_LABEL_ORDER,
    MEMORY_REVIEW_LABEL_VALUES,
    MEMORY_REVIEW_QUEUE_ORDER,
    MEMORY_REVISION_REVIEW_ORDER,
    MEMORY_REVIEW_ORDER,
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
    PersistedMemoryRecord,
    PersistedMemoryRevisionRecord,
    isoformat_or_none,
)
from alicebot_api.store import ContinuityStore, JsonObject, LabelCountRow, MemoryReviewLabelRow, MemoryRevisionRow, MemoryRow


class MemoryAdmissionValidationError(ValueError):
    """Raised when an admission request fails explicit candidate validation."""


class MemoryReviewNotFoundError(LookupError):
    """Raised when a requested memory is not visible inside the current user scope."""


def _serialize_memory(memory: MemoryRow) -> PersistedMemoryRecord:
    return {
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
    return {
        "id": str(memory["id"]),
        "memory_key": memory["memory_key"],
        "value": memory["value"],
        "status": memory["status"],
        "source_event_ids": memory["source_event_ids"],
        "created_at": memory["created_at"].isoformat(),
        "updated_at": memory["updated_at"].isoformat(),
        "deleted_at": isoformat_or_none(memory["deleted_at"]),
    }


def _serialize_memory_review_queue_item(memory: MemoryRow) -> MemoryReviewQueueItem:
    return {
        "id": str(memory["id"]),
        "memory_key": memory["memory_key"],
        "value": memory["value"],
        "status": memory["status"],
        "source_event_ids": memory["source_event_ids"],
        "created_at": memory["created_at"].isoformat(),
        "updated_at": memory["updated_at"].isoformat(),
    }


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


def admit_memory_candidate(
    store: ContinuityStore,
    *,
    user_id: UUID,
    candidate: MemoryCandidateInput,
) -> AdmissionDecisionOutput:
    del user_id

    source_event_ids = _validate_source_events(store, candidate.source_event_ids)
    existing_memory = store.get_memory_by_key(candidate.memory_key)

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
        )

    if existing_memory["status"] == "active" and existing_memory["value"] == candidate.value:
        return AdmissionDecisionOutput(
            action=noop_decision.action,
            reason="memory_unchanged",
            memory=_serialize_memory(existing_memory),
            revision=None,
        )

    memory = store.update_memory(
        memory_id=existing_memory["id"],
        value=candidate.value,
        status="active",
        source_event_ids=source_event_ids,
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
    )
