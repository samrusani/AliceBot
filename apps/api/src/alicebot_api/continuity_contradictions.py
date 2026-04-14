from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import re
from typing import Iterable, cast
from uuid import UUID

from alicebot_api.contracts import (
    ContinuityLifecycleStateRecord,
    CONTRADICTION_CASE_LIST_ORDER,
    ContradictionCaseDetailResponse,
    ContradictionCaseListQueryInput,
    ContradictionCaseListResponse,
    ContradictionCaseListSummary,
    ContradictionCaseRecord,
    ContradictionKind,
    ContradictionResolveInput,
    ContradictionResolveResponse,
    ContradictionStatus,
    ContradictionSyncInput,
    ContradictionSyncResponse,
    ContradictionSyncSummary,
    ContinuityExplanationContradictionRecord,
    ContinuityReviewObjectRecord,
    MemoryTrustClass,
    TrustSignalDirection,
    isoformat_or_none,
)
from alicebot_api.store import (
    ContinuityObjectRow,
    ContinuityRecallCandidateRow,
    ContinuityStore,
    ContradictionCaseRow,
    JsonObject,
)


class ContinuityContradictionValidationError(ValueError):
    """Raised when contradiction requests are invalid."""


class ContinuityContradictionNotFoundError(LookupError):
    """Raised when a contradiction case is not visible in scope."""


_STATUSES_ALL: list[ContradictionStatus] = ["open", "resolved", "dismissed"]
_TRUST_CLASS_PRIORITY: dict[MemoryTrustClass, int] = {
    "human_curated": 4,
    "deterministic": 3,
    "llm_corroborated": 2,
    "llm_single_source": 1,
}
_SOURCE_TIER_PRIORITY: dict[str, int] = {
    "primary": 4,
    "secondary": 3,
    "derived": 2,
    "weak": 1,
}
_CONTRADICTION_PENALTY: dict[ContradictionKind, float] = {
    "direct_fact_conflict": 2.0,
    "preference_conflict": 1.5,
    "temporal_conflict": 1.25,
    "source_hierarchy_conflict": 1.0,
}
_SUBJECT_KEYS = {
    "subject",
    "fact_key",
    "preference_key",
    "preference_subject",
    "state_key",
    "status_key",
    "decision_key",
    "commitment_key",
    "waiting_for_key",
    "blocker_key",
    "action_key",
    "topic",
    "name",
}
_VALUE_KEYS = {
    "value",
    "fact_value",
    "preference_value",
    "state",
    "status_value",
    "decision_value",
    "commitment_value",
}
_TEXT_KEYS = (
    "preference_text",
    "fact_text",
    "decision_text",
    "commitment_text",
    "waiting_for_text",
    "blocker_text",
    "action_text",
)
_TEMPORAL_START_KEYS = {
    "valid_from",
    "start_time",
    "start_at",
    "effective_from",
    "since",
}
_TEMPORAL_END_KEYS = {
    "valid_to",
    "end_time",
    "end_at",
    "effective_to",
    "until",
    "due_at",
}
_PREFERENCE_PATTERNS = (
    re.compile(
        r"(?:(?:i|we)\s+)?(?:prefer|like|love|hate|dislike|avoid)\s+(?P<value>.+?)(?:\s+(?:for|in|with)\s+(?P<subject>.+))?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<subject>.+?)\s+(?:should use|uses|prefers)\s+(?P<value>.+)",
        re.IGNORECASE,
    ),
)
_FACT_PATTERNS = (
    re.compile(r"(?P<subject>.+?)\s+(?:is|are|was|were)\s+(?P<value>.+)", re.IGNORECASE),
    re.compile(r"(?P<subject>.+?)\s*[:=-]\s*(?P<value>.+)", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class _Claim:
    subject: str
    value: str
    preference_like: bool
    temporal_start: datetime | None
    temporal_end: datetime | None
    source_priority: int


@dataclass(frozen=True, slots=True)
class _DetectedContradiction:
    canonical_key: str
    primary_object_id: UUID
    counterpart_object_id: UUID
    primary_object_updated_at: datetime
    counterpart_object_updated_at: datetime
    kind: ContradictionKind
    rationale: str
    payload: JsonObject


@dataclass(frozen=True, slots=True)
class _SyncOutcome:
    cases: list[ContradictionCaseRow]
    scanned_object_count: int
    open_case_count: int
    resolved_case_count: int
    updated_case_count: int


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _validate_status(status: str) -> ContradictionStatus:
    if status not in _STATUSES_ALL:
        allowed = ", ".join(_STATUSES_ALL)
        raise ContinuityContradictionValidationError(f"status must be one of: {allowed}")
    return cast(ContradictionStatus, status)


def _normalize_text(value: object) -> str | None:
    if not isinstance(value, (str, int, float, bool)):
        return None
    normalized = " ".join(str(value).split()).strip()
    return normalized.casefold() if normalized else None


def _normalize_display_text(value: object) -> str | None:
    if not isinstance(value, (str, int, float, bool)):
        return None
    normalized = " ".join(str(value).split()).strip()
    return normalized or None


def _iter_items(payload: object, *, prefix: str = "") -> list[tuple[str, object]]:
    items: list[tuple[str, object]] = []
    if isinstance(payload, dict):
        for key, child in payload.items():
            next_prefix = key if prefix == "" else f"{prefix}.{key}"
            items.extend(_iter_items(child, prefix=next_prefix))
        return items
    if isinstance(payload, list):
        for child in payload:
            items.extend(_iter_items(child, prefix=prefix))
        return items
    items.append((prefix.casefold(), payload))
    return items


def _find_first_text(payloads: Iterable[object], *, keys: set[str]) -> str | None:
    for payload in payloads:
        for key, value in _iter_items(payload):
            if key.split(".")[-1] in keys:
                normalized = _normalize_display_text(value)
                if normalized is not None:
                    return normalized
    return None


def _find_first_datetime(payloads: Iterable[object], *, keys: set[str]) -> datetime | None:
    for payload in payloads:
        for key, value in _iter_items(payload):
            if key.split(".")[-1] not in keys:
                continue
            if isinstance(value, datetime):
                return _normalize_datetime(value)
            if isinstance(value, str):
                try:
                    return _normalize_datetime(datetime.fromisoformat(value))
                except ValueError:
                    continue
    return None


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _source_priority(payloads: Iterable[object]) -> int:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        source_priority = payload.get("source_priority")
        if isinstance(source_priority, int):
            return source_priority
        source_tier = payload.get("source_tier")
        if isinstance(source_tier, str):
            resolved = _SOURCE_TIER_PRIORITY.get(source_tier.strip().casefold())
            if resolved is not None:
                return resolved
        trust_class = payload.get("trust_class")
        if isinstance(trust_class, str) and trust_class in _TRUST_CLASS_PRIORITY:
            return _TRUST_CLASS_PRIORITY[cast(MemoryTrustClass, trust_class)]
    return 0


def _claim_from_structured_fields(row: ContinuityRecallCandidateRow) -> _Claim | None:
    payloads: tuple[object, ...] = (row["body"], row["provenance"])
    subject = _find_first_text(payloads, keys=_SUBJECT_KEYS)
    value = _find_first_text(payloads, keys=_VALUE_KEYS)
    preference_text = _find_first_text(payloads, keys={"preference_text"})
    if subject is not None and value is not None:
        return _Claim(
            subject=subject.casefold(),
            value=value.casefold(),
            preference_like=preference_text is not None,
            temporal_start=_find_first_datetime(payloads, keys=_TEMPORAL_START_KEYS),
            temporal_end=_find_first_datetime(payloads, keys=_TEMPORAL_END_KEYS),
            source_priority=_source_priority(payloads),
        )
    return None


def _claim_from_text_patterns(row: ContinuityRecallCandidateRow) -> _Claim | None:
    payloads: tuple[object, ...] = (row["body"], row["provenance"])
    for text_key in _TEXT_KEYS:
        text_value = _find_first_text(payloads, keys={text_key})
        if text_value is None:
            continue
        patterns = _PREFERENCE_PATTERNS if text_key == "preference_text" else _FACT_PATTERNS
        for pattern in patterns:
            match = pattern.fullmatch(text_value)
            if match is None:
                continue
            subject = _normalize_display_text(match.groupdict().get("subject"))
            value = _normalize_display_text(match.groupdict().get("value"))
            if subject is None or value is None:
                continue
            return _Claim(
                subject=subject.casefold(),
                value=value.casefold(),
                preference_like=text_key == "preference_text",
                temporal_start=_find_first_datetime(payloads, keys=_TEMPORAL_START_KEYS),
                temporal_end=_find_first_datetime(payloads, keys=_TEMPORAL_END_KEYS),
                source_priority=_source_priority(payloads),
            )
    return None


def _extract_claim(row: ContinuityRecallCandidateRow) -> _Claim | None:
    structured = _claim_from_structured_fields(row)
    if structured is not None:
        return structured
    return _claim_from_text_patterns(row)


def _is_live_contradiction_source(row: ContinuityRecallCandidateRow) -> bool:
    if row["status"] not in {"active", "stale"}:
        return False
    return row["superseded_by_object_id"] is None


def _time_ranges_overlap(
    left_start: datetime | None,
    left_end: datetime | None,
    right_start: datetime | None,
    right_end: datetime | None,
) -> bool:
    resolved_left_start = datetime.min.replace(tzinfo=UTC) if left_start is None else left_start
    resolved_left_end = datetime.max.replace(tzinfo=UTC) if left_end is None else left_end
    resolved_right_start = datetime.min.replace(tzinfo=UTC) if right_start is None else right_start
    resolved_right_end = datetime.max.replace(tzinfo=UTC) if right_end is None else right_end
    return resolved_left_start <= resolved_right_end and resolved_right_start <= resolved_left_end


def _canonical_pair(
    left: ContinuityRecallCandidateRow,
    right: ContinuityRecallCandidateRow,
) -> tuple[ContinuityRecallCandidateRow, ContinuityRecallCandidateRow]:
    left_key = (left["object_updated_at"], str(left["id"]))
    right_key = (right["object_updated_at"], str(right["id"]))
    if left_key >= right_key:
        return left, right
    return right, left


def _detect_pair(
    left: ContinuityRecallCandidateRow,
    right: ContinuityRecallCandidateRow,
) -> _DetectedContradiction | None:
    if left["id"] == right["id"]:
        return None
    if left["status"] == "deleted" or right["status"] == "deleted":
        return None
    left_claim = _extract_claim(left)
    right_claim = _extract_claim(right)
    if left_claim is None or right_claim is None:
        return None
    if left_claim.subject != right_claim.subject:
        return None
    if left_claim.value == right_claim.value:
        return None

    primary, counterpart = _canonical_pair(left, right)
    primary_claim = left_claim if primary["id"] == left["id"] else right_claim
    counterpart_claim = right_claim if primary["id"] == left["id"] else left_claim

    kind: ContradictionKind
    if (
        primary_claim.temporal_start is not None
        or primary_claim.temporal_end is not None
        or counterpart_claim.temporal_start is not None
        or counterpart_claim.temporal_end is not None
    ) and _time_ranges_overlap(
        primary_claim.temporal_start,
        primary_claim.temporal_end,
        counterpart_claim.temporal_start,
        counterpart_claim.temporal_end,
    ):
        kind = "temporal_conflict"
    elif primary_claim.preference_like or counterpart_claim.preference_like:
        kind = "preference_conflict"
    elif primary_claim.source_priority != counterpart_claim.source_priority:
        kind = "source_hierarchy_conflict"
    else:
        kind = "direct_fact_conflict"

    rationale = (
        f"Conflicting subject '{primary_claim.subject}' has competing values "
        f"'{primary_claim.value}' and '{counterpart_claim.value}'."
    )
    canonical_material = "|".join(
        [
            kind,
            primary_claim.subject,
            str(primary["id"]),
            str(counterpart["id"]),
        ]
    )
    canonical_key = f"{kind}:{sha256(canonical_material.encode('utf-8')).hexdigest()}"
    payload: JsonObject = {
        "subject": primary_claim.subject,
        "primary_value": primary_claim.value,
        "counterpart_value": counterpart_claim.value,
        "primary_object_type": primary["object_type"],
        "counterpart_object_type": counterpart["object_type"],
        "primary_status": primary["status"],
        "counterpart_status": counterpart["status"],
    }
    if primary_claim.temporal_start is not None:
        payload["primary_temporal_start"] = primary_claim.temporal_start.isoformat()
    if primary_claim.temporal_end is not None:
        payload["primary_temporal_end"] = primary_claim.temporal_end.isoformat()
    if counterpart_claim.temporal_start is not None:
        payload["counterpart_temporal_start"] = counterpart_claim.temporal_start.isoformat()
    if counterpart_claim.temporal_end is not None:
        payload["counterpart_temporal_end"] = counterpart_claim.temporal_end.isoformat()

    return _DetectedContradiction(
        canonical_key=canonical_key,
        primary_object_id=primary["id"],
        counterpart_object_id=counterpart["id"],
        primary_object_updated_at=primary["object_updated_at"],
        counterpart_object_updated_at=counterpart["object_updated_at"],
        kind=kind,
        rationale=rationale,
        payload=payload,
    )


def _serialize_review_object(record: ContinuityObjectRow) -> ContinuityReviewObjectRecord:
    return {
        "id": str(record["id"]),
        "capture_event_id": str(record["capture_event_id"]),
        "object_type": record["object_type"],
        "status": record["status"],
        "lifecycle": _serialize_lifecycle(record),
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
        "created_at": record["created_at"].isoformat(),
        "updated_at": record["updated_at"].isoformat(),
    }


def _serialize_lifecycle(record: ContinuityObjectRow) -> ContinuityLifecycleStateRecord:
    is_preserved = bool(record.get("is_preserved", True))
    is_searchable = bool(record.get("is_searchable", record["object_type"] != "Note"))
    is_promotable = bool(
        record.get(
            "is_promotable",
            record["object_type"] in {"Decision", "Commitment", "WaitingFor", "Blocker", "NextAction"},
        )
    )
    return {
        "is_preserved": is_preserved,
        "preservation_status": "preserved" if is_preserved else "not_preserved",
        "is_searchable": is_searchable,
        "searchability_status": "searchable" if is_searchable else "not_searchable",
        "is_promotable": is_promotable,
        "promotion_status": "promotable" if is_promotable else "not_promotable",
    }


def _case_or_raise(
    store: ContinuityStore,
    *,
    contradiction_case_id: UUID,
) -> ContradictionCaseRow:
    record = store.get_contradiction_case_optional(contradiction_case_id)
    if record is None:
        raise ContinuityContradictionNotFoundError(
            f"contradiction case {contradiction_case_id} was not found"
        )
    return record


def _serialize_case(
    store: ContinuityStore,
    record: ContradictionCaseRow,
) -> ContradictionCaseRecord:
    continuity_object = store.get_continuity_object_optional(record["continuity_object_id"])
    counterpart_object = store.get_continuity_object_optional(record["counterpart_object_id"])
    if continuity_object is None or counterpart_object is None:
        raise ContinuityContradictionNotFoundError(
            f"contradiction case {record['id']} references missing continuity objects"
        )
    return {
        "id": str(record["id"]),
        "canonical_key": record["canonical_key"],
        "status": cast(ContradictionStatus, record["status"]),
        "kind": cast(ContradictionKind, record["kind"]),
        "rationale": record["rationale"],
        "detection_payload": record["detection_payload"],
        "resolution_action": (
            None
            if record["resolution_action"] is None
            else cast("ContradictionResolutionAction", record["resolution_action"])
        ),
        "resolution_note": record["resolution_note"],
        "resolved_at": isoformat_or_none(record["resolved_at"]),
        "continuity_object_updated_at": record["continuity_object_updated_at"].isoformat(),
        "counterpart_object_updated_at": record["counterpart_object_updated_at"].isoformat(),
        "created_at": record["created_at"].isoformat(),
        "updated_at": record["updated_at"].isoformat(),
        "continuity_object": _serialize_review_object(continuity_object),
        "counterpart_object": _serialize_review_object(counterpart_object),
    }


def _source_event_count(row: ContinuityRecallCandidateRow) -> int:
    count = 0
    for payload in (row["body"], row["provenance"]):
        for key, value in _iter_items(payload):
            leaf_key = key.split(".")[-1]
            if leaf_key.endswith("_id") and isinstance(value, str):
                count += 1
            elif leaf_key.endswith("_ids") and isinstance(value, list):
                count += sum(1 for item in value if isinstance(item, str))
    return count


def _sync_trust_signals_for_object(
    store: ContinuityStore,
    *,
    row: ContinuityRecallCandidateRow,
    cases: list[ContradictionCaseRow],
) -> None:
    if not hasattr(store, "upsert_trust_signal"):
        return
    contradiction_cases = [
        case
        for case in cases
        if case["status"] == "open"
        and (case["continuity_object_id"] == row["id"] or case["counterpart_object_id"] == row["id"])
    ]
    contradiction_penalty = sum(
        _CONTRADICTION_PENALTY[cast(ContradictionKind, case["kind"])]
        for case in contradiction_cases
    )
    for case in cases:
        if case["continuity_object_id"] != row["id"] and case["counterpart_object_id"] != row["id"]:
            continue
        counterpart_object_id = (
            case["counterpart_object_id"]
            if case["continuity_object_id"] == row["id"]
            else case["continuity_object_id"]
        )
        is_open = case["status"] == "open"
        store.upsert_trust_signal(
            continuity_object_id=row["id"],
            signal_key=f"contradiction:{case['id']}:{row['id']}",
            signal_type="contradiction",
            signal_state="active" if is_open else "inactive",
            direction="negative" if is_open else "neutral",
            magnitude=min(1.0, _CONTRADICTION_PENALTY[cast(ContradictionKind, case["kind"])] / 2.0)
            if is_open
            else 0.0,
            reason=case["rationale"],
            contradiction_case_id=case["id"],
            related_continuity_object_id=counterpart_object_id,
            payload={
                "kind": case["kind"],
                "status": case["status"],
                "counterpart_object_id": str(counterpart_object_id),
                "canonical_key": case["canonical_key"],
            },
        )

    correction_count = len(
        store.list_continuity_correction_events(
            continuity_object_id=row["id"],
            limit=100,
        )
    )
    evidence_count = len(store.list_continuity_object_evidence(row["id"]))
    source_event_count = _source_event_count(row)

    store.upsert_trust_signal(
        continuity_object_id=row["id"],
        signal_key=f"correction:{row['id']}",
        signal_type="correction",
        signal_state="active" if correction_count > 0 else "inactive",
        direction="positive" if correction_count > 0 else "neutral",
        magnitude=min(1.0, 0.25 + (float(correction_count) * 0.15)) if correction_count > 0 else 0.0,
        reason="Correction history improves trust posture." if correction_count > 0 else "No correction history.",
        contradiction_case_id=None,
        related_continuity_object_id=None,
        payload={"correction_count": correction_count},
    )
    corroboration_strength = max(evidence_count, source_event_count)
    store.upsert_trust_signal(
        continuity_object_id=row["id"],
        signal_key=f"corroboration:{row['id']}",
        signal_type="corroboration",
        signal_state="active" if corroboration_strength > 1 else "inactive",
        direction="positive" if corroboration_strength > 1 else "neutral",
        magnitude=min(1.0, 0.2 + (float(corroboration_strength) * 0.1))
        if corroboration_strength > 1
        else 0.0,
        reason=(
            "Multiple evidence or source references corroborate this object."
            if corroboration_strength > 1
            else "Single-source corroboration only."
        ),
        contradiction_case_id=None,
        related_continuity_object_id=None,
        payload={
            "evidence_count": evidence_count,
            "source_event_count": source_event_count,
        },
    )
    weak_inference = evidence_count == 0 and source_event_count == 0 and contradiction_penalty == 0.0
    store.upsert_trust_signal(
        continuity_object_id=row["id"],
        signal_key=f"weak_inference:{row['id']}",
        signal_type="weak_inference",
        signal_state="active" if weak_inference else "inactive",
        direction="negative" if weak_inference else "neutral",
        magnitude=0.35 if weak_inference else 0.0,
        reason=(
            "Structured continuity state exists without corroborating evidence."
            if weak_inference
            else "Evidence posture is stronger than weak inference."
        ),
        contradiction_case_id=None,
        related_continuity_object_id=None,
        payload={
            "evidence_count": evidence_count,
            "source_event_count": source_event_count,
        },
    )


def contradiction_metrics_by_object(
    store: ContinuityStore,
    *,
    continuity_object_ids: list[UUID],
) -> dict[UUID, tuple[int, float]]:
    metrics: dict[UUID, tuple[int, float]] = {object_id: (0, 0.0) for object_id in continuity_object_ids}
    if not hasattr(store, "list_contradiction_cases_for_objects"):
        return metrics
    cases = store.list_contradiction_cases_for_objects(
        continuity_object_ids=continuity_object_ids,
        statuses=["open"],
    )
    counts: dict[UUID, int] = {object_id: 0 for object_id in continuity_object_ids}
    penalties: dict[UUID, float] = {object_id: 0.0 for object_id in continuity_object_ids}
    for case in cases:
        weight = _CONTRADICTION_PENALTY[cast(ContradictionKind, case["kind"])]
        for object_id in (case["continuity_object_id"], case["counterpart_object_id"]):
            if object_id not in counts:
                continue
            counts[object_id] += 1
            penalties[object_id] += weight
    for object_id in continuity_object_ids:
        metrics[object_id] = (counts.get(object_id, 0), penalties.get(object_id, 0.0))
    return metrics


def build_explanation_contradiction_summary(
    store: ContinuityStore,
    *,
    continuity_object_id: UUID,
) -> ContinuityExplanationContradictionRecord:
    if not hasattr(store, "list_contradiction_cases"):
        return {
            "open_case_count": 0,
            "resolved_case_count": 0,
            "open_case_ids": [],
            "kinds": [],
            "counterpart_object_ids": [],
            "penalty_score": 0.0,
        }
    cases = store.list_contradiction_cases(
        statuses=_STATUSES_ALL,
        limit=100,
        continuity_object_id=continuity_object_id,
    )
    open_cases = [case for case in cases if case["status"] == "open"]
    penalty_score = sum(
        _CONTRADICTION_PENALTY[cast(ContradictionKind, case["kind"])]
        for case in open_cases
    )
    return {
        "open_case_count": len(open_cases),
        "resolved_case_count": sum(1 for case in cases if case["status"] == "resolved"),
        "open_case_ids": [str(case["id"]) for case in open_cases],
        "kinds": sorted({cast(ContradictionKind, case["kind"]) for case in open_cases}),
        "counterpart_object_ids": sorted(
            {
                str(
                    case["counterpart_object_id"]
                    if case["continuity_object_id"] == continuity_object_id
                    else case["continuity_object_id"]
                )
                for case in open_cases
            }
        ),
        "penalty_score": penalty_score,
    }


def sync_contradiction_state_for_objects(
    store: ContinuityStore,
    *,
    continuity_object_ids: list[UUID] | None = None,
) -> _SyncOutcome:
    required_methods = (
        "list_continuity_recall_candidates",
        "list_contradiction_cases_for_objects",
        "list_contradiction_cases",
        "create_contradiction_case",
        "update_contradiction_case_optional",
        "list_continuity_correction_events",
        "list_continuity_object_evidence",
        "upsert_trust_signal",
    )
    if not all(hasattr(store, method_name) for method_name in required_methods):
        return _SyncOutcome(cases=[], scanned_object_count=0, open_case_count=0, resolved_case_count=0, updated_case_count=0)
    rows = [
        row
        for row in store.list_continuity_recall_candidates()
        if row["status"] != "deleted"
    ]
    live_rows = [row for row in rows if _is_live_contradiction_source(row)]
    row_by_id = {row["id"]: row for row in rows}
    target_ids = set(row_by_id) if continuity_object_ids is None else {object_id for object_id in continuity_object_ids if object_id in row_by_id}
    if not target_ids:
        return _SyncOutcome(cases=[], scanned_object_count=0, open_case_count=0, resolved_case_count=0, updated_case_count=0)

    detected_by_key: dict[str, _DetectedContradiction] = {}
    for index, left in enumerate(live_rows):
        for right in live_rows[index + 1 :]:
            if left["id"] not in target_ids and right["id"] not in target_ids:
                continue
            detected = _detect_pair(left, right)
            if detected is not None:
                detected_by_key[detected.canonical_key] = detected

    existing_cases = store.list_contradiction_cases_for_objects(
        continuity_object_ids=list(target_ids),
        statuses=_STATUSES_ALL,
    )
    existing_by_key = {case["canonical_key"]: case for case in existing_cases}
    touched_cases: dict[str, ContradictionCaseRow] = {}
    updated_case_count = 0

    for key, detected in detected_by_key.items():
        existing = existing_by_key.get(key)
        if existing is None:
            touched_cases[key] = store.create_contradiction_case(
                canonical_key=detected.canonical_key,
                continuity_object_id=detected.primary_object_id,
                counterpart_object_id=detected.counterpart_object_id,
                kind=detected.kind,
                status="open",
                rationale=detected.rationale,
                detection_payload=detected.payload,
                resolution_action=None,
                resolution_note=None,
                continuity_object_updated_at=detected.primary_object_updated_at,
                counterpart_object_updated_at=detected.counterpart_object_updated_at,
                resolved_at=None,
            )
            updated_case_count += 1
            continue

        preserve_resolution = (
            existing["status"] in {"resolved", "dismissed"}
            and existing["continuity_object_updated_at"] == detected.primary_object_updated_at
            and existing["counterpart_object_updated_at"] == detected.counterpart_object_updated_at
        )
        next_status = existing["status"] if preserve_resolution else "open"
        next_action = existing["resolution_action"] if preserve_resolution else None
        next_note = existing["resolution_note"] if preserve_resolution else None
        next_resolved_at = existing["resolved_at"] if preserve_resolution else None
        touched_cases[key] = cast(
            ContradictionCaseRow,
            store.update_contradiction_case_optional(
                contradiction_case_id=existing["id"],
                continuity_object_id=detected.primary_object_id,
                counterpart_object_id=detected.counterpart_object_id,
                kind=detected.kind,
                status=next_status,
                rationale=detected.rationale,
                detection_payload=detected.payload,
                resolution_action=next_action,
                resolution_note=next_note,
                continuity_object_updated_at=detected.primary_object_updated_at,
                counterpart_object_updated_at=detected.counterpart_object_updated_at,
                resolved_at=next_resolved_at,
            ),
        )
        if (
            existing["status"] != next_status
            or existing["rationale"] != detected.rationale
            or existing["detection_payload"] != detected.payload
            or existing["continuity_object_updated_at"] != detected.primary_object_updated_at
            or existing["counterpart_object_updated_at"] != detected.counterpart_object_updated_at
        ):
            updated_case_count += 1

    for key, existing in existing_by_key.items():
        if key in detected_by_key or existing["status"] != "open":
            continue
        resolved = store.update_contradiction_case_optional(
            contradiction_case_id=existing["id"],
            continuity_object_id=existing["continuity_object_id"],
            counterpart_object_id=existing["counterpart_object_id"],
            kind=existing["kind"],
            status="resolved",
            rationale=existing["rationale"],
            detection_payload=existing["detection_payload"],
            resolution_action="auto_resolved",
            resolution_note="No active contradiction remained in the latest sync.",
            continuity_object_updated_at=existing["continuity_object_updated_at"],
            counterpart_object_updated_at=existing["counterpart_object_updated_at"],
            resolved_at=_utcnow(),
        )
        if resolved is not None:
            touched_cases[key] = resolved
            updated_case_count += 1

    all_cases = store.list_contradiction_cases_for_objects(
        continuity_object_ids=list(target_ids),
        statuses=_STATUSES_ALL,
    )
    for object_id in target_ids:
        row = row_by_id[object_id]
        _sync_trust_signals_for_object(
            store,
            row=row,
            cases=all_cases,
        )

    cases = store.list_contradiction_cases(
        statuses=_STATUSES_ALL,
        limit=100,
        continuity_object_id=None,
    )
    scoped_cases = [
        case
        for case in cases
        if case["continuity_object_id"] in target_ids or case["counterpart_object_id"] in target_ids
    ]
    return _SyncOutcome(
        cases=scoped_cases,
        scanned_object_count=len(target_ids),
        open_case_count=sum(1 for case in scoped_cases if case["status"] == "open"),
        resolved_case_count=sum(1 for case in scoped_cases if case["status"] == "resolved"),
        updated_case_count=updated_case_count,
    )


def sync_contradictions(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContradictionSyncInput,
) -> ContradictionSyncResponse:
    del user_id
    outcome = sync_contradiction_state_for_objects(
        store,
        continuity_object_ids=(
            None if request.continuity_object_id is None else [request.continuity_object_id]
        ),
    )
    serialized = [_serialize_case(store, case) for case in outcome.cases[: request.limit]]
    summary: ContradictionSyncSummary = {
        "continuity_object_id": (
            None if request.continuity_object_id is None else str(request.continuity_object_id)
        ),
        "scanned_object_count": outcome.scanned_object_count,
        "open_case_count": outcome.open_case_count,
        "resolved_case_count": outcome.resolved_case_count,
        "updated_case_count": outcome.updated_case_count,
    }
    return {
        "items": serialized,
        "summary": summary,
    }


def list_contradiction_cases(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContradictionCaseListQueryInput,
) -> ContradictionCaseListResponse:
    del user_id
    validated_status = _validate_status(request.status)
    rows = store.list_contradiction_cases(
        statuses=[validated_status],
        limit=request.limit,
        continuity_object_id=request.continuity_object_id,
    )
    total_count = store.count_contradiction_cases(
        statuses=[validated_status],
        continuity_object_id=request.continuity_object_id,
    )
    summary: ContradictionCaseListSummary = {
        "status": validated_status,
        "limit": request.limit,
        "returned_count": len(rows),
        "total_count": total_count,
        "order": list(CONTRADICTION_CASE_LIST_ORDER),
    }
    return {
        "items": [_serialize_case(store, row) for row in rows],
        "summary": summary,
    }


def get_contradiction_case(
    store: ContinuityStore,
    *,
    user_id: UUID,
    contradiction_case_id: UUID,
) -> ContradictionCaseDetailResponse:
    del user_id
    return {
        "contradiction_case": _serialize_case(
            store,
            _case_or_raise(store, contradiction_case_id=contradiction_case_id),
        )
    }


def resolve_contradiction_case(
    store: ContinuityStore,
    *,
    user_id: UUID,
    contradiction_case_id: UUID,
    request: ContradictionResolveInput,
) -> ContradictionResolveResponse:
    del user_id
    if request.action not in {
        "confirm_primary",
        "confirm_counterpart",
        "mark_historical",
        "dismiss_false_positive",
        "auto_resolved",
    }:
        raise ContinuityContradictionValidationError("invalid contradiction resolution action")
    existing = _case_or_raise(store, contradiction_case_id=contradiction_case_id)
    resolved = store.update_contradiction_case_optional(
        contradiction_case_id=existing["id"],
        continuity_object_id=existing["continuity_object_id"],
        counterpart_object_id=existing["counterpart_object_id"],
        kind=existing["kind"],
        status="dismissed" if request.action == "dismiss_false_positive" else "resolved",
        rationale=existing["rationale"],
        detection_payload=existing["detection_payload"],
        resolution_action=request.action,
        resolution_note=request.note,
        continuity_object_updated_at=existing["continuity_object_updated_at"],
        counterpart_object_updated_at=existing["counterpart_object_updated_at"],
        resolved_at=_utcnow(),
    )
    if resolved is None:
        raise ContinuityContradictionNotFoundError(
            f"contradiction case {contradiction_case_id} was not found"
        )
    sync_contradiction_state_for_objects(
        store,
        continuity_object_ids=[
            resolved["continuity_object_id"],
            resolved["counterpart_object_id"],
        ],
    )
    refreshed = _case_or_raise(store, contradiction_case_id=contradiction_case_id)
    return {
        "contradiction_case": _serialize_case(store, refreshed),
    }


__all__ = [
    "ContinuityContradictionNotFoundError",
    "ContinuityContradictionValidationError",
    "build_explanation_contradiction_summary",
    "contradiction_metrics_by_object",
    "get_contradiction_case",
    "list_contradiction_cases",
    "resolve_contradiction_case",
    "sync_contradiction_state_for_objects",
    "sync_contradictions",
]
