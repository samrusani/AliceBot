from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from alicebot_api.contracts import (
    CONTINUITY_RECALL_LIST_ORDER,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MEMORY_CONFIRMATION_STATUSES,
    ContinuityRecallOrderingMetadata,
    ContinuityRecallProvenanceReference,
    ContinuityRecallQueryInput,
    ContinuityRecallResponse,
    ContinuityRecallResultRecord,
    ContinuityRecallScopeFilters,
    ContinuityRecallScopeKind,
    ContinuityRecallScopeMatch,
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
    posture_rank: int
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
_POSTURE_RANK: dict[str, int] = {
    "DERIVED": 2,
    "TRIAGE": 1,
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
        values = _collect_strings(
            source,
            keys={"confirmation_status", "memory_confirmation_status"},
        )
        for value in values:
            normalized = value.casefold()
            if normalized in MEMORY_CONFIRMATION_STATUSES:
                return cast(MemoryConfirmationStatus, normalized)

    return "unconfirmed"


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
        "posture_rank": item.posture_rank,
        "confidence": float(row["confidence"]),
    }

    return {
        "id": str(row["id"]),
        "capture_event_id": str(row["capture_event_id"]),
        "object_type": row["object_type"],  # type: ignore[typeddict-item]
        "status": row["status"],
        "title": row["title"],
        "body": row["body"],
        "provenance": row["provenance"],
        "confirmation_status": item.confirmation_status,
        "admission_posture": row["admission_posture"],  # type: ignore[typeddict-item]
        "confidence": float(row["confidence"]),
        "relevance": item.relevance,
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
        posture_rank = _POSTURE_RANK.get(row["admission_posture"], 0)
        relevance = (
            float(len(scope_matches)) * 100.0
            + float(query_term_match_count) * 10.0
            + float(confirmation_rank) * 5.0
            + float(posture_rank) * 2.0
            + float(row["confidence"])
        )

        ranked_candidates.append(
            RankedRecallCandidate(
                row=row,
                scope_matches=scope_matches,
                query_term_match_count=query_term_match_count,
                confirmation_status=confirmation_status,
                confirmation_rank=confirmation_rank,
                posture_rank=posture_rank,
                relevance=relevance,
            )
        )

    return sorted(
        ranked_candidates,
        key=lambda candidate: (
            len(candidate.scope_matches),
            candidate.query_term_match_count,
            candidate.confirmation_rank,
            candidate.posture_rank,
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
