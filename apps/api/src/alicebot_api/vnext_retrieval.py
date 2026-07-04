from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Protocol, Sequence
from uuid import uuid4

from alicebot_api.vnext_embeddings import (
    EmbeddingProvider,
    VNextEmbeddingConfigurationError,
    VNextEmbeddingProviderError,
    get_embedding_provider,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


DEFAULT_CONTEXT_PACK_LIMIT = 8
DEFAULT_SOURCE_LIMIT = 8
DEFAULT_OPEN_LOOP_LIMIT = 8
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
STRATEGIC_QUERY_TYPES = {"strategic_synthesis", "contradiction_check", "project_status", "agent_context"}
RRF_K = 60
VECTOR_STAGE_ENABLED = "enabled"
VECTOR_STAGE_DISABLED_NO_PROVIDER = "disabled: no embedding provider configured"
VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT = "disabled: store does not support vector search"


class VNextRetrievalValidationError(ValueError):
    """Raised when a vNext retrieval request is invalid."""


class VNextRetrievalStore(Protocol):
    """Minimum store surface for context-pack retrieval.

    Stores may additionally expose ``search_memories_fts`` and
    ``search_memories_vector`` (see ``PostgresVNextStore``); the service
    detects them at runtime and degrades to ``search_memories`` otherwise.
    """

    def append_event(self, event: JsonObject) -> JsonObject: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONTEXT_PACK_LIMIT,
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
    time_window: str = "all"
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    include_sources: bool = True
    include_contradictions: bool = True
    max_items: int = DEFAULT_CONTEXT_PACK_LIMIT
    max_tokens: int = 8_000
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
    ) -> tuple[list[JsonObject], str]:
        search_memories_fts = getattr(self.store, "search_memories_fts", None)
        if callable(search_memories_fts):
            rows = search_memories_fts(
                query=query,
                domains=domains or None,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit,
            )
            return list(rows), "postgres_fts"
        rows = self.store.search_memories(
            query=query,
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=limit,
        )
        return list(rows), "store_lexical"

    def _memory_vector_rows(
        self,
        *,
        query: str,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
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
            )
        except (VNextEmbeddingConfigurationError, VNextEmbeddingProviderError) as exc:
            return [], f"disabled: query embedding failed ({exc})"
        return list(rows), VECTOR_STAGE_ENABLED

    def compile_context_pack(self, request: VNextRetrievalRequest) -> JsonObject:
        interpretation = classify_query(request)
        terms = list(interpretation["terms"])  # type: ignore[arg-type]
        domains = list(interpretation["domains"])  # type: ignore[arg-type]
        sensitivity_allowed = list(interpretation["sensitivity_allowed"])  # type: ignore[arg-type]
        trace_id = request.trace_id or str(uuid4())
        context_pack_id = str(uuid4())
        memory_candidate_limit = max(request.max_items * 2, request.max_items)

        fts_rows, fts_source = self._memory_fts_rows(
            query=request.query,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=memory_candidate_limit,
        )
        vector_rows, vector_stage = self._memory_vector_rows(
            query=str(interpretation["query"]),
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=memory_candidate_limit,
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
        supporting_evidence = self._supporting_evidence(selected_memories)
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
            },
            "fusion": {"algorithm": "reciprocal_rank_fusion", "k": RRF_K},
            "vector_stage": vector_stage,
            "stages": {
                "fts": {"source": fts_source, "candidate_count": len(fts_rows)},
                "vector": {"status": vector_stage, "candidate_count": len(vector_rows)},
                "sources": {"source": "store_lexical", "candidate_count": len(source_rows)},
                "open_loops": {"candidate_count": len(open_loop_rows)},
            },
            "selected": selected_trace,
            "excluded_counts": excluded_counts,
        }
        pack: JsonObject = {
            "context_pack_id": context_pack_id,
            "query_interpretation": interpretation,
            "current_known_state": selected_memories[:3],
            "relevant_memories": selected_memories,
            "relevant_beliefs": [item for item in selected_memories if item.get("memory_type") in {"belief", "thesis"}],
            "decisions": [item for item in selected_memories if item.get("memory_type") == "decision"],
            "open_loops": selected_open_loops,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": [],
            "recent_changes": [],
            "historical_timeline": [],
            "missing_information": self._missing_information(selected_memories, selected_sources),
            "sources": selected_sources,
            "warnings": warnings,
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
    "DEFAULT_CONTEXT_PACK_LIMIT",
    "DEFAULT_SENSITIVITY_ALLOWED",
    "RRF_K",
    "VECTOR_STAGE_DISABLED_NO_PROVIDER",
    "VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT",
    "VECTOR_STAGE_ENABLED",
    "VNextRetrievalRequest",
    "VNextRetrievalService",
    "VNextRetrievalStore",
    "VNextRetrievalValidationError",
    "classify_query",
    "normalize_query",
    "query_terms",
    "reciprocal_rank_fusion",
]
