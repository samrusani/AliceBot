from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from uuid import UUID

from alicebot_api.config import get_settings
from alicebot_api.continuity_objects import (
    default_continuity_searchable,
    serialize_continuity_lifecycle_state_from_record,
)
from alicebot_api.continuity_explainability import build_continuity_item_explanation
from alicebot_api.contracts import (
    CONTINUITY_RECALL_LIST_ORDER,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_RETRIEVAL_RUN_LIST_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_RETRIEVAL_RUN_LIST_LIMIT,
    ContinuityRecallFreshnessPosture,
    ContinuityRetrievalDebugCandidateRecord,
    ContinuityRetrievalDebugRecord,
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
    RetrievalRunListResponse,
    RetrievalRunListSummary,
    RetrievalRunRecord,
    RetrievalTraceResponse,
    RetrievalTraceSummary,
    RETRIEVAL_RUN_LIST_ORDER,
    RETRIEVAL_TRACE_CANDIDATE_ORDER,
    MemoryConfirmationStatus,
    MemoryTrustClass,
    isoformat_or_none,
)
from alicebot_api.store import (
    ContinuityRecallCandidateRow,
    ContinuityStore,
    EntityEdgeRow,
    EntityRow,
    JsonObject,
    RetrievalCandidateRow,
    RetrievalRunRow,
)


class ContinuityRecallValidationError(ValueError):
    """Raised when a continuity recall query is invalid."""


class RetrievalTraceNotFoundError(LookupError):
    """Raised when a persisted retrieval trace is not visible in the current scope."""


@dataclass(frozen=True, slots=True)
class RankedRecallCandidate:
    row: ContinuityRecallCandidateRow
    scope_matches: list[ContinuityRecallScopeMatch]
    query_term_match_count: int
    semantic_similarity_score: float
    exact_match_score: float
    recency_score: float
    temporal_overlap_score: float
    entity_match_count: int
    confirmation_status: MemoryConfirmationStatus
    confirmation_rank: int
    trust_class: MemoryTrustClass
    trust_rank: int
    freshness_posture: ContinuityRecallFreshnessPosture
    freshness_rank: int
    provenance_posture: ContinuityRecallProvenancePosture
    provenance_rank: int
    supersession_posture: ContinuityRecallSupersessionPosture
    supersession_rank: int
    supersession_freshness_score: float
    posture_rank: int
    lifecycle_rank: int
    relevance: float


@dataclass(frozen=True, slots=True)
class EntityRetrievalContext:
    anchor_names: tuple[str, ...]
    expansion_names: tuple[str, ...]
    expansion_weights: dict[str, float]


@dataclass(frozen=True, slots=True)
class CandidateStageScores:
    lexical_raw: float
    lexical_normalized: float
    semantic_raw: float
    semantic_normalized: float
    entity_edge_raw: float
    entity_edge_normalized: float
    temporal_raw: float
    temporal_normalized: float
    trust_raw: float
    trust_normalized: float


@dataclass(frozen=True, slots=True)
class CandidateScoringState:
    row: ContinuityRecallCandidateRow
    scope_matches: list[ContinuityRecallScopeMatch]
    scope_matched: bool
    query_term_match_count: int
    semantic_similarity_score: float
    exact_match_score: float
    recency_score: float
    temporal_overlap_score: float
    entity_match_count: int
    lexical_raw_score: float
    semantic_raw_score: float
    entity_edge_raw_score: float
    temporal_raw_score: float
    trust_raw_score: float
    confirmation_status: MemoryConfirmationStatus
    confirmation_rank: int
    trust_class: MemoryTrustClass
    trust_rank: int
    freshness_posture: ContinuityRecallFreshnessPosture
    freshness_rank: int
    provenance_posture: ContinuityRecallProvenancePosture
    provenance_rank: int
    supersession_posture: ContinuityRecallSupersessionPosture
    supersession_rank: int
    supersession_freshness_score: float
    posture_rank: int
    lifecycle_rank: int


@dataclass(frozen=True, slots=True)
class RetrievalTraceCandidate:
    ranked: RankedRecallCandidate
    rank: int | None
    selected: bool
    exclusion_reason: str | None
    stage_scores: CandidateStageScores
    stage_reasons: dict[str, str]


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
_TRUST_CLASS_RANK: dict[MemoryTrustClass, int] = {
    "human_curated": 4,
    "deterministic": 3,
    "llm_corroborated": 2,
    "llm_single_source": 1,
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
_ENTITY_KEYS = (
    _SCOPE_FILTER_KEYS["project"]
    | _SCOPE_FILTER_KEYS["person"]
    | _SCOPE_FILTER_KEYS["thread"]
    | _SCOPE_FILTER_KEYS["task"]
)
_TRUST_CLASS_KEYS = {"trust_class", "memory_trust_class"}
_SEMANTIC_MATCH_THRESHOLD = 0.02
_MAX_QUERY_TERM_COUNT = 64
_MAX_SIMILARITY_QUERY_CHARS = 512
_MAX_SIMILARITY_QUERY_TOKEN_COUNT = 64
_MAX_SIMILARITY_CANDIDATE_TEXT_CHARS = 16_384
_MAX_SIMILARITY_TOKEN_COUNT = 512
_MAX_SIMILARITY_TRIGRAM_COUNT = 4096
_RECENCY_HALF_LIFE_HOURS = 24.0


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
        for term in re.findall(r"[a-z0-9]+", query.casefold()[:_MAX_SIMILARITY_QUERY_CHARS])
        if term
    ][: _MAX_QUERY_TERM_COUNT]


def _count_query_term_matches(*, candidate_text_casefold: str, terms: list[str]) -> int:
    if not terms:
        return 0
    return sum(1 for term in terms if term in candidate_text_casefold)


def _candidate_text(row: ContinuityRecallCandidateRow) -> str:
    text = " ".join(
        [
            row["title"],
            _flatten_text(row["body"]),
            _flatten_text(row["provenance"]),
        ]
    )
    return text[:_MAX_SIMILARITY_CANDIDATE_TEXT_CHARS]


def _tokenize(
    value: str,
    *,
    max_chars: int,
    max_tokens: int,
) -> list[str]:
    tokens = [token for token in re.findall(r"[a-z0-9]+", value.casefold()[:max_chars]) if token]
    if len(tokens) > max_tokens:
        return tokens[:max_tokens]
    return tokens


def _trigrams(value: str, *, max_chars: int, max_ngrams: int) -> set[str]:
    compact = re.sub(r"\s+", " ", value.casefold()[:max_chars]).strip()
    if len(compact) < 3:
        return {compact} if compact else set()
    ngram_count = min(len(compact) - 2, max_ngrams)
    return {compact[index : index + 3] for index in range(ngram_count)}


@dataclass(frozen=True, slots=True)
class SimilarityQueryFeatures:
    normalized_query: str | None
    tokens: set[str]
    trigrams: set[str]


def _build_similarity_query_features(query: str | None) -> SimilarityQueryFeatures:
    normalized_query = _normalize_optional_text(query)
    if normalized_query is None:
        return SimilarityQueryFeatures(
            normalized_query=None,
            tokens=set(),
            trigrams=set(),
        )
    tokens = set(
        _tokenize(
            normalized_query,
            max_chars=_MAX_SIMILARITY_QUERY_CHARS,
            max_tokens=_MAX_SIMILARITY_QUERY_TOKEN_COUNT,
        )
    )
    trigrams = _trigrams(
        normalized_query,
        max_chars=_MAX_SIMILARITY_QUERY_CHARS,
        max_ngrams=_MAX_SIMILARITY_TRIGRAM_COUNT,
    )
    return SimilarityQueryFeatures(
        normalized_query=normalized_query,
        tokens=tokens,
        trigrams=trigrams,
    )


def _semantic_similarity_score(
    *,
    query_features: SimilarityQueryFeatures,
    candidate_text: str,
) -> float:
    if not query_features.tokens:
        return 0.0

    candidate_tokens = set(
        _tokenize(
            candidate_text,
            max_chars=_MAX_SIMILARITY_CANDIDATE_TEXT_CHARS,
            max_tokens=_MAX_SIMILARITY_TOKEN_COUNT,
        )
    )

    token_overlap = (
        len(query_features.tokens & candidate_tokens) / len(query_features.tokens)
        if query_features.tokens
        else 0.0
    )

    candidate_ngrams = _trigrams(
        candidate_text,
        max_chars=_MAX_SIMILARITY_CANDIDATE_TEXT_CHARS,
        max_ngrams=_MAX_SIMILARITY_TRIGRAM_COUNT,
    )
    trigram_overlap = (
        len(query_features.trigrams & candidate_ngrams) / len(query_features.trigrams | candidate_ngrams)
        if query_features.trigrams and candidate_ngrams
        else 0.0
    )

    # Blend term-level overlap and a light character-level similarity proxy.
    return (token_overlap * 0.75) + (trigram_overlap * 0.25)


def _exact_match_score(
    *,
    query_features: SimilarityQueryFeatures,
    candidate_text_casefold: str,
    title: str,
) -> float:
    if query_features.normalized_query is None:
        return 0.0

    query_casefold = query_features.normalized_query.casefold()
    title_casefold = title.casefold()

    if query_casefold in title_casefold:
        return 1.0
    if query_casefold in candidate_text_casefold:
        return 0.8

    terms = query_features.tokens
    if not terms:
        return 0.0
    title_hits = sum(1 for term in terms if term in title_casefold)
    text_hits = sum(1 for term in terms if term in candidate_text_casefold)
    if title_hits == len(terms):
        return 0.7
    if text_hits == len(terms):
        return 0.5
    if text_hits > 0:
        return 0.25 * (text_hits / len(terms))
    return 0.0


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _collect_datetimes(payload: object, *, keys: set[str]) -> list[datetime]:
    values: list[datetime] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.strip().casefold() in keys:
                    if isinstance(child, list):
                        for list_item in child:
                            parsed = _coerce_datetime(list_item)
                            if parsed is not None:
                                values.append(parsed)
                    else:
                        parsed = _coerce_datetime(child)
                        if parsed is not None:
                            values.append(parsed)
                visit(child)
            return
        if isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return values


def _temporal_bounds(row: ContinuityRecallCandidateRow) -> tuple[datetime, datetime]:
    start_candidates = (
        _collect_datetimes(row["provenance"], keys=_TEMPORAL_START_KEYS)
        + _collect_datetimes(row["body"], keys=_TEMPORAL_START_KEYS)
    )
    end_candidates = (
        _collect_datetimes(row["provenance"], keys=_TEMPORAL_END_KEYS)
        + _collect_datetimes(row["body"], keys=_TEMPORAL_END_KEYS)
    )

    start = min(start_candidates) if start_candidates else row["object_created_at"]
    end = max(end_candidates) if end_candidates else row["object_updated_at"]
    if end < start:
        end = start
    return start, end


def _temporal_overlap_score(
    row: ContinuityRecallCandidateRow,
    *,
    since: datetime | None,
    until: datetime | None,
) -> float:
    candidate_start, candidate_end = _temporal_bounds(row)

    if since is None and until is None:
        return 1.0

    window_start = candidate_start if since is None else since
    window_end = candidate_end if until is None else until
    if window_end < window_start:
        return 0.0

    overlap_start = max(candidate_start, window_start)
    overlap_end = min(candidate_end, window_end)
    if overlap_end < overlap_start:
        return 0.0

    overlap_seconds = (overlap_end - overlap_start).total_seconds()
    window_seconds = max((window_end - window_start).total_seconds(), 1.0)
    return max(0.0, min(1.0, overlap_seconds / window_seconds))


def _extract_trust_class(
    row: ContinuityRecallCandidateRow,
    *,
    confirmation_status: MemoryConfirmationStatus,
    provenance_posture: ContinuityRecallProvenancePosture,
) -> MemoryTrustClass:
    explicit_values = _collect_strings_in_order(
        row["provenance"],
        keys=_TRUST_CLASS_KEYS,
    ) + _collect_strings_in_order(
        row["body"],
        keys=_TRUST_CLASS_KEYS,
    )
    for value in explicit_values:
        normalized = value.casefold()
        if normalized in _TRUST_CLASS_RANK:
            return cast(MemoryTrustClass, normalized)

    if confirmation_status == "confirmed":
        return "human_curated"
    if provenance_posture == "strong":
        return "llm_corroborated"
    if provenance_posture == "partial":
        return "llm_single_source"
    return "deterministic"


def _entity_query_terms(request: ContinuityRecallQueryInput) -> list[str]:
    values: list[str] = []
    if request.project is not None:
        values.extend(
            _tokenize(
                request.project,
                max_chars=_MAX_SIMILARITY_QUERY_CHARS,
                max_tokens=_MAX_SIMILARITY_QUERY_TOKEN_COUNT,
            )
        )
    if request.person is not None:
        values.extend(
            _tokenize(
                request.person,
                max_chars=_MAX_SIMILARITY_QUERY_CHARS,
                max_tokens=_MAX_SIMILARITY_QUERY_TOKEN_COUNT,
            )
        )
    if request.query is not None:
        values.extend(
            term
            for term in _tokenize(
                request.query,
                max_chars=_MAX_SIMILARITY_QUERY_CHARS,
                max_tokens=_MAX_SIMILARITY_QUERY_TOKEN_COUNT,
            )
            if len(term) >= 4
        )

    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _entity_match_count(row: ContinuityRecallCandidateRow, *, entity_terms: list[str]) -> int:
    if not entity_terms:
        return 0
    entity_values = _collect_strings(row["provenance"], keys=_ENTITY_KEYS) | _collect_strings(
        row["body"],
        keys=_ENTITY_KEYS,
    )
    if not entity_values:
        return 0
    normalized_values = " ".join(sorted(entity_values)).casefold()
    return sum(1 for term in entity_terms if term in normalized_values)


def _list_entities(store: ContinuityStore) -> list[EntityRow]:
    list_entities = getattr(store, "list_entities", None)
    if not callable(list_entities):
        return []
    entities = list_entities()
    return entities if isinstance(entities, list) else []


def _list_entity_edges_for_entities(
    store: ContinuityStore,
    entity_ids: list[UUID],
) -> list[EntityEdgeRow]:
    list_edges = getattr(store, "list_entity_edges_for_entities", None)
    if callable(list_edges):
        edges = list_edges(entity_ids)
        if isinstance(edges, list):
            return edges

    list_edge_for_entity = getattr(store, "list_entity_edges_for_entity", None)
    if not callable(list_edge_for_entity):
        return []

    rows: list[EntityEdgeRow] = []
    seen: set[UUID] = set()
    for entity_id in entity_ids:
        edges = list_edge_for_entity(entity_id)
        if not isinstance(edges, list):
            continue
        for edge in edges:
            edge_id = edge.get("id")
            if isinstance(edge_id, UUID):
                if edge_id in seen:
                    continue
                seen.add(edge_id)
            rows.append(edge)
    return rows


def _resolve_entity_retrieval_context(
    store: ContinuityStore,
    *,
    request: ContinuityRecallQueryInput,
) -> EntityRetrievalContext:
    entities = _list_entities(store)
    if not entities:
        return EntityRetrievalContext(
            anchor_names=tuple(),
            expansion_names=tuple(),
            expansion_weights={},
        )

    name_by_id: dict[UUID, str] = {
        entity["id"]: entity["name"]
        for entity in entities
        if entity.get("name")
    }
    query_tokens = set(_entity_query_terms(request))
    explicit_names = {
        value.casefold()
        for value in (request.project, request.person)
        if value is not None
    }

    anchor_entities: list[EntityRow] = []
    for entity in entities:
        entity_name = entity["name"].strip()
        if not entity_name:
            continue
        entity_name_casefold = entity_name.casefold()
        entity_tokens = set(
            _tokenize(
                entity_name,
                max_chars=_MAX_SIMILARITY_QUERY_CHARS,
                max_tokens=_MAX_SIMILARITY_QUERY_TOKEN_COUNT,
            )
        )
        if entity_name_casefold in explicit_names:
            anchor_entities.append(entity)
            continue
        if query_tokens and query_tokens & entity_tokens:
            anchor_entities.append(entity)

    if not anchor_entities:
        return EntityRetrievalContext(
            anchor_names=tuple(),
            expansion_names=tuple(),
            expansion_weights={},
        )

    anchor_ids = [entity["id"] for entity in anchor_entities]
    anchor_names = tuple(
        sorted({entity["name"].casefold() for entity in anchor_entities if entity["name"].strip()})
    )
    expansion_weights: dict[str, float] = {
        name: 0.5
        for name in anchor_names
    }

    for edge in _list_entity_edges_for_entities(store, anchor_ids):
        from_name = name_by_id.get(edge["from_entity_id"])
        to_name = name_by_id.get(edge["to_entity_id"])
        if from_name is not None and edge["from_entity_id"] not in anchor_ids:
            expansion_weights.setdefault(from_name.casefold(), 1.25)
        if to_name is not None and edge["to_entity_id"] not in anchor_ids:
            expansion_weights.setdefault(to_name.casefold(), 1.25)

    expansion_names = tuple(sorted(expansion_weights))
    return EntityRetrievalContext(
        anchor_names=anchor_names,
        expansion_names=expansion_names,
        expansion_weights=expansion_weights,
    )


def _entity_edge_raw_score(
    row: ContinuityRecallCandidateRow,
    *,
    entity_context: EntityRetrievalContext,
) -> float:
    if not entity_context.expansion_weights:
        return 0.0
    entity_values = _collect_strings(row["provenance"], keys=_ENTITY_KEYS) | _collect_strings(
        row["body"],
        keys=_ENTITY_KEYS,
    )
    if not entity_values:
        return 0.0
    normalized_values = " ".join(sorted(entity_values)).casefold()
    score = 0.0
    for entity_name, weight in entity_context.expansion_weights.items():
        if entity_name in normalized_values:
            score += weight
    return score


def _token_frequency(value: str, *, max_chars: int, max_tokens: int) -> dict[str, int]:
    frequencies: dict[str, int] = {}
    for token in _tokenize(value, max_chars=max_chars, max_tokens=max_tokens):
        frequencies[token] = frequencies.get(token, 0) + 1
    return frequencies


def _lexical_scores(
    *,
    corpus_rows: list[ContinuityRecallCandidateRow],
    target_rows: list[ContinuityRecallCandidateRow],
    query_terms: list[str],
) -> dict[UUID, float]:
    if not target_rows or not query_terms:
        return {row["id"]: 0.0 for row in target_rows}
    if not corpus_rows:
        return {row["id"]: 0.0 for row in target_rows}

    unique_terms = list(dict.fromkeys(query_terms))
    document_frequencies: dict[str, int] = {term: 0 for term in unique_terms}
    corpus_term_frequencies: dict[UUID, dict[str, int]] = {}
    corpus_doc_lengths: dict[UUID, int] = {}

    for row in corpus_rows:
        frequencies = _token_frequency(
            _candidate_text(row),
            max_chars=_MAX_SIMILARITY_CANDIDATE_TEXT_CHARS,
            max_tokens=_MAX_SIMILARITY_TOKEN_COUNT,
        )
        corpus_term_frequencies[row["id"]] = frequencies
        corpus_doc_lengths[row["id"]] = sum(frequencies.values())
        for term in unique_terms:
            if frequencies.get(term, 0) > 0:
                document_frequencies[term] += 1

    average_doc_length = (
        sum(corpus_doc_lengths.values()) / float(len(corpus_doc_lengths))
        if corpus_doc_lengths
        else 1.0
    )
    k1 = 1.2
    b = 0.75
    document_count = len(corpus_rows)
    scores: dict[UUID, float] = {}
    for row in target_rows:
        score = 0.0
        frequencies = corpus_term_frequencies.get(row["id"])
        if frequencies is None:
            frequencies = _token_frequency(
                _candidate_text(row),
                max_chars=_MAX_SIMILARITY_CANDIDATE_TEXT_CHARS,
                max_tokens=_MAX_SIMILARITY_TOKEN_COUNT,
            )
        doc_length = max(sum(frequencies.values()), 1)
        for term in unique_terms:
            term_frequency = frequencies.get(term, 0)
            if term_frequency <= 0:
                continue
            doc_frequency = document_frequencies.get(term, 0)
            if doc_frequency <= 0:
                continue
            idf = math.log(1.0 + ((document_count - doc_frequency + 0.5) / (doc_frequency + 0.5)))
            denominator = term_frequency + k1 * (1.0 - b + b * (doc_length / max(average_doc_length, 1.0)))
            score += idf * ((term_frequency * (k1 + 1.0)) / denominator)
        scores[row["id"]] = score
    return scores


def _normalize_stage_scores(
    raw_scores: dict[UUID, float],
    *,
    reference_candidate_ids: set[UUID] | None = None,
) -> dict[UUID, float]:
    if not raw_scores:
        return {}
    if reference_candidate_ids is None:
        reference_scores = list(raw_scores.values())
    else:
        reference_scores = [
            score
            for candidate_id, score in raw_scores.items()
            if candidate_id in reference_candidate_ids
        ]
    if not reference_scores:
        return {candidate_id: 0.0 for candidate_id in raw_scores}
    max_score = max(reference_scores)
    if max_score <= 0.0:
        return {candidate_id: 0.0 for candidate_id in raw_scores}
    return {
        candidate_id: min(raw_score / max_score, 1.0)
        for candidate_id, raw_score in raw_scores.items()
    }


def _retrieval_trace_retention_until(*, now: datetime | None = None) -> datetime:
    current_time = datetime.now(tz=UTC) if now is None else now
    retention_days = get_settings().retrieval_trace_retention_days
    return current_time + timedelta(days=retention_days)


def _supersession_freshness_score(
    *,
    freshness_rank: int,
    supersession_rank: int,
) -> float:
    # Higher values favor current, fresher truth over stale superseded records.
    return (float(freshness_rank) * 2.0) + float(supersession_rank)


def _recency_score(*, created_at: datetime, newest_created_at: datetime) -> float:
    age_hours = max((newest_created_at - created_at).total_seconds(), 0.0) / 3600.0
    # Bounded [0, 1], with half-life controlled by _RECENCY_HALF_LIFE_HOURS.
    return 1.0 / (1.0 + (age_hours / _RECENCY_HALF_LIFE_HOURS))


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


def _ordering_metadata(item: RankedRecallCandidate) -> ContinuityRecallOrderingMetadata:
    row = item.row
    return {
        "scope_match_count": len(item.scope_matches),
        "query_term_match_count": item.query_term_match_count,
        "semantic_similarity_score": item.semantic_similarity_score,
        "exact_match_score": item.exact_match_score,
        "recency_score": item.recency_score,
        "temporal_overlap_score": item.temporal_overlap_score,
        "entity_match_count": item.entity_match_count,
        "confirmation_rank": item.confirmation_rank,
        "trust_class": item.trust_class,
        "trust_rank": item.trust_rank,
        "freshness_posture": item.freshness_posture,
        "freshness_rank": item.freshness_rank,
        "provenance_posture": item.provenance_posture,
        "provenance_rank": item.provenance_rank,
        "supersession_posture": item.supersession_posture,
        "supersession_rank": item.supersession_rank,
        "supersession_freshness_score": item.supersession_freshness_score,
        "posture_rank": item.posture_rank,
        "lifecycle_rank": item.lifecycle_rank,
        "confidence": float(row["confidence"]),
    }


def _serialize_recall_result(
    store: ContinuityStore,
    item: RankedRecallCandidate,
) -> ContinuityRecallResultRecord:
    row = item.row

    ordering = _ordering_metadata(item)

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
        "explanation": build_continuity_item_explanation(
            store,
            continuity_object_id=row["id"],
            capture_event_id=row["capture_event_id"],
            title=row["title"],
            body=row["body"],
            provenance=row["provenance"],
            status=row["status"],
            confidence=float(row["confidence"]),
            last_confirmed_at=row["last_confirmed_at"],
            supersedes_object_id=row["supersedes_object_id"],
            superseded_by_object_id=row["superseded_by_object_id"],
            created_at=row["object_created_at"],
            updated_at=row["object_updated_at"],
            confirmation_status=item.confirmation_status,
            provenance_posture=item.provenance_posture,
        ),
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


def _build_ranked_candidate(
    state: CandidateScoringState,
    *,
    relevance: float,
) -> RankedRecallCandidate:
    return RankedRecallCandidate(
        row=state.row,
        scope_matches=state.scope_matches,
        query_term_match_count=state.query_term_match_count,
        semantic_similarity_score=state.semantic_similarity_score,
        exact_match_score=state.exact_match_score,
        recency_score=state.recency_score,
        temporal_overlap_score=state.temporal_overlap_score,
        entity_match_count=state.entity_match_count,
        confirmation_status=state.confirmation_status,
        confirmation_rank=state.confirmation_rank,
        trust_class=state.trust_class,
        trust_rank=state.trust_rank,
        freshness_posture=state.freshness_posture,
        freshness_rank=state.freshness_rank,
        provenance_posture=state.provenance_posture,
        provenance_rank=state.provenance_rank,
        supersession_posture=state.supersession_posture,
        supersession_rank=state.supersession_rank,
        supersession_freshness_score=state.supersession_freshness_score,
        posture_rank=state.posture_rank,
        lifecycle_rank=state.lifecycle_rank,
        relevance=relevance,
    )


def _sort_ranked_candidates(
    ranked_candidates: list[RankedRecallCandidate],
    *,
    ranking_strategy: Literal["legacy_v1", "hybrid_v2"],
) -> list[RankedRecallCandidate]:
    if ranking_strategy == "legacy_v1":
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

    return sorted(
        ranked_candidates,
        key=lambda candidate: (
            candidate.relevance,
            len(candidate.scope_matches),
            candidate.entity_match_count,
            candidate.trust_rank,
            candidate.supersession_freshness_score,
            candidate.temporal_overlap_score,
            candidate.exact_match_score,
            candidate.semantic_similarity_score,
            candidate.query_term_match_count,
            candidate.confirmation_rank,
            candidate.provenance_rank,
            candidate.freshness_rank,
            candidate.posture_rank,
            candidate.lifecycle_rank,
            candidate.recency_score,
            float(candidate.row["confidence"]),
            str(candidate.row["id"]),
        ),
        reverse=True,
    )


def _ordered_recall_candidates(
    store: ContinuityStore,
    *,
    request: ContinuityRecallQueryInput,
    ranking_strategy: Literal["legacy_v1", "hybrid_v2"] = "hybrid_v2",
) -> tuple[list[RankedRecallCandidate], list[RetrievalTraceCandidate], list[str], EntityRetrievalContext]:
    thread_filter = _normalize_uuid_string(request.thread_id)
    task_filter = _normalize_uuid_string(request.task_id)
    project_filter = request.project.casefold() if request.project is not None else None
    person_filter = request.person.casefold() if request.person is not None else None
    query_terms = _query_terms(request.query)
    query_features = _build_similarity_query_features(request.query)
    entity_terms = _entity_query_terms(request)
    entity_context = _resolve_entity_retrieval_context(store, request=request)
    required_scope_count = sum(
        value is not None
        for value in (thread_filter, task_filter, project_filter, person_filter)
    )

    visible_candidates: list[tuple[ContinuityRecallCandidateRow, list[ContinuityRecallScopeMatch], bool]] = []
    for row in store.list_continuity_recall_candidates():
        if row["status"] == "deleted":
            continue
        if not bool(row.get("is_searchable", default_continuity_searchable(row["object_type"]))):
            continue
        if not _matches_time_window(row, since=request.since, until=request.until):
            continue

        scope_matches = _compute_scope_matches(
            row,
            thread_filter=thread_filter,
            task_filter=task_filter,
            project_filter=project_filter,
            person_filter=person_filter,
        )
        scope_matched = len(scope_matches) == required_scope_count
        visible_candidates.append((row, scope_matches, scope_matched))

    if not visible_candidates:
        return [], [], query_terms, entity_context

    candidate_rows = [row for row, _scope_matches, _scope_matched in visible_candidates]
    scope_matched_rows = [
        row
        for row, _scope_matches, scope_matched in visible_candidates
        if scope_matched
    ]
    scoring_reference_rows = scope_matched_rows if scope_matched_rows else candidate_rows
    reference_candidate_ids = {row["id"] for row in scoring_reference_rows}
    newest_created_at = max(row["object_created_at"] for row in scoring_reference_rows)
    lexical_raw_scores = _lexical_scores(
        corpus_rows=scoring_reference_rows,
        target_rows=candidate_rows,
        query_terms=query_terms,
    )

    scoring_states: list[CandidateScoringState] = []
    for row, scope_matches, scope_matched in visible_candidates:
        candidate_text = _candidate_text(row)
        candidate_text_casefold = candidate_text.casefold()
        query_term_match_count = _count_query_term_matches(
            candidate_text_casefold=candidate_text_casefold,
            terms=query_terms,
        )
        semantic_similarity_score = _semantic_similarity_score(
            query_features=query_features,
            candidate_text=candidate_text,
        )
        exact_match_score = _exact_match_score(
            query_features=query_features,
            candidate_text_casefold=candidate_text_casefold,
            title=row["title"],
        )
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
        trust_class = _extract_trust_class(
            row,
            confirmation_status=confirmation_status,
            provenance_posture=provenance_posture,
        )
        trust_rank = _TRUST_CLASS_RANK[trust_class]
        supersession_posture = _extract_supersession_posture(row)
        supersession_rank = _SUPERSESSION_RANK[supersession_posture]
        temporal_overlap_score = _temporal_overlap_score(
            row,
            since=request.since,
            until=request.until,
        )
        recency_score = _recency_score(
            created_at=row["object_created_at"],
            newest_created_at=newest_created_at,
        )
        entity_match_count = _entity_match_count(row, entity_terms=entity_terms)
        supersession_freshness_score = _supersession_freshness_score(
            freshness_rank=freshness_rank,
            supersession_rank=supersession_rank,
        )
        posture_rank = _POSTURE_RANK.get(row["admission_posture"], 0)
        lifecycle_rank = _LIFECYCLE_RANK.get(row["status"], 0)

        scoring_states.append(
            CandidateScoringState(
                row=row,
                scope_matches=scope_matches,
                scope_matched=scope_matched,
                query_term_match_count=query_term_match_count,
                semantic_similarity_score=semantic_similarity_score,
                exact_match_score=exact_match_score,
                recency_score=recency_score,
                temporal_overlap_score=temporal_overlap_score,
                entity_match_count=entity_match_count,
                lexical_raw_score=lexical_raw_scores.get(row["id"], 0.0),
                semantic_raw_score=exact_match_score + semantic_similarity_score,
                entity_edge_raw_score=_entity_edge_raw_score(
                    row,
                    entity_context=entity_context,
                ),
                temporal_raw_score=(temporal_overlap_score * 0.65) + (recency_score * 0.35),
                trust_raw_score=(
                    float(trust_rank)
                    + (float(confirmation_rank) * 0.5)
                    + (float(provenance_rank) * 0.35)
                    + (supersession_freshness_score * 0.35)
                ),
                confirmation_status=confirmation_status,
                confirmation_rank=confirmation_rank,
                trust_class=trust_class,
                trust_rank=trust_rank,
                freshness_posture=freshness_posture,
                freshness_rank=freshness_rank,
                provenance_posture=provenance_posture,
                provenance_rank=provenance_rank,
                supersession_posture=supersession_posture,
                supersession_rank=supersession_rank,
                supersession_freshness_score=supersession_freshness_score,
                posture_rank=posture_rank,
                lifecycle_rank=lifecycle_rank,
            )
        )

    lexical_normalized = _normalize_stage_scores(
        {state.row["id"]: state.lexical_raw_score for state in scoring_states},
        reference_candidate_ids=reference_candidate_ids,
    )
    semantic_normalized = _normalize_stage_scores(
        {state.row["id"]: state.semantic_raw_score for state in scoring_states},
        reference_candidate_ids=reference_candidate_ids,
    )
    entity_edge_normalized = _normalize_stage_scores(
        {state.row["id"]: state.entity_edge_raw_score for state in scoring_states},
        reference_candidate_ids=reference_candidate_ids,
    )
    temporal_normalized = _normalize_stage_scores(
        {state.row["id"]: state.temporal_raw_score for state in scoring_states},
        reference_candidate_ids=reference_candidate_ids,
    )
    trust_normalized = _normalize_stage_scores(
        {state.row["id"]: state.trust_raw_score for state in scoring_states},
        reference_candidate_ids=reference_candidate_ids,
    )

    ranked_candidates: list[RankedRecallCandidate] = []
    excluded_by_id: dict[UUID, str] = {}
    stage_scores_by_id: dict[UUID, CandidateStageScores] = {}
    stage_reasons_by_id: dict[UUID, dict[str, str]] = {}

    has_stream_query = bool(query_terms) or bool(entity_context.expansion_names)
    for state in scoring_states:
        candidate_id = state.row["id"]
        stage_scores = CandidateStageScores(
            lexical_raw=state.lexical_raw_score,
            lexical_normalized=lexical_normalized.get(candidate_id, 0.0),
            semantic_raw=state.semantic_raw_score,
            semantic_normalized=semantic_normalized.get(candidate_id, 0.0),
            entity_edge_raw=state.entity_edge_raw_score,
            entity_edge_normalized=entity_edge_normalized.get(candidate_id, 0.0),
            temporal_raw=state.temporal_raw_score,
            temporal_normalized=temporal_normalized.get(candidate_id, 0.0),
            trust_raw=state.trust_raw_score,
            trust_normalized=trust_normalized.get(candidate_id, 0.0),
        )
        stage_scores_by_id[candidate_id] = stage_scores
        stage_reasons_by_id[candidate_id] = {
            "lexical": (
                "BM25-style lexical overlap across scoped continuity text."
                if stage_scores.lexical_raw > 0.0
                else "No lexical overlap with the query terms."
            ),
            "semantic": (
                "Exact or semantic similarity matched the query wording."
                if stage_scores.semantic_raw > 0.0
                else "No semantic similarity above the retrieval threshold."
            ),
            "entity_edge": (
                "Entity anchors or connected entities matched continuity provenance/body."
                if stage_scores.entity_edge_raw > 0.0
                else "No direct or traversed entity match was found."
            ),
            "temporal": (
                "Recency and temporal overlap favored this candidate."
                if stage_scores.temporal_raw > 0.0
                else "No temporal signal applied."
            ),
            "trust": (
                "Trust, confirmation, provenance, and supersession posture favored this candidate."
                if stage_scores.trust_raw > 0.0
                else "Trust reranking contributed no score."
            ),
        }

        if not state.scope_matched:
            excluded_by_id[candidate_id] = "scope_mismatch"
            continue

        if ranking_strategy == "legacy_v1":
            if query_terms and state.query_term_match_count == 0:
                excluded_by_id[candidate_id] = "no_lexical_match"
                continue
            relevance = (
                float(len(state.scope_matches)) * 100.0
                + float(state.query_term_match_count) * 20.0
                + float(state.confirmation_rank) * 14.0
                + float(state.freshness_rank) * 12.0
                + float(state.provenance_rank) * 8.0
                + float(state.supersession_rank) * 10.0
                + float(state.posture_rank) * 4.0
                + float(state.lifecycle_rank) * 2.0
                + float(state.row["confidence"])
            )
        else:
            stream_matched = (
                stage_scores.lexical_raw > 0.0
                or stage_scores.semantic_raw > 0.0
                or stage_scores.entity_edge_raw > 0.0
            )
            if has_stream_query and not stream_matched:
                excluded_by_id[candidate_id] = "no_stream_match"
                continue
            relevance = (
                float(len(state.scope_matches)) * 100.0
                + stage_scores.entity_edge_normalized * 30.0
                + stage_scores.lexical_normalized * 28.0
                + stage_scores.semantic_normalized * 26.0
                + stage_scores.temporal_normalized * 16.0
                + stage_scores.trust_normalized * 18.0
                + float(state.confirmation_rank) * 6.0
                + float(state.provenance_rank) * 5.0
                + state.supersession_freshness_score * 6.0
                + float(state.posture_rank) * 4.0
                + float(state.lifecycle_rank) * 3.0
                + float(state.row["confidence"])
            )

        ranked_candidates.append(_build_ranked_candidate(state, relevance=relevance))

    ordered_ranked_candidates = _sort_ranked_candidates(
        ranked_candidates,
        ranking_strategy=ranking_strategy,
    )
    selected_ids = [candidate.row["id"] for candidate in ordered_ranked_candidates]
    selected_rank_by_id = {
        candidate_id: index
        for index, candidate_id in enumerate(selected_ids, start=1)
    }

    trace_candidates: list[RetrievalTraceCandidate] = []
    for state in scoring_states:
        candidate_id = state.row["id"]
        selected = candidate_id in selected_rank_by_id
        rank = selected_rank_by_id.get(candidate_id)
        ranked = next(
            (
                candidate
                for candidate in ordered_ranked_candidates
                if candidate.row["id"] == candidate_id
            ),
            _build_ranked_candidate(
                state,
                relevance=0.0,
            ),
        )
        trace_candidates.append(
            RetrievalTraceCandidate(
                ranked=ranked,
                rank=rank,
                selected=selected,
                exclusion_reason=excluded_by_id.get(candidate_id),
                stage_scores=stage_scores_by_id[candidate_id],
                stage_reasons=stage_reasons_by_id[candidate_id],
            )
        )

    trace_candidates.sort(
        key=lambda candidate: (
            0 if candidate.selected else 1,
            candidate.rank if candidate.rank is not None else MAX_CONTINUITY_RECALL_LIMIT + 1,
            -candidate.ranked.relevance,
            str(candidate.ranked.row["id"]),
        )
    )
    return ordered_ranked_candidates, trace_candidates, query_terms, entity_context


def _serialize_debug_candidate(
    trace_candidate: RetrievalTraceCandidate,
) -> ContinuityRetrievalDebugCandidateRecord:
    ordering = _ordering_metadata(trace_candidate.ranked)
    stage_scores = trace_candidate.stage_scores
    return {
        "object_id": str(trace_candidate.ranked.row["id"]),
        "title": trace_candidate.ranked.row["title"],
        "object_type": trace_candidate.ranked.row["object_type"],  # type: ignore[typeddict-item]
        "status": trace_candidate.ranked.row["status"],  # type: ignore[typeddict-item]
        "selected": trace_candidate.selected,
        "rank": trace_candidate.rank,
        "exclusion_reason": trace_candidate.exclusion_reason,
        "scope_matches": trace_candidate.ranked.scope_matches,
        "ordering": ordering,
        "stage_scores": {
            "lexical": {
                "raw_score": stage_scores.lexical_raw,
                "normalized_score": stage_scores.lexical_normalized,
                "matched": stage_scores.lexical_raw > 0.0,
                "reason": trace_candidate.stage_reasons["lexical"],
            },
            "semantic": {
                "raw_score": stage_scores.semantic_raw,
                "normalized_score": stage_scores.semantic_normalized,
                "matched": stage_scores.semantic_raw > 0.0,
                "reason": trace_candidate.stage_reasons["semantic"],
            },
            "entity_edge": {
                "raw_score": stage_scores.entity_edge_raw,
                "normalized_score": stage_scores.entity_edge_normalized,
                "matched": stage_scores.entity_edge_raw > 0.0,
                "reason": trace_candidate.stage_reasons["entity_edge"],
            },
            "temporal": {
                "raw_score": stage_scores.temporal_raw,
                "normalized_score": stage_scores.temporal_normalized,
                "matched": stage_scores.temporal_raw > 0.0,
                "reason": trace_candidate.stage_reasons["temporal"],
            },
            "trust": {
                "raw_score": stage_scores.trust_raw,
                "normalized_score": stage_scores.trust_normalized,
                "matched": stage_scores.trust_raw > 0.0,
                "reason": trace_candidate.stage_reasons["trust"],
            },
        },
        "relevance": trace_candidate.ranked.relevance,
    }


def _serialize_retrieval_run(run: RetrievalRunRow) -> RetrievalRunRecord:
    return {
        "id": str(run["id"]),
        "source_surface": run["source_surface"],
        "ranking_strategy": run["ranking_strategy"],
        "query_text": run["query_text"],
        "request_scope": run["request_scope"],
        "result_ids": run["result_ids"],
        "exclusion_summary": run["exclusion_summary"],
        "candidate_count": run["candidate_count"],
        "selected_count": run["selected_count"],
        "debug_enabled": run["debug_enabled"],
        "retention_until": run["retention_until"].isoformat(),
        "created_at": run["created_at"].isoformat(),
    }


def _debug_candidate_from_row(row: RetrievalCandidateRow) -> ContinuityRetrievalDebugCandidateRecord:
    ordering = cast(ContinuityRecallOrderingMetadata, row["ordering"])
    stage_details = row["stage_details"]
    return {
        "object_id": str(row["continuity_object_id"]),
        "title": row["title"],
        "object_type": row["object_type"],  # type: ignore[typeddict-item]
        "status": row["status"],  # type: ignore[typeddict-item]
        "selected": row["selected"],
        "rank": row["rank"],
        "exclusion_reason": row["exclusion_reason"],
        "scope_matches": cast(list[ContinuityRecallScopeMatch], row["scope_matches"]),
        "ordering": ordering,
        "stage_scores": cast(dict[str, dict[str, object]], stage_details),
        "relevance": float(row["relevance"]),
    }


def _persist_retrieval_trace(
    store: ContinuityStore,
    *,
    request: ContinuityRecallQueryInput,
    ranking_strategy: Literal["legacy_v1", "hybrid_v2"],
    source_surface: str,
    returned_candidates: list[RankedRecallCandidate],
    trace_candidates: list[RetrievalTraceCandidate],
) -> str | None:
    create_retrieval_run = getattr(store, "create_retrieval_run", None)
    create_retrieval_candidate = getattr(store, "create_retrieval_candidate", None)
    if not callable(create_retrieval_run) or not callable(create_retrieval_candidate):
        return None

    exclusion_summary: JsonObject = {}
    for trace_candidate in trace_candidates:
        if trace_candidate.exclusion_reason is None:
            continue
        exclusion_summary[trace_candidate.exclusion_reason] = int(
            exclusion_summary.get(trace_candidate.exclusion_reason, 0)
        ) + 1

    run = create_retrieval_run(
        source_surface=source_surface,
        ranking_strategy=ranking_strategy,
        query_text=request.query,
        request_scope=cast(JsonObject, request.as_payload()),
        result_ids=[str(candidate.row["id"]) for candidate in returned_candidates],
        exclusion_summary=exclusion_summary,
        candidate_count=len(trace_candidates),
        selected_count=len(returned_candidates),
        debug_enabled=request.debug,
        retention_until=_retrieval_trace_retention_until(),
    )

    for trace_candidate in trace_candidates:
        debug_candidate = _serialize_debug_candidate(trace_candidate)
        create_retrieval_candidate(
            retrieval_run_id=run["id"],
            continuity_object_id=trace_candidate.ranked.row["id"],
            rank=trace_candidate.rank,
            selected=trace_candidate.selected,
            exclusion_reason=trace_candidate.exclusion_reason,
            lexical_score=trace_candidate.stage_scores.lexical_raw,
            semantic_score=trace_candidate.stage_scores.semantic_raw,
            entity_edge_score=trace_candidate.stage_scores.entity_edge_raw,
            temporal_score=trace_candidate.stage_scores.temporal_raw,
            trust_score=trace_candidate.stage_scores.trust_raw,
            relevance=trace_candidate.ranked.relevance,
            scope_matches=cast(list[JsonObject], debug_candidate["scope_matches"]),
            stage_details=cast(JsonObject, debug_candidate["stage_scores"]),
            ordering=cast(JsonObject, debug_candidate["ordering"]),
            title=trace_candidate.ranked.row["title"],
            object_type=trace_candidate.ranked.row["object_type"],
            status=trace_candidate.ranked.row["status"],
        )

    return str(run["id"])


def list_retrieval_runs(
    store: ContinuityStore,
    *,
    user_id: UUID,
    limit: int = DEFAULT_RETRIEVAL_RUN_LIST_LIMIT,
) -> RetrievalRunListResponse:
    del user_id
    if limit < 1 or limit > MAX_RETRIEVAL_RUN_LIST_LIMIT:
        raise ContinuityRecallValidationError(
            f"limit must be between 1 and {MAX_RETRIEVAL_RUN_LIST_LIMIT}"
        )

    rows = store.list_retrieval_runs(limit=limit)
    items = [_serialize_retrieval_run(row) for row in rows]
    summary: RetrievalRunListSummary = {
        "limit": limit,
        "returned_count": len(items),
        "total_count": len(items),
        "order": list(RETRIEVAL_RUN_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_retrieval_trace(
    store: ContinuityStore,
    *,
    user_id: UUID,
    retrieval_run_id: UUID,
) -> RetrievalTraceResponse:
    del user_id
    run = store.get_retrieval_run_optional(retrieval_run_id)
    if run is None:
        raise RetrievalTraceNotFoundError(f"retrieval run {retrieval_run_id} was not found")

    candidates = [
        _debug_candidate_from_row(row)
        for row in store.list_retrieval_candidates_for_run(retrieval_run_id)
    ]
    summary: RetrievalTraceSummary = {
        "candidate_count": len(candidates),
        "selected_count": sum(1 for candidate in candidates if candidate["selected"]),
        "order": list(RETRIEVAL_TRACE_CANDIDATE_ORDER),
    }
    return {
        "retrieval_run": _serialize_retrieval_run(run),
        "candidates": candidates,
        "summary": summary,
    }


def query_continuity_recall(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContinuityRecallQueryInput,
    apply_limit: bool = True,
    ranking_strategy: Literal["legacy_v1", "hybrid_v2"] = "hybrid_v2",
    source_surface: str = "continuity_recall",
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
        debug=request.debug,
    )

    _validate_request(normalized_request)

    ordered_candidates, trace_candidates, query_terms, entity_context = _ordered_recall_candidates(
        store,
        request=normalized_request,
        ranking_strategy=ranking_strategy,
    )

    if apply_limit:
        returned_candidates = ordered_candidates[: normalized_request.limit]
    else:
        returned_candidates = ordered_candidates
    returned_candidate_ids = {candidate.row["id"] for candidate in returned_candidates}
    final_trace_candidates = [
        RetrievalTraceCandidate(
            ranked=trace_candidate.ranked,
            rank=trace_candidate.rank,
            selected=trace_candidate.ranked.row["id"] in returned_candidate_ids,
            exclusion_reason=(
                trace_candidate.exclusion_reason
                if trace_candidate.ranked.row["id"] not in returned_candidate_ids
                and trace_candidate.exclusion_reason is not None
                else (
                    None
                    if trace_candidate.ranked.row["id"] in returned_candidate_ids
                    else "trimmed_by_limit"
                )
            ),
            stage_scores=trace_candidate.stage_scores,
            stage_reasons=trace_candidate.stage_reasons,
        )
        for trace_candidate in trace_candidates
    ]
    final_trace_candidates.sort(
        key=lambda candidate: (
            0 if candidate.selected else 1,
            candidate.rank if candidate.rank is not None else MAX_CONTINUITY_RECALL_LIMIT + 1,
            -candidate.ranked.relevance,
            str(candidate.ranked.row["id"]),
        )
    )
    items = [_serialize_recall_result(store, item) for item in returned_candidates]
    retrieval_run_id = _persist_retrieval_trace(
        store,
        request=normalized_request,
        ranking_strategy=ranking_strategy,
        source_surface=source_surface,
        returned_candidates=returned_candidates,
        trace_candidates=final_trace_candidates,
    )

    payload: ContinuityRecallResponse = {
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
    if normalized_request.debug:
        payload["debug"] = {
            "retrieval_run_id": retrieval_run_id,
            "source_surface": source_surface,
            "ranking_strategy": ranking_strategy,
            "query_terms": query_terms,
            "entity_anchor_names": list(entity_context.anchor_names),
            "entity_expansion_names": list(entity_context.expansion_names),
            "candidate_count": len(final_trace_candidates),
            "selected_count": len(returned_candidates),
            "candidates": [_serialize_debug_candidate(candidate) for candidate in final_trace_candidates],
        }
    return payload


def build_default_recall_query_input() -> ContinuityRecallQueryInput:
    return ContinuityRecallQueryInput(limit=DEFAULT_CONTINUITY_RECALL_LIMIT)
