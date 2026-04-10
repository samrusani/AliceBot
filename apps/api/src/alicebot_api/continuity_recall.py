from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from alicebot_api.continuity_objects import (
    default_continuity_searchable,
    serialize_continuity_lifecycle_state_from_record,
)
from alicebot_api.contracts import (
    CONTINUITY_RECALL_LIST_ORDER,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    ContinuityRecallFreshnessPosture,
    ContinuityRecallOrderingMetadata,
    ContinuityRecallProvenancePosture,
    ContinuityRecallProvenanceReference,
    ContinuityRecallQueryInput,
    ContinuityRecallResponse,
    ContinuityRecallResultRecord,
    ContinuityRecallScopeFilters,
    ContinuityRecallScopeKind,
    ContinuityRecallScopeMatch,
    ContinuityRecallSupersessionPosture,
    MemoryConfirmationStatus,
    isoformat_or_none,
)
from alicebot_api.store import ContinuityRecallCandidateRow, ContinuityStore, JsonObject


class ContinuityRecallValidationError(ValueError):
    """Raised when a continuity recall query is invalid."""


@dataclass(frozen=True, slots=True)
class RankedRecallCandidate:
    row: ContinuityRecallCandidateRow
    scope_matches: list[ContinuityRecallScopeMatch]
    query_term_match_count: int
    confirmation_status: MemoryConfirmationStatus
    confirmation_rank: int
    freshness_posture: ContinuityRecallFreshnessPosture
    freshness_rank: int
    provenance_posture: ContinuityRecallProvenancePosture
    provenance_rank: int
    supersession_posture: ContinuityRecallSupersessionPosture
    supersession_rank: int
    posture_rank: int
    lifecycle_rank: int
    relevance: float


_SCOPE_FILTER_KEYS: dict[ContinuityRecallScopeKind, set[str]] = {
    "thread": {"thread_id", "thread"},
    "task": {"task_id", "task"},
    "project": {"project", "project_id", "project_name"},
    "person": {"person", "person_id", "person_name", "owner", "assignee"},
}
_CONFIRMATION_RANK: dict[MemoryConfirmationStatus, int] = {
    "confirmed": 3,
    "unconfirmed": 2,
    "contested": 1,
}
_FRESHNESS_RANK: dict[ContinuityRecallFreshnessPosture, int] = {
    "fresh": 4,
    "aging": 3,
    "stale": 2,
    "superseded": 1,
    "unknown": 0,
}
_PROVENANCE_RANK: dict[ContinuityRecallProvenancePosture, int] = {
    "strong": 3,
    "partial": 2,
    "weak": 1,
    "missing": 0,
}
_SUPERSESSION_RANK: dict[ContinuityRecallSupersessionPosture, int] = {
    "current": 3,
    "historical": 2,
    "superseded": 1,
    "deleted": 0,
}
_POSTURE_RANK: dict[str, int] = {
    "DERIVED": 2,
    "TRIAGE": 1,
}
_LIFECYCLE_RANK: dict[str, int] = {
    "active": 4,
    "stale": 3,
    "completed": 2,
    "cancelled": 2,
    "superseded": 1,
    "deleted": 0,
}


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_uuid_string(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _collect_strings(payload: object, *, keys: set[str]) -> set[str]:
    values: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = key.strip().casefold()
                if normalized_key in keys:
                    if isinstance(child, str):
                        normalized = _normalize_optional_text(child)
                        if normalized is not None:
                            values.add(normalized)
                    elif isinstance(child, list):
                        for item in child:
                            if isinstance(item, str):
                                normalized = _normalize_optional_text(item)
                                if normalized is not None:
                                    values.add(normalized)
                visit(child)
            return

        if isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return values


def _collect_strings_in_order(payload: object, *, keys: set[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()

    def add_value(value: str) -> None:
        normalized = _normalize_optional_text(value)
        if normalized is None:
            return
        if normalized in seen:
            return
        seen.add(normalized)
        values.append(normalized)

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = key.strip().casefold()
                if normalized_key in keys:
                    if isinstance(child, str):
                        add_value(child)
                    elif isinstance(child, list):
                        for item in child:
                            if isinstance(item, str):
                                add_value(item)
                visit(child)
            return

        if isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return values


def _select_ranked_value(values: list[str], *, rank_map: dict[str, int]) -> str | None:
    candidates = {
        value.casefold()
        for value in values
        if value.casefold() in rank_map
    }
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda candidate: (rank_map[candidate], candidate),
    )


def _flatten_text(payload: object) -> str:
    values: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, str):
            normalized = _normalize_optional_text(value)
            if normalized is not None:
                values.append(normalized)
            return

        if isinstance(value, dict):
            for child in value.values():
                visit(child)
            return

        if isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return " ".join(values)


def _extract_confirmation_status(row: ContinuityRecallCandidateRow) -> MemoryConfirmationStatus:
    for source in (row["provenance"], row["body"]):
        values = _collect_strings_in_order(
            source,
            keys={"confirmation_status", "memory_confirmation_status"},
        )
        ranked_value = _select_ranked_value(values, rank_map=_CONFIRMATION_RANK)
        if ranked_value is not None:
            return cast(MemoryConfirmationStatus, ranked_value)

    if row["last_confirmed_at"] is not None:
        return "confirmed"

    return "unconfirmed"


def _extract_freshness_posture(
    row: ContinuityRecallCandidateRow,
    *,
    confirmation_status: MemoryConfirmationStatus,
) -> ContinuityRecallFreshnessPosture:
    for source in (row["provenance"], row["body"]):
        explicit_values = _collect_strings_in_order(
            source,
            keys={"freshness_posture", "freshness_status"},
        )
        ranked_value = _select_ranked_value(explicit_values, rank_map=_FRESHNESS_RANK)
        if ranked_value is not None:
            return cast(ContinuityRecallFreshnessPosture, ranked_value)

    if row["status"] == "superseded" or row["superseded_by_object_id"] is not None:
        return "superseded"
    if row["status"] == "stale":
        return "stale"
    if confirmation_status == "confirmed" or row["last_confirmed_at"] is not None:
        return "fresh"
    if row["status"] in {"active", "completed", "cancelled"}:
        return "aging"
    return "unknown"


def _extract_supersession_posture(
    row: ContinuityRecallCandidateRow,
) -> ContinuityRecallSupersessionPosture:
    if row["status"] == "deleted":
        return "deleted"
    if row["status"] == "superseded" or row["superseded_by_object_id"] is not None:
        return "superseded"
    if row["status"] == "stale":
        return "historical"
    return "current"


def _extract_provenance_posture(
    row: ContinuityRecallCandidateRow,
    *,
    scope_matches: list[ContinuityRecallScopeMatch],
) -> ContinuityRecallProvenancePosture:
    has_source_events = bool(
        _collect_strings(
            row["provenance"],
            keys={"source_event_id", "source_event_ids"},
        )
        | _collect_strings(
            row["body"],
            keys={"source_event_id", "source_event_ids"},
        )
    )
    has_scope_context = len(scope_matches) > 0 or bool(
        _collect_strings(
            row["provenance"],
            keys=(
                _SCOPE_FILTER_KEYS["thread"]
                | _SCOPE_FILTER_KEYS["task"]
                | _SCOPE_FILTER_KEYS["project"]
                | _SCOPE_FILTER_KEYS["person"]
            ),
        )
    )
    if has_source_events and has_scope_context:
        return "strong"
    if has_source_events or has_scope_context:
        return "partial"
    if row["provenance"]:
        return "weak"
    return "missing"


def _compute_scope_matches(
    row: ContinuityRecallCandidateRow,
    *,
    thread_filter: str | None,
    task_filter: str | None,
    project_filter: str | None,
    person_filter: str | None,
) -> list[ContinuityRecallScopeMatch]:
    scope_matches: list[ContinuityRecallScopeMatch] = []

    if thread_filter is not None:
        candidate_values = {
            value.casefold()
            for value in _collect_strings(
                row["provenance"],
                keys=_SCOPE_FILTER_KEYS["thread"],
            )
            | _collect_strings(
                row["body"],
                keys=_SCOPE_FILTER_KEYS["thread"],
            )
        }
        if thread_filter in candidate_values:
            scope_matches.append({"kind": "thread", "value": thread_filter})

    if task_filter is not None:
        candidate_values = {
            value.casefold()
            for value in _collect_strings(
                row["provenance"],
                keys=_SCOPE_FILTER_KEYS["task"],
            )
            | _collect_strings(
                row["body"],
                keys=_SCOPE_FILTER_KEYS["task"],
            )
        }
        if task_filter in candidate_values:
            scope_matches.append({"kind": "task", "value": task_filter})

    if project_filter is not None:
        candidate_values = {
            value.casefold()
            for value in _collect_strings(
                row["provenance"],
                keys=_SCOPE_FILTER_KEYS["project"],
            )
            | _collect_strings(
                row["body"],
                keys=_SCOPE_FILTER_KEYS["project"],
            )
        }
        if project_filter in candidate_values:
            scope_matches.append({"kind": "project", "value": project_filter})

    if person_filter is not None:
        candidate_values = {
            value.casefold()
            for value in _collect_strings(
                row["provenance"],
                keys=_SCOPE_FILTER_KEYS["person"],
            )
            | _collect_strings(
                row["body"],
                keys=_SCOPE_FILTER_KEYS["person"],
            )
        }
        if person_filter in candidate_values:
            scope_matches.append({"kind": "person", "value": person_filter})

    return scope_matches


def _query_terms(query: str | None) -> list[str]:
    if query is None:
        return []
    return [
        term
        for term in re.findall(r"[a-z0-9]+", query.casefold())
        if term
    ]


def _count_query_term_matches(row: ContinuityRecallCandidateRow, terms: list[str]) -> int:
    if not terms:
        return 0

    text = " ".join(
        [
            row["title"],
            _flatten_text(row["body"]),
            _flatten_text(row["provenance"]),
        ]
    ).casefold()
    return sum(1 for term in terms if term in text)


def _matches_time_window(
    row: ContinuityRecallCandidateRow,
    *,
    since: datetime | None,
    until: datetime | None,
) -> bool:
    created_at = row["object_created_at"]
    if since is not None and created_at < since:
        return False
    if until is not None and created_at > until:
        return False
    return True


def _provenance_reference_kind(key: str) -> str:
    if key.endswith("_id"):
        return key[: -len("_id")]
    if key.endswith("_ids"):
        return key[: -len("_ids")]
    return key


def _build_provenance_references(
    capture_event_id: UUID,
    provenance: JsonObject,
) -> list[ContinuityRecallProvenanceReference]:
    references: set[tuple[str, str]] = {
        ("continuity_capture_event", str(capture_event_id)),
    }

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = key.strip().casefold()
                if normalized_key.endswith("_id"):
                    if isinstance(child, (str, UUID)):
                        references.add((_provenance_reference_kind(normalized_key), str(child)))
                elif normalized_key.endswith("_ids") and isinstance(child, list):
                    for item in child:
                        if isinstance(item, (str, UUID)):
                            references.add((_provenance_reference_kind(normalized_key), str(item)))
                visit(child)
            return

        if isinstance(value, list):
            for child in value:
                visit(child)

    visit(provenance)

    return [
        {"source_kind": source_kind, "source_id": source_id}
        for source_kind, source_id in sorted(references)
    ]


def _serialize_recall_result(item: RankedRecallCandidate) -> ContinuityRecallResultRecord:
    row = item.row

    ordering: ContinuityRecallOrderingMetadata = {
        "scope_match_count": len(item.scope_matches),
        "query_term_match_count": item.query_term_match_count,
        "confirmation_rank": item.confirmation_rank,
        "freshness_posture": item.freshness_posture,
        "freshness_rank": item.freshness_rank,
        "provenance_posture": item.provenance_posture,
        "provenance_rank": item.provenance_rank,
        "supersession_posture": item.supersession_posture,
        "supersession_rank": item.supersession_rank,
        "posture_rank": item.posture_rank,
        "lifecycle_rank": item.lifecycle_rank,
        "confidence": float(row["confidence"]),
    }

    return {
        "id": str(row["id"]),
        "capture_event_id": str(row["capture_event_id"]),
        "object_type": row["object_type"],  # type: ignore[typeddict-item]
        "status": row["status"],
        "lifecycle": serialize_continuity_lifecycle_state_from_record(row),
        "title": row["title"],
        "body": row["body"],
        "provenance": row["provenance"],
        "confirmation_status": item.confirmation_status,
        "admission_posture": row["admission_posture"],  # type: ignore[typeddict-item]
        "confidence": float(row["confidence"]),
        "relevance": item.relevance,
        "last_confirmed_at": isoformat_or_none(row["last_confirmed_at"]),
        "supersedes_object_id": (
            None if row["supersedes_object_id"] is None else str(row["supersedes_object_id"])
        ),
        "superseded_by_object_id": (
            None if row["superseded_by_object_id"] is None else str(row["superseded_by_object_id"])
        ),
        "scope_matches": item.scope_matches,
        "provenance_references": _build_provenance_references(
            row["capture_event_id"],
            row["provenance"],
        ),
        "ordering": ordering,
        "created_at": row["object_created_at"].isoformat(),
        "updated_at": row["object_updated_at"].isoformat(),
    }


def _scope_filters_payload(request: ContinuityRecallQueryInput) -> ContinuityRecallScopeFilters:
    payload: ContinuityRecallScopeFilters = {
        "since": isoformat_or_none(request.since),
        "until": isoformat_or_none(request.until),
    }
    if request.thread_id is not None:
        payload["thread_id"] = str(request.thread_id)
    if request.task_id is not None:
        payload["task_id"] = str(request.task_id)
    if request.project is not None:
        payload["project"] = request.project
    if request.person is not None:
        payload["person"] = request.person
    return payload


def _validate_request(request: ContinuityRecallQueryInput) -> None:
    if request.limit < 1 or request.limit > MAX_CONTINUITY_RECALL_LIMIT:
        raise ContinuityRecallValidationError(
            f"limit must be between 1 and {MAX_CONTINUITY_RECALL_LIMIT}"
        )

    if request.since is not None and request.until is not None and request.until < request.since:
        raise ContinuityRecallValidationError("until must be greater than or equal to since")


def _ordered_recall_candidates(
    store: ContinuityStore,
    *,
    request: ContinuityRecallQueryInput,
) -> list[RankedRecallCandidate]:
    thread_filter = _normalize_uuid_string(request.thread_id)
    task_filter = _normalize_uuid_string(request.task_id)
    project_filter = (
        request.project.casefold()
        if request.project is not None
        else None
    )
    person_filter = (
        request.person.casefold()
        if request.person is not None
        else None
    )
    query_terms = _query_terms(request.query)

    ranked_candidates: list[RankedRecallCandidate] = []

    for row in store.list_continuity_recall_candidates():
        if row["status"] == "deleted":
            continue
        if not bool(row.get("is_searchable", default_continuity_searchable(row["object_type"]))):
            continue

        if not _matches_time_window(
            row,
            since=request.since,
            until=request.until,
        ):
            continue

        scope_matches = _compute_scope_matches(
            row,
            thread_filter=thread_filter,
            task_filter=task_filter,
            project_filter=project_filter,
            person_filter=person_filter,
        )

        required_scope_count = sum(
            value is not None
            for value in (thread_filter, task_filter, project_filter, person_filter)
        )
        if len(scope_matches) != required_scope_count:
            continue

        query_term_match_count = _count_query_term_matches(row, query_terms)
        if query_terms and query_term_match_count == 0:
            continue

        confirmation_status = _extract_confirmation_status(row)
        confirmation_rank = _CONFIRMATION_RANK[confirmation_status]
        freshness_posture = _extract_freshness_posture(
            row,
            confirmation_status=confirmation_status,
        )
        freshness_rank = _FRESHNESS_RANK[freshness_posture]
        provenance_posture = _extract_provenance_posture(
            row,
            scope_matches=scope_matches,
        )
        provenance_rank = _PROVENANCE_RANK[provenance_posture]
        supersession_posture = _extract_supersession_posture(row)
        supersession_rank = _SUPERSESSION_RANK[supersession_posture]
        posture_rank = _POSTURE_RANK.get(row["admission_posture"], 0)
        lifecycle_rank = _LIFECYCLE_RANK.get(row["status"], 0)
        relevance = (
            float(len(scope_matches)) * 100.0
            + float(query_term_match_count) * 20.0
            + float(confirmation_rank) * 14.0
            + float(freshness_rank) * 12.0
            + float(provenance_rank) * 8.0
            + float(supersession_rank) * 10.0
            + float(posture_rank) * 4.0
            + float(lifecycle_rank) * 2.0
            + float(row["confidence"])
        )

        ranked_candidates.append(
            RankedRecallCandidate(
                row=row,
                scope_matches=scope_matches,
                query_term_match_count=query_term_match_count,
                confirmation_status=confirmation_status,
                confirmation_rank=confirmation_rank,
                freshness_posture=freshness_posture,
                freshness_rank=freshness_rank,
                provenance_posture=provenance_posture,
                provenance_rank=provenance_rank,
                supersession_posture=supersession_posture,
                supersession_rank=supersession_rank,
                posture_rank=posture_rank,
                lifecycle_rank=lifecycle_rank,
                relevance=relevance,
            )
        )

    return sorted(
        ranked_candidates,
        key=lambda candidate: (
            len(candidate.scope_matches),
            candidate.query_term_match_count,
            candidate.confirmation_rank,
            candidate.freshness_rank,
            candidate.provenance_rank,
            candidate.supersession_rank,
            candidate.posture_rank,
            candidate.lifecycle_rank,
            float(candidate.row["confidence"]),
            candidate.row["object_created_at"],
            str(candidate.row["id"]),
        ),
        reverse=True,
    )


def query_continuity_recall(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContinuityRecallQueryInput,
    apply_limit: bool = True,
) -> ContinuityRecallResponse:
    del user_id

    normalized_query = _normalize_optional_text(request.query)
    normalized_project = _normalize_optional_text(request.project)
    normalized_person = _normalize_optional_text(request.person)
    normalized_request = ContinuityRecallQueryInput(
        query=normalized_query,
        thread_id=request.thread_id,
        task_id=request.task_id,
        project=normalized_project,
        person=normalized_person,
        since=request.since,
        until=request.until,
        limit=request.limit,
    )

    _validate_request(normalized_request)

    ordered_candidates = _ordered_recall_candidates(
        store,
        request=normalized_request,
    )

    if apply_limit:
        returned_candidates = ordered_candidates[: normalized_request.limit]
    else:
        returned_candidates = ordered_candidates
    items = [_serialize_recall_result(item) for item in returned_candidates]

    return {
        "items": items,
        "summary": {
            "query": normalized_request.query,
            "filters": _scope_filters_payload(normalized_request),
            "limit": normalized_request.limit,
            "returned_count": len(items),
            "total_count": len(ordered_candidates),
            "order": list(CONTINUITY_RECALL_LIST_ORDER),
        },
    }


def build_default_recall_query_input() -> ContinuityRecallQueryInput:
    return ContinuityRecallQueryInput(limit=DEFAULT_CONTINUITY_RECALL_LIMIT)
