from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import re
from typing import Mapping, Protocol, Sequence
from uuid import uuid4

# Read-only reuse of the contradiction-detection machinery that backs
# VNextContradictionService. compile_context_pack must not mutate state,
# so it calls the pure candidate finder directly instead of
# generate_contradiction_report (which persists edges/artifacts/events).
from alicebot_api import vnext_contradictions
from alicebot_api.vnext_embeddings import (
    EmbeddingProvider,
    VNextEmbeddingConfigurationError,
    VNextEmbeddingProviderError,
    get_embedding_provider,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_CONTEXT_PACK_LIMIT = 8
DEFAULT_SOURCE_LIMIT = 8
DEFAULT_OPEN_LOOP_LIMIT = 8
DEFAULT_RECENT_CHANGES_LIMIT = 5
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
STRATEGIC_QUERY_TYPES = {"strategic_synthesis", "contradiction_check", "project_status", "agent_context"}
RRF_K = 60
VECTOR_STAGE_ENABLED = "enabled"
VECTOR_STAGE_DISABLED_NO_PROVIDER = "disabled: no embedding provider configured"
VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT = "disabled: store does not support vector search"
# Crude token estimate: ~4 characters of serialized JSON per token. Used by
# the greedy context-pack budget packer; precision is not required, only a
# stable, monotone proxy for payload size.
TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4
# A memory whose last_confirmed_at is older than this many days gets a
# "staleness" note attached in the context pack so agents can weigh it.
STALENESS_NOTE_AFTER_DAYS = 90
# Trace exclusion_reason for items selected by ranking but dropped by the
# token budget packer.
EXCLUSION_REASON_TOKEN_BUDGET = "token_budget"
CONTRADICTIONS_STAGE_ENABLED = "enabled"
CONTRADICTIONS_STAGE_NOT_REQUESTED = "disabled: not requested"
CONTRADICTIONS_STAGE_NO_STORE_SUPPORT = "disabled: store does not support beliefs"


class VNextRetrievalValidationError(ValueError):
    """Raised when a vNext retrieval request is invalid."""


class VNextRetrievalStore(Protocol):
    """Minimum store surface for context-pack retrieval.

    Stores may additionally expose ``search_memories_fts`` and
    ``search_memories_vector`` (see ``PostgresVNextStore``); the service
    detects them at runtime and degrades to ``search_memories`` otherwise.
    The same applies to ``list_events`` (recent_changes section) and
    ``list_beliefs`` (contradicting_evidence section): stores without them
    yield empty sections instead of failing.

    ``memory_types``/``projects`` are only forwarded to the store when the
    request sets them, so minimal stores that predate those keyword
    arguments keep working for unfiltered requests.
    """

    def append_event(self, event: JsonObject) -> JsonObject: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONTEXT_PACK_LIMIT,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        include_expired: bool = False,
    ) -> list[JsonObject]: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_SOURCE_LIMIT,
    ) -> list[JsonObject]: ...

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_OPEN_LOOP_LIMIT,
    ) -> list[JsonObject]: ...

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[JsonObject]: ...

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class VNextRetrievalRequest:
    query: str
    domains: tuple[str, ...] = ()
    projects: tuple[str, ...] = ()
    people: tuple[str, ...] = ()
    memory_types: tuple[str, ...] = ()
    time_window: str = "all"
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    include_sources: bool = True
    include_contradictions: bool = True
    max_items: int = DEFAULT_CONTEXT_PACK_LIMIT
    # None means "no token budget": nothing is dropped, but the pack still
    # reports its token estimate. When set, the greedy packer enforces it.
    max_tokens: int | None = None
    actor_type: str = "system"
    actor_id: str | None = None
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    trace_id: str | None = None
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    item: JsonObject
    target_type: str
    rank: int
    rrf_score: float
    stage_ranks: dict[str, int]
    selected: bool
    exclusion_reason: str | None = None

    def to_trace_record(self) -> JsonObject:
        return {
            "target_type": self.target_type,
            "target_id": str(self.item.get("id")),
            "rank": self.rank,
            "rrf_score": round(self.rrf_score, 6),
            "stage_ranks": dict(self.stage_ranks),
            "selected": self.selected,
            "exclusion_reason": self.exclusion_reason,
        }


def normalize_query(query: str) -> str:
    normalized = " ".join(query.split()).strip()
    if normalized == "":
        raise VNextRetrievalValidationError("query must not be empty")
    return normalized


def query_terms(query: str) -> list[str]:
    terms = [term.casefold() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", normalize_query(query))]
    stopwords = {"about", "what", "when", "where", "which", "with", "from", "this", "that", "should", "could"}
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in stopwords or term in seen:
            continue
        deduped.append(term)
        seen.add(term)
    return deduped


def _contains_any(query: str, words: tuple[str, ...]) -> bool:
    lowered = query.casefold()
    return any(word in lowered for word in words)


def classify_query(request: VNextRetrievalRequest) -> JsonObject:
    query = normalize_query(request.query)
    lowered = query.casefold()

    if _contains_any(lowered, ("contradict", "conflict", "inconsistent", "disagree")):
        query_type = "contradiction_check"
    elif _contains_any(lowered, ("open loop", "todo", "waiting", "blocked", "unresolved")):
        query_type = "open_loop_review"
    elif _contains_any(lowered, ("project", "status", "roadmap", "milestone", "next step")):
        query_type = "project_status"
    elif _contains_any(lowered, ("who is", "person", "people", "relationship")):
        query_type = "people_context"
    elif _contains_any(lowered, ("when", "timeline", "history", "changed", "since")):
        query_type = "temporal_recall"
    elif _contains_any(lowered, ("draft", "write", "compose")):
        query_type = "draft_generation"
    elif _contains_any(lowered, ("agent", "context pack", "handoff", "resume")):
        query_type = "agent_context"
    elif query.startswith('"') and query.endswith('"'):
        query_type = "exact_recall"
    else:
        query_type = "strategic_synthesis"

    domains = list(request.domains) or _infer_domains(lowered)
    sensitivity_allowed = list(request.sensitivity_allowed) or list(DEFAULT_SENSITIVITY_ALLOWED)
    return {
        "query": query,
        "query_type": query_type,
        "terms": query_terms(query),
        "domains": domains,
        "projects": list(request.projects),
        "people": list(request.people),
        "memory_types": list(request.memory_types),
        "time_window": request.time_window,
        "sensitivity_allowed": sensitivity_allowed,
        "requires_sources": request.include_sources or query_type in STRATEGIC_QUERY_TYPES,
        "requires_contradictions": request.include_contradictions and query_type in STRATEGIC_QUERY_TYPES,
        "requires_raw_evidence": _contains_any(lowered, ("quote", "source", "evidence", "prove", "where did")),
    }


def _infer_domains(lowered_query: str) -> list[str]:
    domains: list[str] = []
    if _contains_any(lowered_query, ("alice", "project", "roadmap", "sprint", "build")):
        domains.extend(["project", "professional"])
    if _contains_any(lowered_query, ("family", "health", "spiritual", "money", "legal")):
        domains.append("personal")
    return domains


def _allowed(item: JsonObject, *, domains: list[str], sensitivity_allowed: list[str]) -> str | None:
    item_domain = item.get("domain")
    item_sensitivity = item.get("sensitivity")
    if domains and isinstance(item_domain, str) and item_domain not in domains and item_domain != "unknown":
        return "domain_filtered"
    if isinstance(item_sensitivity, str) and item_sensitivity not in sensitivity_allowed:
        return "sensitivity_filtered"
    return None


def reciprocal_rank_fusion(
    ranked_lists: Mapping[str, Sequence[JsonObject]],
    *,
    k: int = RRF_K,
) -> list[tuple[JsonObject, float, dict[str, int]]]:
    """Fuse per-stage ranked result lists with Reciprocal Rank Fusion.

    Each item scores ``sum(1 / (k + rank))`` over the stages it appears in.
    Returns ``(item, rrf_score, stage_ranks)`` tuples ordered by descending
    score with a deterministic id tie-break.
    """
    if k < 1:
        raise VNextRetrievalValidationError("reciprocal rank fusion k must be at least 1")
    items: dict[str, JsonObject] = {}
    scores: dict[str, float] = {}
    stage_ranks: dict[str, dict[str, int]] = {}
    for stage, rows in ranked_lists.items():
        for rank, row in enumerate(rows, start=1):
            item_id = str(row.get("id"))
            if item_id not in items:
                items[item_id] = row
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            stage_ranks.setdefault(item_id, {})[stage] = rank
    ordered_ids = sorted(items, key=lambda item_id: (-scores[item_id], item_id))
    return [(items[item_id], scores[item_id], stage_ranks[item_id]) for item_id in ordered_ids]


def _fused_candidates(
    ranked_lists: Mapping[str, Sequence[JsonObject]],
    *,
    target_type: str,
    domains: list[str],
    sensitivity_allowed: list[str],
    limit: int,
) -> list[RetrievalCandidate]:
    candidates: list[RetrievalCandidate] = []
    selected_count = 0
    for rank, (item, rrf_score, stage_ranks) in enumerate(reciprocal_rank_fusion(ranked_lists), start=1):
        exclusion_reason = _allowed(item, domains=domains, sensitivity_allowed=sensitivity_allowed)
        selected = exclusion_reason is None and selected_count < limit
        if selected:
            selected_count += 1
        elif exclusion_reason is None:
            exclusion_reason = "trimmed_by_limit"
        candidates.append(
            RetrievalCandidate(
                item=item,
                target_type=target_type,
                rank=rank,
                rrf_score=rrf_score,
                stage_ranks=stage_ranks,
                selected=selected,
                exclusion_reason=exclusion_reason,
            )
        )
    return candidates


def _compact_item(item: JsonObject) -> JsonObject:
    return {key: value for key, value in item.items() if key != "deleted_at"}


def estimate_item_tokens(item: JsonObject) -> int:
    """Estimate the token cost of one pack item (chars/4 heuristic)."""
    try:
        text = json.dumps(json_safe(item), ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        text = str(item)
    chars = len(text)
    return max(1, (chars + TOKEN_ESTIMATE_CHARS_PER_TOKEN - 1) // TOKEN_ESTIMATE_CHARS_PER_TOKEN)


@dataclass(slots=True)
class _TokenBudget:
    """Greedy token-budget packer state.

    Items are offered in priority order. Once one item does not fit, the
    budget is marked truncated and every later item is dropped too, keeping
    the packed prefix aligned with the ranking order.
    """

    token_budget: int | None
    token_estimate: int = 0
    truncated: bool = False
    dropped_item_count: int = 0

    def admit(self, item: JsonObject) -> bool:
        cost = estimate_item_tokens(item)
        if self.truncated or (
            self.token_budget is not None and self.token_estimate + cost > self.token_budget
        ):
            self.truncated = True
            self.dropped_item_count += 1
            return False
        self.token_estimate += cost
        return True

    def to_record(self) -> JsonObject:
        return {
            "token_budget": self.token_budget,
            "token_estimate": self.token_estimate,
            "truncated": self.truncated,
            "dropped_item_count": self.dropped_item_count,
        }


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _staleness_note(memory: JsonObject, *, now: datetime) -> JsonObject | None:
    """Note for memories not confirmed within STALENESS_NOTE_AFTER_DAYS days."""
    last_confirmed = _parse_timestamp(memory.get("last_confirmed_at"))
    if last_confirmed is None:
        return None
    age_days = (now - last_confirmed).days
    if age_days <= STALENESS_NOTE_AFTER_DAYS:
        return None
    return {
        "days_since_last_confirmed": age_days,
        "threshold_days": STALENESS_NOTE_AFTER_DAYS,
        "note": f"last confirmed {age_days} days ago (over the {STALENESS_NOTE_AFTER_DAYS}-day threshold)",
    }


def _memory_title(memory: JsonObject) -> str:
    for key in ("title", "canonical_text", "summary", "memory_key"):
        value = memory.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().splitlines()[0][:120]
    return str(memory.get("id"))


def _memory_reference(memory: JsonObject) -> JsonObject:
    return {
        "id": str(memory.get("id")),
        "title": _memory_title(memory),
        "memory_type": memory.get("memory_type"),
    }


def _optional_search_filters(
    memory_types: tuple[str, ...],
    projects: tuple[str, ...],
) -> dict[str, object]:
    """Only forward filter kwargs when set, so minimal stores keep working."""
    filters: dict[str, object] = {}
    if memory_types:
        filters["memory_types"] = tuple(memory_types)
    if projects:
        filters["projects"] = tuple(projects)
    return filters


def _apply_budget_exclusions(
    candidates: list[RetrievalCandidate],
    kept_items: list[JsonObject],
) -> list[RetrievalCandidate]:
    """Deselect ranking-selected candidates the token budget dropped."""
    kept_ids = {str(item.get("id")) for item in kept_items}
    updated: list[RetrievalCandidate] = []
    for candidate in candidates:
        if candidate.selected and str(candidate.item.get("id")) not in kept_ids:
            updated.append(replace(candidate, selected=False, exclusion_reason=EXCLUSION_REASON_TOKEN_BUDGET))
        else:
            updated.append(candidate)
    return updated


class VNextRetrievalService:
    def __init__(
        self,
        store: VNextRetrievalStore,
        *,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.store = store
        self.embedding_provider = embedding_provider if embedding_provider is not None else get_embedding_provider()

    def _memory_fts_rows(
        self,
        *,
        query: str,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
    ) -> tuple[list[JsonObject], str]:
        filters = _optional_search_filters(memory_types, projects)
        search_memories_fts = getattr(self.store, "search_memories_fts", None)
        if callable(search_memories_fts):
            rows = search_memories_fts(
                query=query,
                domains=domains or None,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit,
                **filters,
            )
            return list(rows), "postgres_fts"
        rows = self.store.search_memories(
            query=query,
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=limit,
            **filters,
        )
        return list(rows), "store_lexical"

    def _memory_vector_rows(
        self,
        *,
        query: str,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
    ) -> tuple[list[JsonObject], str]:
        if self.embedding_provider is None:
            return [], VECTOR_STAGE_DISABLED_NO_PROVIDER
        search_memories_vector = getattr(self.store, "search_memories_vector", None)
        if not callable(search_memories_vector):
            return [], VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT
        try:
            query_vector = self.embedding_provider.embed_text(query)
            rows = search_memories_vector(
                query_vector=query_vector,
                domains=domains or None,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit,
                **_optional_search_filters(memory_types, projects),
            )
        except (VNextEmbeddingConfigurationError, VNextEmbeddingProviderError) as exc:
            return [], f"disabled: query embedding failed ({exc})"
        return list(rows), VECTOR_STAGE_ENABLED

    def compile_context_pack(self, request: VNextRetrievalRequest) -> JsonObject:
        if request.max_tokens is not None and request.max_tokens < 1:
            raise VNextRetrievalValidationError("max_tokens must be a positive integer when set")
        interpretation = classify_query(request)
        terms = list(interpretation["terms"])  # type: ignore[arg-type]
        domains = list(interpretation["domains"])  # type: ignore[arg-type]
        sensitivity_allowed = list(interpretation["sensitivity_allowed"])  # type: ignore[arg-type]
        memory_types = tuple(request.memory_types)
        projects = tuple(request.projects)
        trace_id = request.trace_id or str(uuid4())
        context_pack_id = str(uuid4())
        memory_candidate_limit = max(request.max_items * 2, request.max_items)

        fts_rows, fts_source = self._memory_fts_rows(
            query=request.query,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=memory_candidate_limit,
            memory_types=memory_types,
            projects=projects,
        )
        vector_rows, vector_stage = self._memory_vector_rows(
            query=str(interpretation["query"]),
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=memory_candidate_limit,
            memory_types=memory_types,
            projects=projects,
        )
        memory_lists: dict[str, Sequence[JsonObject]] = {"fts": fts_rows}
        if vector_stage == VECTOR_STAGE_ENABLED:
            memory_lists["vector"] = vector_rows

        source_rows = self.store.search_sources(
            query=request.query,
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=max(DEFAULT_SOURCE_LIMIT, request.max_items),
        )
        open_loop_rows = self.store.list_open_loops(
            status="open",
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_OPEN_LOOP_LIMIT,
        )

        memory_candidates = _fused_candidates(
            memory_lists,
            target_type="memory",
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=request.max_items,
        )
        source_candidates = _fused_candidates(
            {"lexical": source_rows},
            target_type="source",
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_SOURCE_LIMIT,
        )
        open_loop_candidates = _fused_candidates(
            {"listing": open_loop_rows},
            target_type="open_loop",
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_OPEN_LOOP_LIMIT,
        )

        selected_memories = [_compact_item(candidate.item) for candidate in memory_candidates if candidate.selected]
        selected_sources = [_compact_item(candidate.item) for candidate in source_candidates if candidate.selected]
        selected_open_loops = [_compact_item(candidate.item) for candidate in open_loop_candidates if candidate.selected]

        # Greedy token-budget packing in priority order: memories (fused
        # rank), then open loops, then sources, then provenance quotes.
        budget = _TokenBudget(token_budget=request.max_tokens)
        selected_memories = [item for item in selected_memories if budget.admit(item)]
        selected_open_loops = [item for item in selected_open_loops if budget.admit(item)]
        selected_sources = [item for item in selected_sources if budget.admit(item)]
        supporting_evidence = [
            evidence for evidence in self._supporting_evidence(selected_memories) if budget.admit(evidence)
        ]
        memory_candidates = _apply_budget_exclusions(memory_candidates, selected_memories)
        open_loop_candidates = _apply_budget_exclusions(open_loop_candidates, selected_open_loops)
        source_candidates = _apply_budget_exclusions(source_candidates, selected_sources)

        now = datetime.now(UTC)
        for memory in selected_memories:
            staleness = _staleness_note(memory, now=now)
            if staleness is not None:
                memory["staleness"] = staleness

        contradicting_evidence, contradictions_stage = self._contradicting_evidence(
            selected_memories,
            requested=bool(interpretation["requires_contradictions"]),
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
        )
        recent_changes = self._recent_changes()

        warnings = self._warnings(
            memory_candidates=memory_candidates,
            source_candidates=source_candidates,
            open_loop_candidates=open_loop_candidates,
        )
        all_candidates = [*memory_candidates, *source_candidates, *open_loop_candidates]
        excluded_counts: dict[str, int] = {}
        for candidate in all_candidates:
            if candidate.exclusion_reason is None:
                continue
            excluded_counts[candidate.exclusion_reason] = excluded_counts.get(candidate.exclusion_reason, 0) + 1
        selected_trace = [candidate.to_trace_record() for candidate in all_candidates if candidate.selected]
        trace = {
            "trace_id": trace_id,
            "candidate_count": len(all_candidates),
            "selected_count": len(selected_trace),
            "query_terms": terms,
            "filters": {
                "domains": domains,
                "sensitivity_allowed": sensitivity_allowed,
                "time_window": request.time_window,
                "memory_types": list(memory_types),
                "projects": list(projects),
            },
            "fusion": {"algorithm": "reciprocal_rank_fusion", "k": RRF_K},
            "vector_stage": vector_stage,
            "budget": budget.to_record(),
            "stages": {
                "fts": {"source": fts_source, "candidate_count": len(fts_rows)},
                "vector": {"status": vector_stage, "candidate_count": len(vector_rows)},
                "sources": {"source": "store_lexical", "candidate_count": len(source_rows)},
                "open_loops": {"candidate_count": len(open_loop_rows)},
                "contradictions": {"status": contradictions_stage, "candidate_count": len(contradicting_evidence)},
                "recent_changes": {"candidate_count": len(recent_changes)},
            },
            "selected": selected_trace,
            "excluded_counts": excluded_counts,
        }
        pack: JsonObject = {
            "context_pack_id": context_pack_id,
            "query_interpretation": interpretation,
            # Compact references only; the full rows appear once, in
            # relevant_memories.
            "current_known_state": [_memory_reference(item) for item in selected_memories],
            "relevant_memories": selected_memories,
            "relevant_beliefs": [item for item in selected_memories if item.get("memory_type") in {"belief", "thesis"}],
            "decisions": [item for item in selected_memories if item.get("memory_type") == "decision"],
            "procedures": [item for item in selected_memories if item.get("memory_type") in {"procedure", "routine"}],
            "open_loops": selected_open_loops,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": contradicting_evidence,
            "recent_changes": recent_changes,
            "missing_information": self._missing_information(selected_memories, selected_sources),
            "sources": selected_sources,
            "warnings": warnings,
            "budget": budget.to_record(),
            "trace_id": trace_id,
            "trace": trace,
            "agent_identity": request.agent_identity,
            "policy_decision": request.policy_decision,
        }
        append_event(
            self.store,
            event_type="retrieval.context_pack_compiled",
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            target_type="context_pack",
            target_id=context_pack_id,
            trace_id=trace_id,
            run_id=request.run_id,
            payload={
                "query": request.query,
                "query_type": interpretation["query_type"],
                "candidate_count": trace["candidate_count"],
                "selected_count": trace["selected_count"],
                "vector_stage": vector_stage,
                "budget": budget.to_record(),
                "warnings": warnings,
                "agent_identity": request.agent_identity,
                "policy_decision": request.policy_decision,
            },
        )
        if request.actor_type == "agent" and request.actor_id is not None:
            append_event(
                self.store,
                event_type="agent.context_pack_requested",
                actor_type="agent",
                actor_id=request.actor_id,
                target_type="context_pack",
                target_id=context_pack_id,
                trace_id=trace_id,
                run_id=request.run_id,
                payload={
                    "query": request.query,
                    "query_type": interpretation["query_type"],
                    "selected_count": trace["selected_count"],
                    "agent_identity": request.agent_identity,
                    "policy_decision": request.policy_decision,
                },
            )
        return pack

    def _contradicting_evidence(
        self,
        memories: list[JsonObject],
        *,
        requested: bool,
        domains: list[str],
        sensitivity_allowed: list[str],
    ) -> tuple[list[JsonObject], str]:
        """Contradiction candidates between the selected memories and active beliefs.

        Reuses the pure detection helpers behind VNextContradictionService
        without persisting edges, artifacts, or events (read-only path).
        Stores without ``list_beliefs`` (e.g. the SQLite on-ramp) degrade
        to an empty section with an honest stage status.
        """
        if not requested:
            return [], CONTRADICTIONS_STAGE_NOT_REQUESTED
        list_beliefs = getattr(self.store, "list_beliefs", None)
        if not callable(list_beliefs):
            return [], CONTRADICTIONS_STAGE_NO_STORE_SUPPORT
        limit = vnext_contradictions.DEFAULT_CONTRADICTION_LIMIT
        new_items = [memory for memory in memories if memory.get("memory_type") not in {"belief", "thesis"}]
        if not new_items:
            return [], CONTRADICTIONS_STAGE_ENABLED
        beliefs = list_beliefs(
            status="active",
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=max(limit * 2, limit),
        )
        candidates = vnext_contradictions._find_candidates(  # noqa: SLF001 - deliberate read-only reuse
            new_items=new_items,
            beliefs=list(beliefs),
            limit=limit,
        )
        return [candidate.to_record() for candidate in candidates], CONTRADICTIONS_STAGE_ENABLED

    def _recent_changes(self, *, limit: int = DEFAULT_RECENT_CHANGES_LIMIT) -> list[JsonObject]:
        """Most recent ``memory.*`` events from the store event log."""
        list_events = getattr(self.store, "list_events", None)
        if not callable(list_events):
            return []
        # Fetch a few extra rows: memory-targeted events that are not
        # memory.* (e.g. provenance_link.created) are filtered out below.
        events = list_events(target_type="memory", limit=limit * 4)
        changes: list[JsonObject] = []
        for event in events:
            event_type = str(event.get("event_type") or "")
            if not event_type.startswith("memory."):
                continue
            changes.append(
                {
                    "event_id": str(event.get("id")),
                    "event_type": event_type,
                    "target_id": event.get("target_id"),
                    "occurred_at": event.get("occurred_at"),
                    "actor_type": event.get("actor_type"),
                }
            )
            if len(changes) >= limit:
                break
        return changes

    def _supporting_evidence(self, memories: list[JsonObject]) -> list[JsonObject]:
        evidence: list[JsonObject] = []
        for memory in memories:
            memory_id = str(memory.get("id"))
            for link in self.store.list_provenance_links(target_type="memory", target_id=memory_id):
                evidence.append(
                    {
                        "target_type": "memory",
                        "target_id": memory_id,
                        "source_id": link.get("source_id"),
                        "source_chunk_id": link.get("source_chunk_id"),
                        "quote": link.get("quote"),
                        "evidence_role": link.get("evidence_role"),
                        "confidence": link.get("confidence"),
                    }
                )
        return evidence

    @staticmethod
    def _warnings(
        *,
        memory_candidates: list[RetrievalCandidate],
        source_candidates: list[RetrievalCandidate],
        open_loop_candidates: list[RetrievalCandidate],
    ) -> list[str]:
        candidates = [*memory_candidates, *source_candidates, *open_loop_candidates]
        warnings: list[str] = []
        if not any(candidate.selected for candidate in memory_candidates):
            warnings.append("no_relevant_memories_selected")
        if any(candidate.exclusion_reason == "sensitivity_filtered" for candidate in candidates):
            warnings.append("sensitive_items_filtered")
        if any(candidate.exclusion_reason == "domain_filtered" for candidate in candidates):
            warnings.append("domain_items_filtered")
        return warnings

    @staticmethod
    def _missing_information(memories: list[JsonObject], sources: list[JsonObject]) -> list[JsonObject]:
        missing: list[JsonObject] = []
        if not memories:
            missing.append({"kind": "memory", "reason": "No matching memory was selected."})
        if not sources:
            missing.append({"kind": "source", "reason": "No matching source was selected."})
        return missing


__all__ = [
    "CONTRADICTIONS_STAGE_ENABLED",
    "CONTRADICTIONS_STAGE_NOT_REQUESTED",
    "CONTRADICTIONS_STAGE_NO_STORE_SUPPORT",
    "DEFAULT_CONTEXT_PACK_LIMIT",
    "DEFAULT_RECENT_CHANGES_LIMIT",
    "DEFAULT_SENSITIVITY_ALLOWED",
    "EXCLUSION_REASON_TOKEN_BUDGET",
    "RRF_K",
    "STALENESS_NOTE_AFTER_DAYS",
    "TOKEN_ESTIMATE_CHARS_PER_TOKEN",
    "VECTOR_STAGE_DISABLED_NO_PROVIDER",
    "VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT",
    "VECTOR_STAGE_ENABLED",
    "VNextRetrievalRequest",
    "VNextRetrievalService",
    "VNextRetrievalStore",
    "VNextRetrievalValidationError",
    "classify_query",
    "estimate_item_tokens",
    "normalize_query",
    "query_terms",
    "reciprocal_rank_fusion",
]
