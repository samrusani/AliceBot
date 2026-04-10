from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from alicebot_api.contracts import (
    DEFAULT_MEMORY_CONFIRMATION_STATUS,
    DEFAULT_MEMORY_PROMOTION_ELIGIBILITY,
    DEFAULT_MEMORY_TRUST_CLASS,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    TEMPORAL_TIMELINE_ORDER,
    EntityRecord,
    TemporalExplainQueryInput,
    TemporalExplainResponse,
    TemporalFactExplainRecord,
    TemporalFactSupersessionRecord,
    TemporalProvenanceRecord,
    TemporalStateAtQueryInput,
    TemporalStateAtResponse,
    TemporalStateEdgeRecord,
    TemporalStateFactRecord,
    TemporalTimelineEventRecord,
    TemporalTimelineQueryInput,
    TemporalTimelineResponse,
    TemporalTrustRecord,
    TemporalValidityRecord,
    isoformat_or_none,
)
from alicebot_api.store import ContinuityStore, EntityEdgeRow, EntityRow, JsonObject, JsonValue, MemoryRevisionRow, MemoryRow


class TemporalStateValidationError(ValueError):
    """Raised when a temporal state request fails explicit validation."""


class TemporalStateNotFoundError(LookupError):
    """Raised when a requested entity is not visible inside the current user scope."""


@dataclass(frozen=True, slots=True)
class _MemorySnapshot:
    memory_id: UUID
    memory_key: str
    value: JsonValue | None
    status: str
    source_event_ids: list[str]
    memory_type: str | None
    confidence: float | None
    confirmation_status: str | None
    trust_class: str | None
    trust_reason: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    created_at: datetime
    effective_revision_id: UUID | None
    effective_revision_sequence_no: int | None
    effective_revision_action: str | None
    effective_revision_created_at: datetime | None


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _resolve_as_of(at: datetime | None) -> datetime:
    if at is None:
        return datetime.now(UTC)
    return _normalize_datetime(at)


def _validate_time_window(*, since: datetime | None, until: datetime | None) -> None:
    if since is not None and until is not None and until < since:
        raise TemporalStateValidationError("until must be greater than or equal to since")


def _serialize_entity(entity: EntityRow) -> EntityRecord:
    return {
        "id": str(entity["id"]),
        "entity_type": entity["entity_type"],
        "name": entity["name"],
        "source_memory_ids": entity["source_memory_ids"],
        "created_at": entity["created_at"].isoformat(),
    }


def _serialize_validity(valid_from: datetime | None, valid_to: datetime | None, *, at: datetime) -> TemporalValidityRecord:
    return {
        "valid_from": isoformat_or_none(valid_from),
        "valid_to": isoformat_or_none(valid_to),
        "effective_at": _is_effective_at(valid_from=valid_from, valid_to=valid_to, at=at),
    }


def _serialize_edge_state(edge: EntityEdgeRow, *, at: datetime) -> TemporalStateEdgeRecord:
    return {
        "id": str(edge["id"]),
        "from_entity_id": str(edge["from_entity_id"]),
        "to_entity_id": str(edge["to_entity_id"]),
        "relationship_type": edge["relationship_type"],
        "validity": _serialize_validity(edge["valid_from"], edge["valid_to"], at=at),
        "source_memory_ids": edge["source_memory_ids"],
        "created_at": edge["created_at"].isoformat(),
    }


def _serialize_fact_state(snapshot: _MemorySnapshot, *, at: datetime) -> TemporalStateFactRecord:
    return {
        "memory_id": str(snapshot.memory_id),
        "memory_key": snapshot.memory_key,
        "value": snapshot.value,
        "status": snapshot.status,
        "validity": _serialize_validity(snapshot.valid_from, snapshot.valid_to, at=at),
        "created_at": snapshot.created_at.isoformat(),
    }


def _parse_optional_candidate_datetime(candidate: JsonObject, key: str) -> datetime | None:
    raw_value = candidate.get(key)
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return _normalize_datetime(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _snapshot_defaults(memory: MemoryRow) -> dict[str, object]:
    return {
        "memory_key": memory["memory_key"],
        "value": None,
        "status": "active",
        "source_event_ids": [],
        "memory_type": None,
        "confidence": None,
        "confirmation_status": DEFAULT_MEMORY_CONFIRMATION_STATUS,
        "trust_class": DEFAULT_MEMORY_TRUST_CLASS,
        "trust_reason": None,
        "valid_from": None,
        "valid_to": None,
    }


def _apply_revision(
    *,
    current: dict[str, object],
    revision: MemoryRevisionRow,
) -> dict[str, object]:
    next_state = dict(current)
    candidate = cast(JsonObject, revision["candidate"])
    next_state["source_event_ids"] = list(revision["source_event_ids"])

    if revision["action"] == "DELETE":
        next_state["status"] = "deleted"
    else:
        next_state["status"] = "active"
        next_state["value"] = revision["new_value"]

    if "memory_type" in candidate:
        next_state["memory_type"] = candidate["memory_type"]
    if "confidence" in candidate:
        next_state["confidence"] = candidate["confidence"]
    if "confirmation_status" in candidate:
        next_state["confirmation_status"] = candidate["confirmation_status"]
    if "trust_class" in candidate:
        next_state["trust_class"] = candidate["trust_class"]
    if "trust_reason" in candidate:
        next_state["trust_reason"] = candidate["trust_reason"]
    if "valid_from" in candidate:
        next_state["valid_from"] = _parse_optional_candidate_datetime(candidate, "valid_from")
    if "valid_to" in candidate:
        next_state["valid_to"] = _parse_optional_candidate_datetime(candidate, "valid_to")
    return next_state


def _reconstruct_memory_snapshot(
    memory: MemoryRow,
    *,
    revisions: list[MemoryRevisionRow],
    at: datetime,
) -> _MemorySnapshot | None:
    if len(revisions) == 0:
        if memory["created_at"] > at:
            return None
        return _MemorySnapshot(
            memory_id=memory["id"],
            memory_key=memory["memory_key"],
            value=memory["value"],
            status=memory["status"],
            source_event_ids=memory["source_event_ids"],
            memory_type=memory["memory_type"],
            confidence=memory["confidence"],
            confirmation_status=memory["confirmation_status"],
            trust_class=memory["trust_class"],
            trust_reason=memory["trust_reason"],
            valid_from=memory["valid_from"],
            valid_to=memory["valid_to"],
            created_at=memory["created_at"],
            effective_revision_id=None,
            effective_revision_sequence_no=None,
            effective_revision_action=None,
            effective_revision_created_at=None,
        )

    state = _snapshot_defaults(memory)
    effective_revision: MemoryRevisionRow | None = None
    for revision in revisions:
        revision_created_at = _normalize_datetime(revision["created_at"])
        if revision_created_at > at:
            break
        state = _apply_revision(current=state, revision=revision)
        effective_revision = revision

    if effective_revision is None:
        return None

    return _MemorySnapshot(
        memory_id=memory["id"],
        memory_key=memory["memory_key"],
        value=cast(JsonValue | None, state["value"]),
        status=cast(str, state["status"]),
        source_event_ids=cast(list[str], state["source_event_ids"]),
        memory_type=cast(str | None, state["memory_type"]),
        confidence=cast(float | None, state["confidence"]),
        confirmation_status=cast(str | None, state["confirmation_status"]),
        trust_class=cast(str | None, state["trust_class"]),
        trust_reason=cast(str | None, state["trust_reason"]),
        valid_from=cast(datetime | None, state["valid_from"]),
        valid_to=cast(datetime | None, state["valid_to"]),
        created_at=memory["created_at"],
        effective_revision_id=effective_revision["id"],
        effective_revision_sequence_no=effective_revision["sequence_no"],
        effective_revision_action=effective_revision["action"],
        effective_revision_created_at=effective_revision["created_at"],
    )


def _is_effective_at(*, valid_from: datetime | None, valid_to: datetime | None, at: datetime) -> bool:
    normalized_valid_from = None if valid_from is None else _normalize_datetime(valid_from)
    normalized_valid_to = None if valid_to is None else _normalize_datetime(valid_to)
    if normalized_valid_from is not None and at < normalized_valid_from:
        return False
    if normalized_valid_to is not None and at > normalized_valid_to:
        return False
    return True


def _is_active_snapshot(snapshot: _MemorySnapshot, *, at: datetime) -> bool:
    if snapshot.status != "active":
        return False
    return _is_effective_at(valid_from=snapshot.valid_from, valid_to=snapshot.valid_to, at=at)


def _load_entity(store: ContinuityStore, *, entity_id: UUID) -> EntityRow:
    entity = store.get_entity_optional(entity_id)
    if entity is None:
        raise TemporalStateNotFoundError(f"entity {entity_id} was not found")
    return entity


def _load_entity_memories(store: ContinuityStore, *, entity: EntityRow) -> list[MemoryRow]:
    memory_ids = [UUID(raw_memory_id) for raw_memory_id in entity["source_memory_ids"]]
    return store.list_memories_by_ids(memory_ids)


def _effective_fact_snapshots(
    store: ContinuityStore,
    *,
    entity: EntityRow,
    at: datetime,
) -> tuple[list[_MemorySnapshot], dict[UUID, _MemorySnapshot], dict[UUID, list[MemoryRevisionRow]]]:
    memories = _load_entity_memories(store, entity=entity)
    revisions_by_memory_id: dict[UUID, list[MemoryRevisionRow]] = {}
    snapshots_by_memory_id: dict[UUID, _MemorySnapshot] = {}
    for memory in memories:
        revisions = store.list_memory_revisions(memory["id"])
        revisions_by_memory_id[memory["id"]] = revisions
        snapshot = _reconstruct_memory_snapshot(memory, revisions=revisions, at=at)
        if snapshot is None:
            continue
        snapshots_by_memory_id[memory["id"]] = snapshot

    active_snapshots = sorted(
        (
            snapshot
            for snapshot in snapshots_by_memory_id.values()
            if _is_active_snapshot(snapshot, at=at)
        ),
        key=lambda snapshot: (snapshot.memory_key, str(snapshot.memory_id)),
    )
    return active_snapshots, snapshots_by_memory_id, revisions_by_memory_id


def _effective_edges(
    store: ContinuityStore,
    *,
    entity_id: UUID,
    at: datetime,
) -> list[EntityEdgeRow]:
    return [
        edge
        for edge in store.list_entity_edges_for_entity(entity_id)
        if edge["created_at"] <= at
        and _is_effective_at(valid_from=edge["valid_from"], valid_to=edge["valid_to"], at=at)
    ]


def get_temporal_state_at(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TemporalStateAtQueryInput,
) -> TemporalStateAtResponse:
    del user_id

    as_of = _resolve_as_of(request.at)
    entity = _load_entity(store, entity_id=request.entity_id)
    facts, _, _ = _effective_fact_snapshots(store, entity=entity, at=as_of)
    edges = sorted(
        _effective_edges(store, entity_id=request.entity_id, at=as_of),
        key=lambda edge: (edge["created_at"], str(edge["id"])),
    )
    return {
        "state_at": {
            "entity": _serialize_entity(entity),
            "facts": [_serialize_fact_state(snapshot, at=as_of) for snapshot in facts],
            "edges": [_serialize_edge_state(edge, at=as_of) for edge in edges],
            "summary": {
                "entity_id": str(entity["id"]),
                "entity_name": entity["name"],
                "entity_type": entity["entity_type"],
                "as_of": as_of.isoformat(),
                "fact_count": len(facts),
                "edge_count": len(edges),
            },
        }
    }


def _timeline_memory_events(
    memory: MemoryRow,
    *,
    revisions: list[MemoryRevisionRow],
    at: datetime,
) -> list[TemporalTimelineEventRecord]:
    events: list[TemporalTimelineEventRecord] = []
    state = _snapshot_defaults(memory)
    for revision in revisions:
        state = _apply_revision(current=state, revision=revision)
        snapshot = _MemorySnapshot(
            memory_id=memory["id"],
            memory_key=memory["memory_key"],
            value=cast(JsonValue | None, state["value"]),
            status=cast(str, state["status"]),
            source_event_ids=cast(list[str], state["source_event_ids"]),
            memory_type=cast(str | None, state["memory_type"]),
            confidence=cast(float | None, state["confidence"]),
            confirmation_status=cast(str | None, state["confirmation_status"]),
            trust_class=cast(str | None, state["trust_class"]),
            trust_reason=cast(str | None, state["trust_reason"]),
            valid_from=cast(datetime | None, state["valid_from"]),
            valid_to=cast(datetime | None, state["valid_to"]),
            created_at=memory["created_at"],
            effective_revision_id=revision["id"],
            effective_revision_sequence_no=revision["sequence_no"],
            effective_revision_action=revision["action"],
            effective_revision_created_at=revision["created_at"],
        )
        events.append(
            {
                "id": str(revision["id"]),
                "event_type": f"fact_{revision['action'].lower()}",
                "object_kind": "fact",
                "object_id": str(memory["id"]),
                "occurred_at": revision["created_at"].isoformat(),
                "summary": f"{memory['memory_key']} {revision['action'].lower()}",
                "payload": {
                    "memory_key": memory["memory_key"],
                    "value": snapshot.value,
                    "status": snapshot.status,
                    "validity": _serialize_validity(snapshot.valid_from, snapshot.valid_to, at=at),
                    "source_event_ids": snapshot.source_event_ids,
                },
            }
        )
    return events


def _timeline_edge_events(edge: EntityEdgeRow, *, at: datetime) -> list[TemporalTimelineEventRecord]:
    events: list[TemporalTimelineEventRecord] = [
        {
            "id": str(edge["id"]),
            "event_type": "edge_recorded",
            "object_kind": "edge",
            "object_id": str(edge["id"]),
            "occurred_at": edge["created_at"].isoformat(),
            "summary": (
                f"{edge['relationship_type']} {edge['from_entity_id']} -> {edge['to_entity_id']}"
            ),
            "payload": {
                "relationship_type": edge["relationship_type"],
                "from_entity_id": str(edge["from_entity_id"]),
                "to_entity_id": str(edge["to_entity_id"]),
                "validity": _serialize_validity(edge["valid_from"], edge["valid_to"], at=at),
                "source_memory_ids": edge["source_memory_ids"],
            },
        }
    ]
    if edge["valid_to"] is not None:
        events.append(
            {
                "id": f"{edge['id']}:valid_to",
                "event_type": "edge_validity_ended",
                "object_kind": "edge",
                "object_id": str(edge["id"]),
                "occurred_at": edge["valid_to"].isoformat(),
                "summary": f"{edge['relationship_type']} validity ended",
                "payload": {
                    "relationship_type": edge["relationship_type"],
                    "from_entity_id": str(edge["from_entity_id"]),
                    "to_entity_id": str(edge["to_entity_id"]),
                    "source_memory_ids": edge["source_memory_ids"],
                },
            }
        )
    return events


def get_temporal_timeline(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TemporalTimelineQueryInput,
) -> TemporalTimelineResponse:
    del user_id

    since = None if request.since is None else _normalize_datetime(request.since)
    until = None if request.until is None else _normalize_datetime(request.until)
    _validate_time_window(since=since, until=until)

    entity = _load_entity(store, entity_id=request.entity_id)
    now = _resolve_as_of(until)
    memories = _load_entity_memories(store, entity=entity)
    edges = store.list_entity_edges_for_entity(request.entity_id)

    events: list[TemporalTimelineEventRecord] = [
        {
            "id": str(entity["id"]),
            "event_type": "entity_created",
            "object_kind": "entity",
            "object_id": str(entity["id"]),
            "occurred_at": entity["created_at"].isoformat(),
            "summary": f"{entity['entity_type']} created",
            "payload": {
                "entity_type": entity["entity_type"],
                "name": entity["name"],
                "source_memory_ids": entity["source_memory_ids"],
            },
        }
    ]
    for memory in memories:
        events.extend(_timeline_memory_events(memory, revisions=store.list_memory_revisions(memory["id"]), at=now))
    for edge in edges:
        events.extend(_timeline_edge_events(edge, at=now))

    filtered_events = [
        event
        for event in events
        if (since is None or _normalize_datetime(datetime.fromisoformat(event["occurred_at"])) >= since)
        and (until is None or _normalize_datetime(datetime.fromisoformat(event["occurred_at"])) <= until)
    ]
    ordered_events = sorted(
        filtered_events,
        key=lambda event: (event["occurred_at"], event["event_type"], event["id"]),
    )
    limited_events = ordered_events[: request.limit]

    return {
        "timeline": {
            "entity": _serialize_entity(entity),
            "events": limited_events,
            "summary": {
                "entity_id": str(entity["id"]),
                "entity_name": entity["name"],
                "entity_type": entity["entity_type"],
                "since": isoformat_or_none(since),
                "until": isoformat_or_none(until),
                "returned_count": len(limited_events),
                "total_count": len(ordered_events),
                "limit": request.limit,
                "order": list(TEMPORAL_TIMELINE_ORDER),
            },
        }
    }


def _fact_trust(snapshot: _MemorySnapshot) -> TemporalTrustRecord:
    return {
        "trust_class": snapshot.trust_class,
        "trust_reason": snapshot.trust_reason,
        "confirmation_status": snapshot.confirmation_status,
        "confidence": snapshot.confidence,
    }


def _fact_provenance(snapshot: _MemorySnapshot) -> TemporalProvenanceRecord:
    return {
        "source_memory_ids": [str(snapshot.memory_id)],
        "source_event_ids": snapshot.source_event_ids,
        "revision_sequence_no": snapshot.effective_revision_sequence_no,
        "revision_action": snapshot.effective_revision_action,
        "revision_created_at": isoformat_or_none(snapshot.effective_revision_created_at),
    }


def _serialize_fact_supersession(
    *,
    revision: MemoryRevisionRow,
    snapshot: _MemorySnapshot,
    at: datetime,
    effective_revision_id_as_of: UUID | None,
) -> TemporalFactSupersessionRecord:
    return {
        "revision_id": str(revision["id"]),
        "sequence_no": revision["sequence_no"],
        "action": revision["action"],
        "created_at": revision["created_at"].isoformat(),
        "value": snapshot.value,
        "status": snapshot.status,
        "validity": _serialize_validity(snapshot.valid_from, snapshot.valid_to, at=at),
        "source_event_ids": snapshot.source_event_ids,
        "effective_at_as_of": effective_revision_id_as_of == revision["id"],
    }


def _fact_supersession_chain(
    memory: MemoryRow,
    *,
    revisions: list[MemoryRevisionRow],
    at: datetime,
    effective_revision_id_as_of: UUID | None,
) -> list[TemporalFactSupersessionRecord]:
    chain: list[TemporalFactSupersessionRecord] = []
    state = _snapshot_defaults(memory)
    for revision in revisions:
        state = _apply_revision(current=state, revision=revision)
        snapshot = _MemorySnapshot(
            memory_id=memory["id"],
            memory_key=memory["memory_key"],
            value=cast(JsonValue | None, state["value"]),
            status=cast(str, state["status"]),
            source_event_ids=cast(list[str], state["source_event_ids"]),
            memory_type=cast(str | None, state["memory_type"]),
            confidence=cast(float | None, state["confidence"]),
            confirmation_status=cast(str | None, state["confirmation_status"]),
            trust_class=cast(str | None, state["trust_class"]),
            trust_reason=cast(str | None, state["trust_reason"]),
            valid_from=cast(datetime | None, state["valid_from"]),
            valid_to=cast(datetime | None, state["valid_to"]),
            created_at=memory["created_at"],
            effective_revision_id=revision["id"],
            effective_revision_sequence_no=revision["sequence_no"],
            effective_revision_action=revision["action"],
            effective_revision_created_at=revision["created_at"],
        )
        chain.append(
            _serialize_fact_supersession(
                revision=revision,
                snapshot=snapshot,
                at=at,
                effective_revision_id_as_of=effective_revision_id_as_of,
            )
        )
    return chain


def _edge_trust(
    *,
    supporting_snapshots: list[_MemorySnapshot],
) -> TemporalTrustRecord:
    if len(supporting_snapshots) == 0:
        return {
            "trust_class": None,
            "trust_reason": None,
            "confirmation_status": None,
            "confidence": None,
        }

    lowest_confidence = min(
        (
            snapshot.confidence
            for snapshot in supporting_snapshots
            if snapshot.confidence is not None
        ),
        default=None,
    )
    representative = supporting_snapshots[0]
    combined_reasons = [
        snapshot.trust_reason
        for snapshot in supporting_snapshots
        if snapshot.trust_reason is not None and snapshot.trust_reason != ""
    ]
    return {
        "trust_class": representative.trust_class,
        "trust_reason": "; ".join(combined_reasons) if combined_reasons else representative.trust_reason,
        "confirmation_status": representative.confirmation_status,
        "confidence": lowest_confidence,
    }


def _edge_provenance(
    edge: EntityEdgeRow,
    *,
    supporting_snapshots: list[_MemorySnapshot],
) -> TemporalProvenanceRecord:
    source_event_ids: list[str] = []
    seen_source_event_ids: set[str] = set()
    for snapshot in supporting_snapshots:
        for source_event_id in snapshot.source_event_ids:
            if source_event_id in seen_source_event_ids:
                continue
            seen_source_event_ids.add(source_event_id)
            source_event_ids.append(source_event_id)
    return {
        "source_memory_ids": list(edge["source_memory_ids"]),
        "source_event_ids": source_event_ids,
        "revision_sequence_no": None,
        "revision_action": None,
        "revision_created_at": None,
    }


def _edge_supersession_chain(
    all_edges: list[EntityEdgeRow],
    *,
    edge: EntityEdgeRow,
    at: datetime,
) -> list[dict[str, object]]:
    related_edges = sorted(
        (
            candidate
            for candidate in all_edges
            if candidate["from_entity_id"] == edge["from_entity_id"]
            and candidate["to_entity_id"] == edge["to_entity_id"]
            and candidate["relationship_type"] == edge["relationship_type"]
        ),
        key=lambda candidate: (candidate["created_at"], str(candidate["id"])),
    )
    return [
        {
            "id": str(candidate["id"]),
            "created_at": candidate["created_at"].isoformat(),
            "validity": _serialize_validity(candidate["valid_from"], candidate["valid_to"], at=at),
            "source_memory_ids": candidate["source_memory_ids"],
            "effective_at_as_of": candidate["id"] == edge["id"],
        }
        for candidate in related_edges
    ]


def get_temporal_explain(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TemporalExplainQueryInput,
) -> TemporalExplainResponse:
    del user_id

    as_of = _resolve_as_of(request.at)
    entity = _load_entity(store, entity_id=request.entity_id)
    active_facts, snapshots_by_memory_id, revisions_by_memory_id = _effective_fact_snapshots(
        store,
        entity=entity,
        at=as_of,
    )
    all_memories = {memory["id"]: memory for memory in _load_entity_memories(store, entity=entity)}
    all_edges = store.list_entity_edges_for_entity(request.entity_id)
    active_edges = [
        edge
        for edge in all_edges
        if edge["created_at"] <= as_of
        and _is_effective_at(valid_from=edge["valid_from"], valid_to=edge["valid_to"], at=as_of)
    ]

    fact_records: list[TemporalFactExplainRecord] = []
    for snapshot in active_facts:
        memory = all_memories[snapshot.memory_id]
        fact_records.append(
            {
                **_serialize_fact_state(snapshot, at=as_of),
                "trust": _fact_trust(snapshot),
                "provenance": _fact_provenance(snapshot),
                "supersession_chain": _fact_supersession_chain(
                    memory,
                    revisions=revisions_by_memory_id.get(snapshot.memory_id, []),
                    at=as_of,
                    effective_revision_id_as_of=snapshot.effective_revision_id,
                ),
            }
        )

    edge_records: list[dict[str, object]] = []
    for edge in sorted(active_edges, key=lambda item: (item["created_at"], str(item["id"]))):
        supporting_snapshots = [
            snapshot
            for raw_memory_id in edge["source_memory_ids"]
            if (snapshot := snapshots_by_memory_id.get(UUID(raw_memory_id))) is not None
        ]
        edge_records.append(
            {
                **_serialize_edge_state(edge, at=as_of),
                "trust": _edge_trust(supporting_snapshots=supporting_snapshots),
                "provenance": _edge_provenance(edge, supporting_snapshots=supporting_snapshots),
                "supersession_chain": _edge_supersession_chain(all_edges, edge=edge, at=as_of),
            }
        )

    return {
        "explain": {
            "entity": _serialize_entity(entity),
            "facts": fact_records,
            "edges": cast(list[dict[str, object]], edge_records),
            "summary": {
                "entity_id": str(entity["id"]),
                "entity_name": entity["name"],
                "entity_type": entity["entity_type"],
                "as_of": as_of.isoformat(),
                "fact_count": len(fact_records),
                "edge_count": len(edge_records),
            },
        }
    }


__all__ = [
    "TemporalStateNotFoundError",
    "TemporalStateValidationError",
    "get_temporal_explain",
    "get_temporal_state_at",
    "get_temporal_timeline",
]
