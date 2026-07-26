from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import itertools
import json
import re
import sqlite3
from typing import Mapping
from uuid import UUID, uuid4

import pytest

from alicebot_api import vnext_retrieval as vnext_retrieval_module
from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_embeddings import VNextEmbeddingProviderError
from alicebot_api.vnext_occurrence_predicates import (
    OCCURRENCE_AGGREGATION_SCHEMA,
    occurrence_coverage_review_receipt_digest,
    occurrence_evidence_facts_digest,
    occurrence_evidence_review_receipt_digest,
    occurrence_unit_review_receipt_digest,
)
from alicebot_api.vnext_occurrence_taxonomy import (
    build_occurrence_predicate_atom,
)
from alicebot_api.vnext_project_scope import memory_project_scope
from alicebot_api.vnext_retrieval import (
    BUDGET_STRATEGIES,
    CONTEXT_DEPTHS,
    CONTEXT_DEPTH_MINIMAL_MAX_ITEMS,
    CONTRADICTIONS_STAGE_ENABLED,
    CONTRADICTIONS_STAGE_NOT_REQUESTED,
    CONTRADICTIONS_STAGE_NO_STORE_SUPPORT,
    ENTITY_NAME_CANDIDATE_LIMIT,
    EXCLUSION_REASON_TOKEN_BUDGET,
    GRAPH_ENTITY_MATCH_LIMIT,
    GRAPH_STAGE_DISABLED_NO_ENTITY_MATCH,
    GRAPH_STAGE_DISABLED_NO_STORE_SUPPORT,
    GRAPH_STAGE_ENABLED,
    LEGACY_SCOPED_SCAN_MAX_ROWS,
    RRF_K,
    SOURCES_STAGE_DISABLED_BY_FLAG,
    SOURCE_CHUNK_STAGE_DISABLED_NO_STORE_SUPPORT,
    SOURCE_STAGE_TEMPORAL,
    STAGE_DISABLED_MINIMAL,
    STALENESS_NOTE_AFTER_DAYS,
    SUPERSESSION_STAGE_ENABLED,
    TEMPORAL_STAGE_DISABLED_NO_STORE_SUPPORT,
    TEMPORAL_STAGE_ENABLED,
    TIE_BREAK_CONTENT_STABLE,
    VECTOR_STAGE_DISABLED_NO_PROVIDER,
    VECTOR_STAGE_DISABLED_QUERY_EMBEDDING_FAILED,
    VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest,
    VNextRetrievalCompletenessError,
    VNextRetrievalService,
    VNextRetrievalValidationError,
    classify_query,
    entity_name_candidates,
    estimate_item_tokens,
    query_terms,
    reciprocal_rank_fusion,
)


_UNSET = object()
_OCCURRENCE_TEST_SOURCE_ID = "11111111-1111-4111-8111-111111111111"
_OCCURRENCE_TEST_CHUNK_ID = "22222222-2222-4222-8222-222222222222"
_OCCURRENCE_TEST_DISPOSITION_ID = "33333333-3333-4333-8333-333333333333"
_OCCURRENCE_TEST_EXTRACTOR_VERSION = "retrieval-reader-test-v1"


@pytest.fixture(autouse=True)
def _clear_embedding_env(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)


class StubEmbeddingProvider:
    provider = "stub"
    model = "stub-embedding"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.embedded_texts: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        if self.fail:
            raise VNextEmbeddingProviderError("embeddings endpoint returned HTTP 500")
        self.embedded_texts.append(text)
        return [0.1] * 1536

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


class StubRerankProvider:
    provider = "stub"
    model = "stub-reranker"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete(
        self,
        prompt: str,
    ) -> vnext_retrieval_module.vnext_reranker.RerankCompletion:
        self.prompts.append(prompt)
        count_match = re.search(
            r"JSON array of (\d+) integers",
            prompt,
        )
        assert count_match is not None
        count = int(count_match.group(1))
        return vnext_retrieval_module.vnext_reranker.RerankCompletion(
            content=json.dumps([50] * count),
        )


class InMemoryVNextRetrievalStore:
    def __init__(
        self,
        *,
        memories: list[dict[str, object]],
        sources: list[dict[str, object]],
        open_loops: list[dict[str, object]] | None = None,
        provenance_links: list[dict[str, object]] | None = None,
        vector_memories: list[dict[str, object]] | None = None,
        beliefs: list[dict[str, object]] | None = None,
        seeded_events: list[dict[str, object]] | None = None,
        entities: list[dict[str, object]] | None = None,
        edges: list[dict[str, object]] | None = None,
        source_chunks: list[dict[str, object]] | None = None,
    ) -> None:
        self.memories = memories
        self.sources = sources
        self.open_loops = open_loops or []
        self.provenance_links = provenance_links or []
        self.vector_memories = vector_memories
        self.beliefs = beliefs
        self.entities = entities or []
        self.edges = edges or []
        self.source_chunks = source_chunks or []
        self.events: list[dict[str, object]] = list(seeded_events or [])
        self.memory_search_domains: object = _UNSET
        self.source_search_domains: object = _UNSET
        self.open_loop_domains: object = _UNSET
        self.memory_search_kwargs: list[dict[str, object]] = []
        self.fts_match_any_queries: list[str] = []
        self.chunk_match_any_queries: list[str] = []
        self.time_search_calls: list[dict[str, object]] = []
        self.fts_limits: list[int] = []
        self.vector_limits: list[int] = []
        self.memory_bulk_reads = 0

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def _memory_text(self, row: dict[str, object]) -> str:
        parts = [row.get(key) for key in ("title", "canonical_text", "summary")]
        return " ".join(part for part in parts if isinstance(part, str)).casefold()

    def _apply_filters(
        self,
        rows: list[dict[str, object]],
        *,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
    ) -> list[dict[str, object]]:
        if memory_types:
            rows = [row for row in rows if row.get("memory_type") in memory_types]
        if projects:
            rows = [row for row in rows if set(memory_project_scope(row)).intersection(projects)]
        if created_by_agent_ids:
            rows = [row for row in rows if row.get("created_by_agent_id") in created_by_agent_ids]
        if run_id is not None:
            rows = [row for row in rows if row.get("run_id") == run_id]
        return rows

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
    ) -> list[dict[str, object]]:
        del query, sensitivity_allowed, include_expired
        self.memory_search_domains = domains
        rows = self._apply_filters(
            self.memories,
            memory_types=memory_types,
            projects=projects,
            created_by_agent_ids=created_by_agent_ids,
            run_id=run_id,
        )
        return rows[:limit]

    def search_memories_fts(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
        match_any: bool = False,
    ) -> list[dict[str, object]]:
        del sensitivity_allowed, include_expired
        self.fts_limits.append(limit)
        if match_any:
            self.fts_match_any_queries.append(query)
        self.memory_search_domains = domains
        self.memory_search_kwargs.append(
            {
                "memory_types": memory_types,
                "projects": projects,
                "created_by_agent_ids": created_by_agent_ids,
                "run_id": run_id,
            }
        )
        terms = [term.casefold() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+", query)]
        rows = [row for row in self.memories if any(term in self._memory_text(row) for term in terms)]
        rows = self._apply_filters(
            rows,
            memory_types=memory_types,
            projects=projects,
            created_by_agent_ids=created_by_agent_ids,
            run_id=run_id,
        )
        return rows[:limit]

    def search_memories_vector(
        self,
        *,
        query_vector: list[float],
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
    ) -> list[dict[str, object]]:
        del query_vector, domains, sensitivity_allowed, include_expired
        self.vector_limits.append(limit)
        if self.vector_memories is None:
            return []
        rows = self._apply_filters(
            self.vector_memories,
            memory_types=memory_types,
            projects=projects,
            created_by_agent_ids=created_by_agent_ids,
            run_id=run_id,
        )
        return rows[:limit]

    def search_memories_by_time(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        window_center: datetime | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed, include_expired
        self.time_search_calls.append({"window_start": window_start, "window_end": window_end})
        center = window_center if window_center is not None else window_start + (window_end - window_start) / 2
        dated: list[tuple[float, str, dict[str, object]]] = []
        for row in self.memories:
            raw = row.get("valid_from") or row.get("first_seen_at") or row.get("created_at")
            if not isinstance(raw, str):
                continue
            event = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if event.tzinfo is None:
                event = event.replace(tzinfo=UTC)
            if not (window_start <= event < window_end):
                continue
            dated.append((abs((event - center).total_seconds()), str(row.get("id")), row))
        dated.sort(key=lambda entry: (entry[0], entry[1]))
        rows = self._apply_filters(
            [row for _distance, _row_id, row in dated],
            memory_types=memory_types,
            projects=projects,
            created_by_agent_ids=created_by_agent_ids,
            run_id=run_id,
        )
        return rows[:limit]

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        rows = [
            event
            for event in reversed(self.events)
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]
        return rows[:limit] if limit is not None else rows

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        rows = [row for row in (self.beliefs or []) if status is None or row.get("status") == status]
        return rows[:limit]

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del query, sensitivity_allowed
        self.source_search_domains = domains
        return self.sources[:limit]

    def get_source(self, source_id: str) -> dict[str, object] | None:
        for row in self.sources:
            if str(row.get("id")) == source_id:
                return row
        return None

    def get_memories_by_ids(self, memory_ids: tuple[str, ...]) -> list[dict[str, object]]:
        self.memory_bulk_reads += 1
        wanted = set(memory_ids)
        return [row for row in [*self.memories, *(self.vector_memories or [])] if str(row.get("id")) in wanted]

    def search_source_chunks(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        match_any: bool = False,
    ) -> list[dict[str, object]]:
        del domains, sensitivity_allowed
        if match_any:
            self.chunk_match_any_queries.append(query)
        terms = [term.casefold() for term in re.findall(r"\w+", query)]
        rows: list[dict[str, object]] = []
        for chunk in self.source_chunks:
            text = str(chunk.get("text") or "").casefold()
            matched = (
                any(term in text for term in terms) if match_any else terms and all(term in text for term in terms)
            )
            if matched:
                rows.append(chunk)
        return rows[:limit]

    def list_source_chunks(self, source_id: str) -> list[dict[str, object]]:
        return [chunk for chunk in self.source_chunks if str(chunk.get("source_id")) == str(source_id)]

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del sensitivity_allowed
        self.open_loop_domains = domains
        rows = [row for row in self.open_loops if status is None or row.get("status") == status]
        return rows[:limit]

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[dict[str, object]]:
        return [
            link
            for link in self.provenance_links
            if link.get("target_type") == target_type and link.get("target_id") == target_id
        ]

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[dict[str, object]]:
        return [
            edge
            for edge in self.edges
            if (from_id is None or edge.get("from_id") == from_id)
            and (to_id is None or edge.get("to_id") == to_id)
            and edge.get("valid_to") is None
        ]

    def get_memory(self, memory_id: str) -> dict[str, object] | None:
        for row in [*self.memories, *(self.vector_memories or [])]:
            if str(row.get("id")) == memory_id:
                return row
        return None

    def find_entities_by_names(self, normalized_names: tuple[str, ...]) -> list[dict[str, object]]:
        names = set(normalized_names)
        matched = [
            entity
            for entity in self.entities
            if entity.get("normalized_name") in names or any(alias in names for alias in entity.get("aliases", []))
        ]
        return sorted(matched, key=lambda entity: -int(entity.get("mention_count", 0) or 0))


def _memory_row(memory_id: str, text: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": memory_id,
        "memory_type": "semantic",
        "canonical_text": text,
        "status": "active",
        "confidence": 0.8,
        "domain": "project",
        "sensitivity": "private",
    }
    row.update(overrides)
    return row


def test_query_classifier_identifies_sprint3_query_shapes() -> None:
    interpretation = classify_query(
        VNextRetrievalRequest(
            query="What contradictions are blocking the Alice project status?",
            domains=("project",),
            sensitivity_allowed=("public", "private"),
        )
    )

    assert interpretation["query_type"] == "contradiction_check"
    assert interpretation["domains"] == ["project"]
    assert interpretation["sensitivity_allowed"] == ["public", "private"]
    assert interpretation["requires_sources"] is True
    assert interpretation["requires_contradictions"] is True
    assert "alice" in query_terms("What should Alice retrieve about Alice?")


def test_query_classifier_does_not_hard_scope_ambiguous_business_money_query() -> None:
    query = "where did the advertising money move away from adwords"

    inferred = classify_query(VNextRetrievalRequest(query=query))
    explicit = classify_query(VNextRetrievalRequest(query=query, domains=("personal",)))

    assert inferred["domains"] == []
    assert explicit["domains"] == ["personal"]


def test_inferred_domains_are_disclosed_but_never_used_as_hard_filters() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-legal",
                "Legal approved the updated data processing agreement.",
                domain="professional",
            )
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="What did legal approve for data processing?")
    )

    assert pack["query_interpretation"]["domains"] == []
    assert pack["query_interpretation"]["inferred_domains"] == ["personal"]
    assert store.memory_search_domains is None
    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-legal"]


def test_domain_inference_uses_word_boundaries() -> None:
    assert classify_query(VNextRetrievalRequest(query="prevent malice in the queue"))["inferred_domains"] == []
    assert classify_query(VNextRetrievalRequest(query="review the illegal campaign"))["inferred_domains"] == []


def test_reciprocal_rank_fusion_scores_and_orders_candidates() -> None:
    row_a = {"id": "a"}
    row_b = {"id": "b"}
    row_c = {"id": "c"}

    fused = reciprocal_rank_fusion({"fts": [row_a, row_b], "vector": [row_b, row_c]}, k=60)

    by_id = {str(item["id"]): (score, stage_ranks) for item, score, stage_ranks in fused}
    assert by_id["a"][0] == pytest.approx(1.0 / 61.0)
    assert by_id["b"][0] == pytest.approx(1.0 / 62.0 + 1.0 / 61.0)
    assert by_id["c"][0] == pytest.approx(1.0 / 62.0)
    assert [str(item["id"]) for item, _score, _ranks in fused] == ["b", "a", "c"]
    assert by_id["b"][1] == {"fts": 2, "vector": 1}
    assert by_id["a"][1] == {"fts": 1}
    assert by_id["c"][1] == {"vector": 2}


def test_reciprocal_rank_fusion_breaks_ties_deterministically() -> None:
    fused = reciprocal_rank_fusion({"fts": [{"id": "b"}], "vector": [{"id": "a"}]}, k=60)

    assert [str(item["id"]) for item, _score, _ranks in fused] == ["a", "b"]


def test_context_pack_includes_memories_sources_open_loops_provenance_and_trace() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-1",
                "Alice vNext uses provenance first retrieval.",
                memory_type="decision",
                confidence=0.92,
                first_seen_at="2026-05-10T00:00:00Z",
                last_seen_at="2026-05-10T00:00:00Z",
                metadata_json={},
            )
        ],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Alice provenance note",
                "content_hash": "sha256:abc",
                "captured_at": "2026-05-10T00:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {},
            }
        ],
        open_loops=[
            {
                "id": "loop-1",
                "title": "Validate Alice retrieval trace",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
        provenance_links=[
            {
                "id": "link-1",
                "target_type": "memory",
                "target_id": "memory-1",
                "source_id": "source-1",
                "source_chunk_id": "chunk-1",
                "quote": "Alice vNext uses provenance first retrieval.",
                "evidence_role": "quoted_from",
                "confidence": 0.9,
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice provenance retrieval", domains=("project",), max_items=4)
    )

    assert pack["query_interpretation"]["query_type"] == "strategic_synthesis"
    assert pack["relevant_memories"][0]["id"] == "memory-1"
    assert pack["sources"][0]["id"] == "source-1"
    assert pack["open_loops"][0]["id"] == "loop-1"
    assert pack["decisions"][0]["id"] == "memory-1"
    assert pack["procedures"] == []
    assert pack["contradicting_evidence"] == []
    assert pack["recent_changes"] == []
    # historical_timeline was removed from the pack schema.
    assert "historical_timeline" not in pack
    # current_known_state is a compact reference list, not duplicate rows.
    assert pack["current_known_state"] == [
        {"id": "memory-1", "title": "Alice vNext uses provenance first retrieval.", "memory_type": "decision"}
    ]
    # No token budget requested: estimate is still reported, nothing dropped.
    assert pack["budget"]["token_budget"] is None
    assert pack["budget"]["token_estimate"] > 0
    assert pack["budget"]["truncated"] is False
    assert pack["budget"]["dropped_item_count"] == 0
    assert pack["supporting_evidence"] == [
        {
            "target_type": "memory",
            "target_id": "memory-1",
            "source_id": "source-1",
            "source_chunk_id": "chunk-1",
            "quote": "Alice vNext uses provenance first retrieval.",
            "evidence_role": "quoted_from",
            "confidence": 0.9,
        }
    ]
    assert pack["trace_id"] == pack["trace"]["trace_id"]
    assert pack["trace"]["candidate_count"] == 3
    assert pack["trace"]["selected_count"] == 3
    assert pack["trace"]["vector_stage"] == VECTOR_STAGE_DISABLED_NO_PROVIDER
    assert pack["trace"]["fusion"] == {
        "algorithm": "reciprocal_rank_fusion",
        "k": RRF_K,
        "tie_break": TIE_BREAK_CONTENT_STABLE,
    }
    assert pack["trace"]["stages"]["fts"] == {"source": "postgres_fts", "candidate_count": 1}
    assert pack["trace"]["stages"]["vector"] == {
        "status": VECTOR_STAGE_DISABLED_NO_PROVIDER,
        "candidate_count": 0,
    }
    memory_trace = [record for record in pack["trace"]["selected"] if record["target_type"] == "memory"]
    assert memory_trace[0]["stage_ranks"] == {"fts": 1}
    assert store.events[-1]["event_type"] == "retrieval.context_pack_compiled"
    assert store.events[-1]["trace_id"] == pack["trace_id"]


def test_context_pack_fuses_vector_results_with_rrf_when_provider_is_configured() -> None:
    memory_a = _memory_row("memory-a", "Alice retrieval ranking test alpha.")
    memory_b = _memory_row("memory-b", "Alice retrieval ranking test beta.")
    memory_c = _memory_row("memory-c", "Semantically related but lexically distant.")
    store = InMemoryVNextRetrievalStore(
        memories=[memory_a, memory_b],
        sources=[],
        vector_memories=[memory_b, memory_c],
    )
    provider = StubEmbeddingProvider()

    pack = VNextRetrievalService(store, embedding_provider=provider).compile_context_pack(
        VNextRetrievalRequest(query="Alice retrieval ranking", domains=("project",), max_items=4)
    )

    assert provider.embedded_texts == ["Alice retrieval ranking"]
    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-b", "memory-a", "memory-c"]
    assert pack["trace"]["vector_stage"] == VECTOR_STAGE_ENABLED
    assert pack["trace"]["stages"]["vector"] == {"status": VECTOR_STAGE_ENABLED, "candidate_count": 2}
    memory_trace = [record for record in pack["trace"]["selected"] if record["target_type"] == "memory"]
    assert memory_trace[0]["target_id"] == "memory-b"
    assert memory_trace[0]["stage_ranks"] == {"fts": 2, "vector": 1}
    assert memory_trace[0]["rrf_score"] == pytest.approx(1.0 / 62.0 + 1.0 / 61.0, abs=1e-6)


def test_context_pack_degrades_to_fts_when_query_embedding_fails() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Alice retrieval fallback check.")],
        sources=[],
        vector_memories=[_memory_row("memory-2", "Never returned because embed fails.")],
    )

    pack = VNextRetrievalService(store, embedding_provider=StubEmbeddingProvider(fail=True)).compile_context_pack(
        VNextRetrievalRequest(query="Alice retrieval fallback", domains=("project",))
    )

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-1"]
    assert pack["trace"]["vector_stage"] == VECTOR_STAGE_DISABLED_QUERY_EMBEDDING_FAILED
    assert pack["trace"]["stages"]["vector"]["candidate_count"] == 0


def test_context_pack_filters_sensitive_memories_and_records_trace_exclusion() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-public",
                "Alice retrieval is public enough to show.",
                sensitivity="public",
                first_seen_at="2026-05-10T00:00:00Z",
                last_seen_at="2026-05-10T00:00:00Z",
            ),
            _memory_row(
                "memory-secret",
                "Alice retrieval secret should be filtered.",
                sensitivity="highly_sensitive",
                first_seen_at="2026-05-10T00:00:00Z",
                last_seen_at="2026-05-10T00:00:00Z",
            ),
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="Alice retrieval",
            domains=("project",),
            sensitivity_allowed=("public",),
        )
    )

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-public"]
    assert "sensitive_items_filtered" in pack["warnings"]
    assert pack["trace"]["excluded_counts"] == {"sensitivity_filtered": 1}
    assert [record["target_id"] for record in pack["trace"]["selected"]] == ["memory-public"]


def test_unscoped_query_does_not_filter_to_unknown_domain() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-personal",
                "Coffee preference is pour over.",
                domain="personal",
            )
        ],
        sources=[
            {
                "id": "source-personal",
                "source_type": "manual_text",
                "title": "Coffee preference",
                "content_hash": "sha256:coffee",
                "domain": "personal",
                "sensitivity": "private",
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="coffee preference"))

    assert pack["query_interpretation"]["domains"] == []
    assert store.memory_search_domains is None
    assert store.source_search_domains is None
    assert store.open_loop_domains is None
    assert pack["relevant_memories"][0]["id"] == "memory-personal"


def test_grounding_runtime_failure_does_not_abort_context_pack_but_baseexception_does(
    monkeypatch,
) -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Marcus Chen approved the launch.")],
        sources=[],
    )

    monkeypatch.setattr(
        vnext_retrieval_module,
        "compute_query_grounding",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("probe failed")),
    )
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Did Marcus Chen approve the launch?")
    )
    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-1"]
    assert "grounding" not in pack

    class ProbeCancelled(BaseException):
        pass

    monkeypatch.setattr(
        vnext_retrieval_module,
        "compute_query_grounding",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ProbeCancelled("cancelled")),
    )
    with pytest.raises(ProbeCancelled, match="cancelled"):
        VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(query="Did Marcus Chen approve the launch?")
        )


def test_context_pack_records_missing_information_when_no_candidates_match() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-1",
                "Unrelated note",
                domain="unknown",
                sensitivity="public",
                first_seen_at="2026-05-10T00:00:00Z",
                last_seen_at="2026-05-10T00:00:00Z",
            )
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice provenance"))

    assert pack["relevant_memories"] == []
    assert {"kind": "memory", "reason": "No matching memory was selected."} in pack["missing_information"]
    assert "no_relevant_memories_selected" in pack["warnings"]


# -- token budget -----------------------------------------------------------------


def test_context_pack_enforces_max_tokens_with_greedy_packing_and_traces_drops() -> None:
    memories = [
        _memory_row(f"memory-{index}", f"Alice retrieval budget item number {index} with padding text.")
        for index in range(1, 5)
    ]
    store = InMemoryVNextRetrievalStore(memories=memories, sources=[])
    service = VNextRetrievalService(store)

    # Budget that fits exactly the first two memories and nothing more.
    first_two_cost = sum(
        estimate_item_tokens({key: value for key, value in row.items() if key != "deleted_at"}) for row in memories[:2]
    )
    pack = service.compile_context_pack(
        VNextRetrievalRequest(query="Alice retrieval budget", max_items=8, max_tokens=first_two_cost)
    )

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-1", "memory-2"]
    assert pack["budget"]["token_budget"] == first_two_cost
    assert pack["budget"]["token_estimate"] <= first_two_cost
    assert pack["budget"]["truncated"] is True
    assert pack["budget"]["dropped_item_count"] == 2
    assert pack["trace"]["budget"] == pack["budget"]
    assert pack["trace"]["excluded_counts"][EXCLUSION_REASON_TOKEN_BUDGET] == 2
    assert pack["trace"]["selected_count"] == 2
    assert [record["target_id"] for record in pack["trace"]["selected"]] == ["memory-1", "memory-2"]
    assert pack["current_known_state"] == [
        {"id": "memory-1", "title": memories[0]["canonical_text"], "memory_type": "semantic"},
        {"id": "memory-2", "title": memories[1]["canonical_text"], "memory_type": "semantic"},
    ]


def test_context_pack_budget_packs_sections_in_priority_order() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Alice budget priority memory row.")],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Alice budget priority source",
                "content_hash": "sha256:abc",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
        open_loops=[
            {
                "id": "loop-1",
                "title": "Alice budget priority loop",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
    )
    memory_cost = estimate_item_tokens(_memory_row("memory-1", "Alice budget priority memory row."))
    loop_cost = estimate_item_tokens(
        {
            "id": "loop-1",
            "title": "Alice budget priority loop",
            "status": "open",
            "domain": "project",
            "sensitivity": "private",
        }
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice budget priority", max_tokens=memory_cost + loop_cost)
    )

    # Memories pack first, open loops second; the source no longer fits.
    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-1"]
    assert [loop["id"] for loop in pack["open_loops"]] == ["loop-1"]
    assert pack["sources"] == []
    assert pack["budget"]["truncated"] is True
    assert pack["budget"]["dropped_item_count"] == 1
    source_trace = [record for record in pack["trace"]["selected"] if record["target_type"] == "source"]
    assert source_trace == []
    assert pack["trace"]["excluded_counts"][EXCLUSION_REASON_TOKEN_BUDGET] == 1


def test_context_pack_rejects_non_positive_max_tokens() -> None:
    store = InMemoryVNextRetrievalStore(memories=[], sources=[])
    with pytest.raises(ValueError, match="max_tokens"):
        VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice", max_tokens=0))


@pytest.mark.parametrize(
    ("overrides", "field_name"),
    [
        ({"max_items": 0}, "max_items"),
        ({"max_items": 51}, "max_items"),
        ({"max_tokens": 50_001}, "max_tokens"),
        ({"time_window": "forever"}, "time_window"),
        ({"time_window": "0d"}, "time_window"),
    ],
)
def test_context_pack_enforces_authoritative_service_bounds(overrides: dict[str, object], field_name: str) -> None:
    store = InMemoryVNextRetrievalStore(memories=[], sources=[])

    with pytest.raises(VNextRetrievalValidationError, match=field_name):
        VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(query="Alice", **overrides)  # type: ignore[arg-type]
        )


def test_context_pack_counts_recent_changes_inside_the_content_budget() -> None:
    memory = _memory_row("memory-1", "Alice recent-change budget row.")
    seeded_event = {
        "id": "event-1",
        "event_type": "memory.updated",
        "actor_type": "system",
        "target_type": "memory",
        "target_id": "memory-1",
        "occurred_at": "2026-07-01T00:00:00Z",
    }
    store = InMemoryVNextRetrievalStore(memories=[memory], sources=[], seeded_events=[seeded_event])
    memory_only_budget = estimate_item_tokens(memory)

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="Alice recent-change budget",
            max_tokens=memory_only_budget,
        )
    )

    assert [item["id"] for item in pack["relevant_memories"]] == ["memory-1"]
    assert pack["recent_changes"] == []
    assert pack["budget"]["allocation"]["recent_changes"] == 0
    assert pack["budget"]["token_estimate"] <= memory_only_budget
    assert pack["budget"]["truncated"] is True
    assert "trace" in pack["budget"]["excluded_sections"]
    assert pack["budget"]["serialized_token_estimate"] > pack["budget"]["token_estimate"]
    assert pack["budget"]["serialized_token_estimate"] == estimate_item_tokens(pack)
    assert pack["budget"]["excluded_token_estimate"] == (estimate_item_tokens(pack) - pack["budget"]["token_estimate"])


# -- memory_types and projects filters ---------------------------------------------


def test_context_pack_threads_memory_types_and_projects_to_recall_stages() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row("memory-decision", "Alice filter threading decision.", memory_type="decision"),
            _memory_row("memory-preference", "Alice filter threading preference.", memory_type="preference"),
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="Alice filter threading",
            memory_types=("decision",),
            projects=("alicebot",),
        )
    )

    assert store.memory_search_kwargs[-1] == {
        "memory_types": ("decision",),
        "projects": ("alicebot",),
        "created_by_agent_ids": (),
        "run_id": None,
    }
    assert pack["trace"]["filters"]["memory_types"] == ["decision"]
    assert pack["trace"]["filters"]["projects"] == ["alicebot"]
    assert pack["trace"]["filters"]["created_by_agent_ids"] == []
    assert pack["trace"]["filters"]["run_id"] is None
    assert pack["query_interpretation"]["memory_types"] == ["decision"]


def test_context_pack_omits_filter_kwargs_when_unset_for_minimal_stores() -> None:
    class MinimalStore(InMemoryVNextRetrievalStore):
        def search_memories_fts(self, *, query, domains=None, sensitivity_allowed=None, limit=50):  # type: ignore[override]
            # Legacy signature without memory_types/projects/include_expired.
            return super().search_memories_fts(
                query=query, domains=domains, sensitivity_allowed=sensitivity_allowed, limit=limit
            )

    store = MinimalStore(memories=[_memory_row("memory-1", "Alice minimal store check.")], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice minimal store"))

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-1"]


# -- FTS OR-fallback ---------------------------------------------------------------


def _sqlite_retrieval_store() -> SQLiteVNextStore:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, f"{user_id}@example.com", "Fallback Test")
    return SQLiteVNextStore(conn, user_id)


def _commit_announcement_decision(store: SQLiteVNextStore) -> dict[str, object]:
    return store.create_memory(
        {
            "memory_key": "decision.alice-announcement",
            "memory_type": "decision",
            "title": "Alice public announcement timing",
            "canonical_text": (
                "Decision: Alice public announcement goes out Monday after the pre-launch audit passes."
            ),
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
            "value": {"text": "Alice public announcement goes out Monday."},
        }
    )


def test_natural_language_question_falls_back_to_or_matching_on_sqlite() -> None:
    # The no-embeddings default path: FTS5 ANDs "alice public announcement
    # go" and the stored text says "goes", so the strict pass returns
    # nothing. The OR-fallback must still recall the memory, and the trace
    # must say so.
    store = _sqlite_retrieval_store()
    memory = _commit_announcement_decision(store)

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="When does the Alice public announcement go out?")
    )

    assert [item["id"] for item in pack["relevant_memories"]] == [memory["id"]]
    assert pack["trace"]["stages"]["fts"] == {
        "source": "sqlite_fts_or_fallback",
        "candidate_count": 1,
    }


def test_keyword_query_that_and_matches_does_not_use_the_fallback_on_sqlite() -> None:
    store = _sqlite_retrieval_store()
    memory = _commit_announcement_decision(store)

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice announcement"))

    assert [item["id"] for item in pack["relevant_memories"]] == [memory["id"]]
    assert pack["trace"]["stages"]["fts"] == {"source": "sqlite_fts", "candidate_count": 1}


def test_count_candidate_statistic_uses_real_sqlite_fts_mode_and_provenance_dedup() -> None:
    store = _sqlite_retrieval_store()
    provenance = (
        ("record-1", "source-a", "chunk-a"),
        ("record-2", "source-a", "chunk-a"),  # restatement of the same captured turn
        ("record-3", "source-b", "chunk-b"),
    )
    for memory_key, source_id, chunk_id in provenance:
        store.create_memory(
            {
                "memory_key": f"memory.{memory_key}",
                "memory_type": "semantic",
                "title": "Bike service record",
                "canonical_text": f"Bike service record {memory_key} was logged.",
                "status": "active",
                "domain": "personal",
                "sensitivity": "private",
                "value": {"text": f"Bike service record {memory_key} was logged."},
                "metadata_json": {
                    "source_id": source_id,
                    "source_chunk_id": chunk_id,
                },
            }
        )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many bike service records are there?",
            domains=("personal",),
        )
    )

    assert pack["trace"]["stages"]["fts"] == {
        "source": "sqlite_fts_or_fallback",
        "candidate_count": 3,
    }
    statistic = pack["trace"]["stages"]["coverage_mode"]["candidate_instance_count"]
    assert statistic["count"] == 2
    assert statistic["fts_source"] == "sqlite_fts_or_fallback"
    assert statistic["deduplication"] == "source_chunk_then_source_then_memory_id"
    assert statistic["rows_examined"] == 3
    assert statistic["candidate_prefix_exhausted"] is True
    assert statistic["more_candidate_groups_may_exist"] is False
    assert statistic["is_answer"] is False
    assert statistic["supports_numeric_sum"] is False
    # The widened OR fallback is useful trace telemetry, never reader-visible
    # aggregation evidence.
    assert "aggregation" not in pack
    assert "aggregation" not in pack["budget"]["allocation"]


def test_strict_count_candidate_statistic_without_selected_rollup_stays_trace_only() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                f"memory-bike-{index}",
                f"Bike service record {index} was completed.",
                metadata_json={"source_id": f"source-{index}", "source_chunk_id": f"chunk-{index}"},
            )
            for index in range(1, 4)
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="How many bike service records are there?")
    )

    statistic = pack["trace"]["stages"]["coverage_mode"]["candidate_instance_count"]
    assert statistic["fts_source"] == "postgres_fts"
    assert statistic["count"] == 3
    assert statistic["candidate_prefix_exhausted"] is True
    assert statistic["more_candidate_groups_may_exist"] is False
    assert "aggregation" not in pack
    assert "aggregation" not in pack["budget"]["allocation"]


def test_single_token_miss_does_not_fire_the_or_fallback() -> None:
    store = InMemoryVNextRetrievalStore(memories=[_memory_row("memory-1", "Unrelated note")], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="kubernetes"))

    assert pack["relevant_memories"] == []
    assert pack["trace"]["stages"]["fts"] == {"source": "postgres_fts", "candidate_count": 0}
    assert store.fts_match_any_queries == []


def test_multi_token_miss_retries_once_with_match_any_and_reports_fallback_source() -> None:
    store = InMemoryVNextRetrievalStore(memories=[_memory_row("memory-1", "Unrelated note")], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="kubernetes deployment pipeline")
    )

    assert store.fts_match_any_queries == ["kubernetes deployment pipeline"]
    assert pack["trace"]["stages"]["fts"] == {
        "source": "postgres_fts_or_fallback",
        "candidate_count": 0,
    }


def test_or_fallback_degrades_cleanly_for_stores_without_match_any() -> None:
    class LegacyStore(InMemoryVNextRetrievalStore):
        def search_memories_fts(  # type: ignore[override]
            self,
            *,
            query,
            domains=None,
            sensitivity_allowed=None,
            limit=50,
            memory_types=(),
            projects=(),
            created_by_agent_ids=(),
            run_id=None,
            include_expired=False,
        ):
            # Legacy signature without match_any.
            return []

    store = LegacyStore(memories=[], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="kubernetes deployment pipeline")
    )

    assert pack["relevant_memories"] == []
    assert pack["trace"]["stages"]["fts"] == {"source": "postgres_fts", "candidate_count": 0}


# -- fused source stage (chunk content + provenance + title/recency) ----------------


def test_source_stage_fuses_chunk_content_provenance_and_title_recency() -> None:
    source_title = {
        "id": "source-title",
        "source_type": "manual_text",
        "title": "Migration cutover checklist",
        "content_hash": "sha256:title",
        "domain": "project",
        "sensitivity": "private",
    }
    source_chunk = {
        "id": "source-chunk",
        "source_type": "chat_session",
        "title": "Untitled session 41",
        "content_hash": "sha256:chunk",
        "domain": "project",
        "sensitivity": "private",
    }
    source_prov = {
        "id": "source-prov",
        "source_type": "document",
        "title": "Import 9f3a4c",
        "content_hash": "sha256:prov",
        "domain": "project",
        "sensitivity": "private",
    }
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Migration cutover decision: Friday night window.")],
        sources=[source_title, source_chunk, source_prov],
        source_chunks=[
            {
                "id": "chunk-1",
                "source_id": "source-chunk",
                "chunk_index": 0,
                "text": "the migration cutover happens Friday night",
            }
        ],
        provenance_links=[
            {
                "id": "link-1",
                "target_type": "memory",
                "target_id": "memory-1",
                "source_id": "source-prov",
                "quote": "Migration cutover decision: Friday night window.",
                "evidence_role": "quoted_from",
                "confidence": 0.9,
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="migration cutover Friday", domains=("project",))
    )

    # RRF: the content hit (chunk_fts rank 1 + title_recency rank 2) beats
    # the provenance source (provenance rank 1 + title_recency rank 3),
    # which beats the lexical-only row (title_recency rank 1 alone).
    assert [item["id"] for item in pack["sources"]] == ["source-chunk", "source-prov", "source-title"]
    # Strict chunk pass matched, so the one-shot OR retry never fired.
    assert store.chunk_match_any_queries == []
    assert pack["trace"]["stages"]["sources"] == {
        "source": "rrf(chunk_fts+provenance+title_recency)",
        "candidate_count": 3,
        "chunk_fts": 1,
        "provenance": 1,
        "title_recency": 3,
        "chunk_fts_source": "postgres_fts",
    }
    source_trace = {
        record["target_id"]: record for record in pack["trace"]["selected"] if record["target_type"] == "source"
    }
    assert source_trace["source-chunk"]["stage_ranks"] == {"chunk_fts": 1, "title_recency": 2}
    assert source_trace["source-prov"]["stage_ranks"] == {"provenance": 1, "title_recency": 3}
    assert source_trace["source-title"]["stage_ranks"] == {"title_recency": 1}


def test_chunk_fts_deepens_until_it_finds_distinct_parent_sources() -> None:
    class ChunkOnlyStore(InMemoryVNextRetrievalStore):
        def search_sources(self, **_kwargs) -> list[dict[str, object]]:  # type: ignore[override]
            return []

    sources = [
        {
            "id": "source-long",
            "source_type": "document",
            "title": "Long document",
            "content_hash": "sha256:long",
            "domain": "project",
            "sensitivity": "private",
        },
        {
            "id": "source-other",
            "source_type": "document",
            "title": "Other document",
            "content_hash": "sha256:other",
            "domain": "project",
            "sensitivity": "private",
        },
    ]
    chunks = [
        {
            "id": f"chunk-long-{index}",
            "source_id": "source-long",
            "chunk_index": index,
            "text": "release completeness needle",
        }
        for index in range(33)
    ]
    chunks.append(
        {
            "id": "chunk-other",
            "source_id": "source-other",
            "chunk_index": 0,
            "text": "release completeness needle",
        }
    )
    store = ChunkOnlyStore(memories=[], sources=sources, source_chunks=chunks)

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="release completeness needle"))

    assert [row["id"] for row in pack["sources"]] == ["source-long", "source-other"]
    assert pack["trace"]["stages"]["sources"]["chunk_fts"] == 2


def test_provenance_fusion_pulls_source_with_no_lexical_match() -> None:
    # The evidence source has no query-term overlap anywhere the lexical
    # path looks (title/uri/metadata) and no matching chunk text; only the
    # provenance link of the winning memory can pull it in.
    class NoLexicalHitsStore(InMemoryVNextRetrievalStore):
        def search_sources(self, **_kwargs) -> list[dict[str, object]]:  # type: ignore[override]
            return []

    store = NoLexicalHitsStore(
        memories=[_memory_row("memory-1", "Quarterly board deck must use dark mode.")],
        sources=[
            {
                "id": "source-evidence",
                "source_type": "document",
                "title": "Import 9f3a4c",
                "content_hash": "sha256:evidence",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
        source_chunks=[
            {
                "id": "chunk-1",
                "source_id": "source-evidence",
                "chunk_index": 0,
                "text": "lorem ipsum dolor sit amet",
            }
        ],
        provenance_links=[
            {
                "id": "link-1",
                "target_type": "memory",
                "target_id": "memory-1",
                "source_id": "source-evidence",
                "quote": "Quarterly board deck must use dark mode.",
                "evidence_role": "quoted_from",
                "confidence": 0.9,
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="quarterly board deck dark mode", domains=("project",))
    )

    assert [item["id"] for item in pack["sources"]] == ["source-evidence"]
    stage = pack["trace"]["stages"]["sources"]
    assert stage["provenance"] == 1
    assert stage["title_recency"] == 0
    source_trace = [record for record in pack["trace"]["selected"] if record["target_type"] == "source"]
    assert source_trace[0]["stage_ranks"] == {"provenance": 1}


def test_source_provenance_uses_one_bulk_link_read_and_one_bulk_source_read() -> None:
    class BulkProvenanceStore(InMemoryVNextRetrievalStore):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.bulk_provenance_calls = 0
            self.bulk_source_calls = 0

        def list_provenance_links_for_targets(self, *, target_type, target_ids):
            self.bulk_provenance_calls += 1
            ids = set(target_ids)
            return [
                link
                for link in self.provenance_links
                if link.get("target_type") == target_type and link.get("target_id") in ids
            ]

        def get_sources_by_ids(self, source_ids):
            self.bulk_source_calls += 1
            ids = set(source_ids)
            return [source for source in self.sources if source.get("id") in ids]

    memories = [_memory_row(f"memory-{index:02d}", f"Winning memory {index}") for index in range(40)]
    sources = [
        {
            "id": f"source-{index:02d}",
            "title": f"Evidence {index}",
            "domain": "project",
            "sensitivity": "private",
        }
        for index in range(40)
    ]
    links = [
        {
            "id": f"link-{index:02d}",
            "target_type": "memory",
            "target_id": f"memory-{index:02d}",
            "source_id": f"source-{index:02d}",
        }
        for index in range(40)
    ]
    store = BulkProvenanceStore(
        memories=memories,
        sources=sources,
        provenance_links=links,
    )

    ranked_lists, stage = VNextRetrievalService(store)._source_stage_lists(
        query="unmatched",
        domains=[],
        sensitivity_allowed=["private"],
        limit=40,
        winning_memories=memories,
    )

    assert len(ranked_lists["provenance"]) == 40
    assert stage["provenance"] == 40
    assert store.bulk_provenance_calls == 1
    assert store.bulk_source_calls == 1


def test_source_chunk_or_fallback_retries_once_and_reports_the_relaxed_pass() -> None:
    source = {
        "id": "source-1",
        "source_type": "chat_session",
        "title": "Untitled session 7",
        "content_hash": "sha256:budget",
        "domain": "project",
        "sensitivity": "private",
    }
    store = InMemoryVNextRetrievalStore(
        memories=[],
        sources=[source],
        source_chunks=[
            {
                "id": "chunk-1",
                "source_id": "source-1",
                "chunk_index": 0,
                "text": "the annual budget review moved to Thursday",
            }
        ],
    )

    query = "when was the budget review moved?"
    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query=query))

    # Strict pass demands every token ("when" never appears); the one-shot
    # OR retry recovers the source and the trace reports the relaxed pass.
    assert store.chunk_match_any_queries == [query]
    assert [item["id"] for item in pack["sources"]] == ["source-1"]
    stage = pack["trace"]["stages"]["sources"]
    assert stage["chunk_fts"] == 1
    assert stage["chunk_fts_source"] == "postgres_fts_or_fallback"


def test_source_stage_degrades_to_title_recency_for_stores_without_chunk_search() -> None:
    class LegacyStore(InMemoryVNextRetrievalStore):
        # Shadow the class attributes so getattr(...) is not callable,
        # mirroring stores that predate the chunk-content substrate.
        search_source_chunks = None  # type: ignore[assignment]
        get_source = None  # type: ignore[assignment]

    store = LegacyStore(
        memories=[_memory_row("memory-1", "Alice legacy source stage check.")],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Alice legacy source",
                "content_hash": "sha256:legacy",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice legacy source", domains=("project",))
    )

    # Old behavior preserved: the lexical list alone still populates the
    # section, and the trace says which lists could not run.
    assert [item["id"] for item in pack["sources"]] == ["source-1"]
    assert pack["trace"]["stages"]["sources"] == {
        "source": "rrf(title_recency)",
        "candidate_count": 1,
        "chunk_fts": 0,
        "provenance": 0,
        "title_recency": 1,
        "chunk_fts_source": SOURCE_CHUNK_STAGE_DISABLED_NO_STORE_SUPPORT,
    }


def test_source_chunk_or_fallback_degrades_for_stores_without_match_any() -> None:
    class LegacyChunkStore(InMemoryVNextRetrievalStore):
        def search_source_chunks(  # type: ignore[override]
            self,
            *,
            query,
            domains=None,
            sensitivity_allowed=None,
            limit=50,
        ):
            # Legacy signature without match_any.
            return []

    store = LegacyChunkStore(
        memories=[],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Fallback degradation source",
                "content_hash": "sha256:degrade",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="kubernetes deployment pipeline")
    )

    # The TypeError from the retry is swallowed; the strict (empty) chunk
    # result stands and the label does not claim a relaxed pass ran.
    assert [item["id"] for item in pack["sources"]] == ["source-1"]
    stage = pack["trace"]["stages"]["sources"]
    assert stage["chunk_fts"] == 0
    assert stage["chunk_fts_source"] == "postgres_fts"


def test_source_content_beats_recency_on_sqlite() -> None:
    # The rank-1 LongMemEval failure: the session that SAYS the thing was
    # ingested months before lexically-similar-but-empty newer sessions.
    # The content-blind title/recency path ranks the newer sessions first;
    # the chunk-FTS list must pull the early session back to the top.
    store = _sqlite_retrieval_store()
    early = store.create_source(
        {
            "source_type": "chat_session",
            "title": "Chat about the golden retriever",
            "content_hash": "sha256:early",
            "captured_at": "2026-01-05T00:00:00Z",
        }
    )
    store.create_source_chunk(
        {
            "source_id": early["id"],
            "chunk_index": 0,
            "text": "[USER]: I adopted a golden retriever puppy named Biscuit last weekend.",
        }
    )
    decoys = []
    for index in range(6):
        decoy = store.create_source(
            {
                "source_type": "chat_session",
                "title": f"Golden hour photo walk {index}",
                "content_hash": f"sha256:decoy-{index}",
                "captured_at": f"2026-06-0{index + 1}T00:00:00Z",
            }
        )
        store.create_source_chunk(
            {
                "source_id": decoy["id"],
                "chunk_index": 0,
                "text": "We compared camera lenses and tripods for the evening shoot.",
            }
        )
        decoys.append(decoy)

    # Control: the content-blind lexical list alone ranks every newer
    # decoy above the session that contains the answer.
    lexical = store.search_sources(query="golden retriever Biscuit")
    assert lexical[0]["id"] != early["id"]
    assert lexical[-1]["id"] == early["id"]

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="golden retriever Biscuit"))

    assert pack["sources"][0]["id"] == early["id"]
    stage = pack["trace"]["stages"]["sources"]
    assert stage["source"] == "rrf(chunk_fts+provenance+title_recency)"
    assert stage["chunk_fts"] == 1
    assert stage["chunk_fts_source"] == "sqlite_fts"
    source_trace = {
        record["target_id"]: record for record in pack["trace"]["selected"] if record["target_type"] == "source"
    }
    assert source_trace[str(early["id"])]["stage_ranks"]["chunk_fts"] == 1


def test_source_content_or_fallback_beats_recency_on_sqlite() -> None:
    # Same content-beats-recency shape through the OR-fallback: the strict
    # chunk pass ANDs "alice public announcement go" and the stored text
    # says "goes", so only the relaxed retry can reach the early session.
    store = _sqlite_retrieval_store()
    early = store.create_source(
        {
            "source_type": "chat_session",
            "title": "Alice public announcement thread",
            "content_hash": "sha256:early",
            "captured_at": "2026-01-05T00:00:00Z",
        }
    )
    store.create_source_chunk(
        {
            "source_id": early["id"],
            "chunk_index": 0,
            "text": "[USER]: The Alice public announcement goes out Monday after the pre-launch audit passes.",
        }
    )
    for index in range(6):
        decoy = store.create_source(
            {
                "source_type": "chat_session",
                "title": f"Announcement drafts folder sync {index}",
                "content_hash": f"sha256:decoy-{index}",
                "captured_at": f"2026-06-0{index + 1}T00:00:00Z",
            }
        )
        store.create_source_chunk(
            {
                "source_id": decoy["id"],
                "chunk_index": 0,
                "text": "We reorganized the shared folder permissions this morning.",
            }
        )

    question = "When does the Alice public announcement go out?"
    assert store.search_source_chunks(query=question) == []

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query=question))

    assert pack["sources"][0]["id"] == early["id"]
    stage = pack["trace"]["stages"]["sources"]
    assert stage["chunk_fts"] == 1
    assert stage["chunk_fts_source"] == "sqlite_fts_or_fallback"


def test_provenance_fusion_pulls_source_with_no_lexical_match_on_sqlite() -> None:
    store = _sqlite_retrieval_store()
    evidence = store.create_source(
        {
            "source_type": "document",
            "title": "Import 9f3a4c",
            "content_hash": "sha256:evidence",
            "captured_at": "2026-01-05T00:00:00Z",
        }
    )
    store.create_source_chunk({"source_id": evidence["id"], "chunk_index": 0, "text": "lorem ipsum dolor sit amet"})
    decoy = store.create_source(
        {
            "source_type": "document",
            "title": "Quarterly newsletter archive",
            "content_hash": "sha256:decoy",
            "captured_at": "2026-06-01T00:00:00Z",
        }
    )
    store.create_source_chunk({"source_id": decoy["id"], "chunk_index": 0, "text": "newsletter formatting notes"})
    memory = store.create_memory(
        {
            "memory_key": "preference.board-deck",
            "memory_type": "preference",
            "title": "Board deck style",
            "canonical_text": "Sam prefers the quarterly board deck in dark mode.",
            "status": "active",
            "domain": "project",
            "sensitivity": "private",
            "value": {"text": "dark mode board deck"},
        }
    )
    store.create_provenance_link(
        {
            "target_type": "memory",
            "target_id": memory["id"],
            "source_id": evidence["id"],
            "quote": "quarterly board deck in dark mode",
            "evidence_role": "quoted_from",
        }
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="quarterly board deck dark mode")
    )

    # The winning memory's provenance drags the lexically-invisible
    # evidence source into the pack.
    assert [item["id"] for item in pack["relevant_memories"]] == [memory["id"]]
    assert str(evidence["id"]) in {str(item["id"]) for item in pack["sources"]}
    stage = pack["trace"]["stages"]["sources"]
    assert stage["provenance"] == 1
    source_trace = {
        record["target_id"]: record for record in pack["trace"]["selected"] if record["target_type"] == "source"
    }
    assert source_trace[str(evidence["id"])]["stage_ranks"]["provenance"] == 1


def test_context_pack_filters_memories_by_project_metadata() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-alicebot",
                "Alice project scoped row.",
                metadata_json={"project_id": "alicebot"},
            ),
            _memory_row(
                "memory-hermes",
                "Alice project scoped row for hermes.",
                metadata_json={"project_id": "hermes"},
            ),
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice project scoped", projects=("alicebot",))
    )

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-alicebot"]


def test_context_pack_project_scope_uses_overlap_for_multi_project_memories() -> None:
    shared = _memory_row(
        "memory-shared",
        "Shared release coordination fact.",
        project_scope=["alicebot", "hermes"],
        metadata_json={"project_scope": ["alicebot", "hermes"]},
    )
    store = InMemoryVNextRetrievalStore(memories=[shared], sources=[])

    alice = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="shared release coordination", projects=("alicebot",))
    )
    hermes = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="shared release coordination", projects=("hermes",))
    )
    unrelated = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="shared release coordination", projects=("other",))
    )

    assert [row["id"] for row in alice["relevant_memories"]] == ["memory-shared"]
    assert [row["id"] for row in hermes["relevant_memories"]] == ["memory-shared"]
    assert unrelated["relevant_memories"] == []


def test_context_pack_does_not_widen_explicit_empty_memory_scope() -> None:
    explicitly_unscoped = _memory_row(
        "memory-explicitly-unscoped",
        "Release coordination project fact.",
        project_scope=[],
        project_id="alicebot",
        metadata_json={
            "project_id": "alicebot",
            "agentic_memory": {"project_scope": ["alicebot"]},
        },
    )
    in_scope = _memory_row(
        "memory-alicebot",
        "Release coordination project fact.",
        project_scope=["alicebot"],
    )
    store = InMemoryVNextRetrievalStore(
        memories=[explicitly_unscoped, in_scope],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="release coordination project", projects=("alicebot",))
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-alicebot"]


def test_source_post_admission_uses_complete_persisted_envelope_scope() -> None:
    marker = "persisted source envelope evidence"
    stale_project = "stale-project"
    real_project = "real-project"
    explicitly_empty = {
        "id": "source-explicit-empty",
        "source_type": "chat_session",
        "title": marker,
        "content_hash": "sha256:source-explicit-empty",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {
            "project_id": stale_project,
            "metadata_json": {"project_scope": []},
        },
    }
    inner_real = {
        "id": "source-inner-real",
        "source_type": "chat_session",
        "title": marker,
        "content_hash": "sha256:source-inner-real",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {
            "project_id": stale_project,
            "metadata_json": {"project_scope": [real_project]},
        },
    }
    store = InMemoryVNextRetrievalStore(
        memories=[],
        sources=[explicitly_empty, inner_real],
        source_chunks=[
            {
                "id": "chunk-explicit-empty",
                "source_id": explicitly_empty["id"],
                "chunk_index": 0,
                "text": marker,
            },
            {
                "id": "chunk-inner-real",
                "source_id": inner_real["id"],
                "chunk_index": 0,
                "text": marker,
            },
        ],
    )

    stale_pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query=marker, projects=(stale_project,))
    )
    real_pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query=marker, projects=(real_project,))
    )

    assert stale_pack["sources"] == []
    assert [row["id"] for row in real_pack["sources"]] == ["source-inner-real"]
    assert real_pack["trace"]["stages"]["sources"]["chunk_fts"] == 1
    assert real_pack["trace"]["stages"]["sources"]["title_recency"] == 1


def test_scoped_pack_rejects_cross_project_source_metadata_and_derivations(monkeypatch) -> None:
    cross_scope_source = {
        "id": "source-hermes",
        "title": "Fundraiser history",
        "captured_at": "2025-01-02T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {
            "project_id": "alicebot",
            "session_date": "2025-01-01",
            "metadata_json": {"project_scope": ["hermes"]},
        },
    }
    memories = [
        _memory_row(
            "memory-alice-1",
            "The release fundraiser raised $1,000.",
            project_id="alicebot",
            source_created_at="2025-01-01T00:00:00Z",
            metadata_json={
                "project_id": "alicebot",
                "source_id": "source-hermes",
                "source_refs": ["source:source-hermes"],
                "source_chunk_id": "chunk-hermes",
                "capture_content_hash": "sha256:hermes-only",
                "session_date": "2025-01-01",
            },
        ),
        _memory_row(
            "memory-alice-2",
            "The release fundraiser raised $2,000.",
            project_id="alicebot",
            metadata_json={
                "project_id": "alicebot",
                "source_id": "source-hermes",
                "source_refs": ["source:source-hermes"],
                "session_date": "2025-02-01",
            },
        ),
    ]
    store = InMemoryVNextRetrievalStore(
        memories=memories,
        sources=[cross_scope_source],
        provenance_links=[
            {
                "id": "link-hermes",
                "target_type": "memory",
                "target_id": "memory-alice-1",
                "source_id": "source-hermes",
                "source_chunk_id": "chunk-hermes",
                "quote": "The release fundraiser raised $1,000.",
                "evidence_role": "quoted_from",
                "confidence": 0.9,
            }
        ],
    )
    source_resolver_results: list[object] = []
    original_build_currency_chains = vnext_retrieval_module.vnext_currency.build_currency_chains

    def _capture_currency_source_lookup(rows, *, source_lookup):
        source_resolver_results.append(source_lookup("source-hermes"))
        return original_build_currency_chains(rows, source_lookup=source_lookup)

    monkeypatch.setattr(
        vnext_retrieval_module.vnext_currency,
        "build_currency_chains",
        _capture_currency_source_lookup,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="release fundraiser",
            projects=("alicebot",),
            reference_time=datetime(2025, 3, 1, tzinfo=UTC),
        )
    )

    assert source_resolver_results == [None]
    assert pack["sources"] == []
    assert pack["supporting_evidence"] == []
    assert "derived_values" not in pack
    assert all("event_time" not in memory for memory in pack["relevant_memories"])
    first = pack["relevant_memories"][0]
    assert "source_created_at" not in first
    assert first["metadata_json"] == {"project_id": "alicebot", "source_refs": []}
    assert "source-hermes" not in json.dumps(pack, sort_keys=True)


def test_context_pack_applies_project_scope_to_every_emitted_content_section() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-alicebot",
                "Release readiness scoped fact.",
                project_id="alicebot",
            ),
            _memory_row(
                "memory-hermes",
                "Release readiness scoped fact.",
                project_id="hermes",
            ),
        ],
        sources=[
            {
                "id": "source-alicebot",
                "title": "Release readiness source A",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_id": "alicebot"},
            },
            {
                "id": "source-hermes",
                "title": "Release readiness source B",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_id": "hermes"},
            },
        ],
        open_loops=[
            {
                "id": "loop-alicebot",
                "title": "Ship AliceBot",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
                "project_id": "alicebot",
            },
            {
                "id": "loop-hermes",
                "title": "Ship Hermes",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
                "project_id": "hermes",
            },
        ],
        seeded_events=[
            {
                "id": "event-alicebot",
                "event_type": "memory.updated",
                "actor_type": "system",
                "target_type": "memory",
                "target_id": "memory-alicebot",
                "occurred_at": "2026-07-01T00:00:00Z",
            },
            {
                "id": "event-hermes",
                "event_type": "memory.updated",
                "actor_type": "system",
                "target_type": "memory",
                "target_id": "memory-hermes",
                "occurred_at": "2026-07-02T00:00:00Z",
            },
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="release readiness scoped",
            projects=("alicebot",),
        )
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-alicebot"]
    assert [row["id"] for row in pack["sources"]] == ["source-alicebot"]
    assert [row["id"] for row in pack["open_loops"]] == ["loop-alicebot"]
    assert [row["target_id"] for row in pack["recent_changes"]] == ["memory-alicebot"]


def test_context_pack_applies_people_scope_to_memories_sources_and_loops() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-sam",
                "Quarterly planning person-scoped fact.",
                metadata_json={"people": ["Sam"]},
            ),
            _memory_row(
                "memory-alex",
                "Quarterly planning person-scoped fact.",
                metadata_json={"people": ["Alex"]},
            ),
        ],
        sources=[
            {
                "id": "source-sam",
                "title": "Quarterly planning with Sam",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"people": ["Sam"]},
            },
            {
                "id": "source-alex",
                "title": "Quarterly planning with Alex",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"people": ["Alex"]},
            },
        ],
        open_loops=[
            {
                "id": "loop-sam",
                "title": "Follow up with Sam",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"person": "Sam"},
            },
            {
                "id": "loop-alex",
                "title": "Follow up with Alex",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"person": "Alex"},
            },
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="quarterly planning", people=("Sam",))
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-sam"]
    assert [row["id"] for row in pack["sources"]] == ["source-sam"]
    assert [row["id"] for row in pack["open_loops"]] == ["loop-sam"]


def test_people_scope_surfaces_valid_row_ranked_behind_a_full_decoy_window() -> None:
    """A people-scoped hit must survive even when it ranks behind a full
    ``2 * max_items`` window of non-matching decoys.

    The people filter runs in Python over the store's top-N, so if the
    candidate window is only ``2 * max_items`` the store returns nothing but
    decoys and the one valid row (ranked below the window) is never fetched,
    erasing a real result. Regression for audit P1 #5.
    """
    decoys = [
        _memory_row(
            f"memory-decoy-{index:02d}",
            "Quarterly planning person-scoped fact.",
            metadata_json={"people": ["Alex"]},
        )
        for index in range(16)
    ]
    valid_row = _memory_row(
        "memory-sam",
        "Quarterly planning person-scoped fact.",
        metadata_json={"people": ["Sam"]},
    )
    store = InMemoryVNextRetrievalStore(memories=[*decoys, valid_row], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="quarterly planning", people=("Sam",), max_items=8)
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-sam"]


def test_time_window_surfaces_valid_row_ranked_behind_a_full_decoy_window() -> None:
    """A time-window hit must survive even when it ranks behind a full
    ``2 * max_items`` window of out-of-window decoys (audit P1 #5)."""
    reference_time = datetime(2026, 7, 10, tzinfo=UTC)
    decoys = [
        _memory_row(
            f"memory-old-{index:02d}",
            "Time-window deployment fact.",
            valid_from="2026-06-01T00:00:00Z",
        )
        for index in range(16)
    ]
    valid_row = _memory_row(
        "memory-new",
        "Time-window deployment fact.",
        valid_from="2026-07-08T00:00:00Z",
    )
    store = InMemoryVNextRetrievalStore(memories=[*decoys, valid_row], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="time-window deployment",
            time_window="7d",
            reference_time=reference_time,
            max_items=8,
        )
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-new"]


def test_people_scope_surfaces_valid_row_beyond_the_overfetch_cap() -> None:
    """A people-scoped hit must survive even when it ranks past the fixed
    SCOPED_ROW_OVERFETCH_LIMIT (200) decoy window. A fixed over-fetch only moves
    the cliff; the store must deepen the scan until enough scoped rows survive
    (audit 2 P1 #3)."""
    decoys = [
        _memory_row(
            f"memory-decoy-{index:03d}",
            "Quarterly planning person-scoped fact.",
            metadata_json={"people": ["Alex"]},
        )
        for index in range(210)
    ]
    valid_row = _memory_row(
        "memory-sam",
        "Quarterly planning person-scoped fact.",
        metadata_json={"people": ["Sam"]},
    )
    store = InMemoryVNextRetrievalStore(memories=[*decoys, valid_row], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="quarterly planning", people=("Sam",), max_items=8)
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-sam"]


def test_time_window_surfaces_valid_row_beyond_the_overfetch_cap() -> None:
    """A time-window hit must survive even when it ranks past the fixed
    SCOPED_ROW_OVERFETCH_LIMIT (200) out-of-window decoy window (audit 2 P1 #3).
    The time filter has no graph rescue, so pagination is the only guard."""
    reference_time = datetime(2026, 7, 10, tzinfo=UTC)
    decoys = [
        _memory_row(
            f"memory-old-{index:03d}",
            "Time-window deployment fact.",
            valid_from="2026-06-01T00:00:00Z",
        )
        for index in range(210)
    ]
    valid_row = _memory_row(
        "memory-new",
        "Time-window deployment fact.",
        valid_from="2026-07-08T00:00:00Z",
    )
    store = InMemoryVNextRetrievalStore(memories=[*decoys, valid_row], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="time-window deployment",
            time_window="7d",
            reference_time=reference_time,
            max_items=8,
        )
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-new"]


def test_people_scope_has_no_rank_4000_cliff_and_embeds_query_once() -> None:
    decoys = [
        _memory_row(
            f"memory-decoy-{index:04d}",
            "Quarterly planning person-scoped fact.",
            metadata_json={"people": ["Alex"]},
        )
        for index in range(4_001)
    ]
    valid_row = _memory_row(
        "memory-sam",
        "Quarterly planning person-scoped fact.",
        metadata_json={"people": ["Sam"]},
    )
    rows = [*decoys, valid_row]
    store = InMemoryVNextRetrievalStore(memories=rows, vector_memories=rows, sources=[])
    provider = StubEmbeddingProvider()

    pack = VNextRetrievalService(store, embedding_provider=provider).compile_context_pack(
        VNextRetrievalRequest(
            query="quarterly planning",
            people=("Sam",),
            max_items=1,
            include_sources=False,
        )
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-sam"]
    assert store.fts_limits == [200, 400, 800, 1600, 3200, 6400]
    assert store.vector_limits == [200, 400, 800, 1600, 3200, 6400]
    assert provider.embedded_texts == ["quarterly planning"]


def test_legacy_scope_deepening_fails_closed_at_finite_boundary() -> None:
    scope = vnext_retrieval_module._ResolvedRetrievalScope(
        projects=frozenset(),
        people=frozenset({"sam"}),
        window_start=None,
        window_end=None,
    )
    limits: list[int] = []

    def _endless_decoys(limit: int) -> tuple[list[dict[str, object]], str]:
        limits.append(limit)
        return [{"id": f"decoy-{index}", "metadata_json": {"people": ["alex"]}} for index in range(limit)], "legacy"

    with pytest.raises(
        VNextRetrievalCompletenessError,
        match=f"within {LEGACY_SCOPED_SCAN_MAX_ROWS} rows",
    ):
        vnext_retrieval_module._fetch_scope_filtered(
            _endless_decoys,
            scope=scope,
            person_linked_memory_ids=frozenset(),
            target=1,
        )

    assert limits == [200, 400, 800, 1_600, 3_200, 6_400, 12_800, 16_384]


def test_legacy_scope_deepening_detects_repeated_prefix_and_deduplicates() -> None:
    scope = vnext_retrieval_module._ResolvedRetrievalScope(
        projects=frozenset(),
        people=frozenset({"sam"}),
        window_start=None,
        window_end=None,
    )
    repeated_limits: list[int] = []
    decoy = {"id": "same-decoy", "metadata_json": {"people": ["alex"]}}

    def _repeated(limit: int) -> tuple[list[dict[str, object]], str]:
        repeated_limits.append(limit)
        return [decoy] * limit, "legacy"

    with pytest.raises(VNextRetrievalCompletenessError, match="non-progressing prefix"):
        vnext_retrieval_module._fetch_scope_filtered(
            _repeated,
            scope=scope,
            person_linked_memory_ids=frozenset(),
            target=1,
        )
    assert repeated_limits == [200, 400]

    target = {"id": "sam-target", "metadata_json": {"people": ["sam"]}}
    rows, source = vnext_retrieval_module._fetch_scope_filtered(
        lambda _limit: ([target, target], "exhausted"),
        scope=scope,
        person_linked_memory_ids=frozenset(),
        target=1,
    )
    assert rows == [target]
    assert source == "exhausted"


def test_sqlite_people_and_time_scope_precedes_source_chunk_title_and_loop_limits() -> None:
    store = _sqlite_retrieval_store()
    user_id = store.user_id
    target_source_id = "00000000-0000-0000-0000-000000000001"
    target_chunk_id = "00000000-0000-0000-0000-000000000002"
    target_loop_id = "00000000-0000-0000-0000-000000000003"
    target_metadata = json.dumps({"people": ["Sam"], "session_date": "2026-07-08T00:00:00+00:00"})
    store.conn.execute(
        """
        INSERT INTO sources (
          id, user_id, source_type, title, content_hash, captured_at,
          source_created_at, metadata_json
        ) VALUES (?, ?, 'chat_session', 'Scoped needle source', ?, ?, ?, ?)
        """,
        (
            target_source_id,
            user_id,
            "target-hash",
            "2026-01-01T00:00:00+00:00",
            None,
            target_metadata,
        ),
    )
    store.conn.execute(
        """
        INSERT INTO source_chunks (id, user_id, source_id, chunk_index, text, created_at)
        VALUES (?, ?, ?, 0, 'scoped needle evidence', '2026-01-01T00:00:00+00:00')
        """,
        (target_chunk_id, user_id, target_source_id),
    )
    store.conn.execute(
        """
        INSERT INTO open_loops (
          id, user_id, title, status, opened_at, created_at, updated_at, metadata_json
        ) VALUES (?, ?, 'Scoped needle follow-up', 'open', ?, ?, ?, ?)
        """,
        (
            target_loop_id,
            user_id,
            "2026-07-08T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            target_metadata,
        ),
    )

    source_rows: list[tuple[object, ...]] = []
    chunk_rows: list[tuple[object, ...]] = []
    loop_rows: list[tuple[object, ...]] = []
    for index in range(420):
        is_people_decoy = index < 210
        ordinal = index + 10
        source_id = f"10000000-0000-0000-0000-{ordinal:012d}"
        metadata = json.dumps({"people": ["Alex" if is_people_decoy else "Sam"]})
        event_time = "2026-07-09T00:00:00+00:00" if is_people_decoy else "2027-01-01T00:00:00+00:00"
        created_at = f"2026-12-31T23:{index // 60:02d}:{index % 60:02d}+00:00"
        source_rows.append(
            (
                source_id,
                user_id,
                f"decoy-hash-{index}",
                created_at,
                event_time,
                metadata,
            )
        )
        chunk_rows.append(
            (
                f"20000000-0000-0000-0000-{ordinal:012d}",
                user_id,
                source_id,
                created_at,
            )
        )
        loop_rows.append(
            (
                f"30000000-0000-0000-0000-{ordinal:012d}",
                user_id,
                event_time,
                created_at,
                created_at,
                metadata,
            )
        )
    store.conn.executemany(
        """
        INSERT INTO sources (
          id, user_id, source_type, title, content_hash, captured_at,
          source_created_at, metadata_json
        ) VALUES (?, ?, 'chat_session', 'Scoped needle source', ?, ?, ?, ?)
        """,
        source_rows,
    )
    store.conn.executemany(
        """
        INSERT INTO source_chunks (id, user_id, source_id, chunk_index, text, created_at)
        VALUES (?, ?, ?, 0, 'scoped needle evidence', ?)
        """,
        chunk_rows,
    )
    store.conn.executemany(
        """
        INSERT INTO open_loops (
          id, user_id, title, status, opened_at, created_at, updated_at, metadata_json
        ) VALUES (?, ?, 'Scoped needle follow-up', 'open', ?, ?, ?, ?)
        """,
        loop_rows,
    )

    window_start = datetime(2026, 7, 3, tzinfo=UTC)
    window_end = datetime(2026, 7, 10, tzinfo=UTC)
    scope_kwargs = {
        "scope_people": ("sam",),
        "scope_window_start": window_start,
        "scope_window_end": window_end,
    }
    chunks = store.search_source_chunks(query="scoped needle", limit=1, **scope_kwargs)
    sources = store.search_sources(query="scoped needle", limit=1, **scope_kwargs)
    loops = store.list_open_loops(limit=1, **scope_kwargs)
    assert [str(row["source_id"]) for row in chunks] == [target_source_id]
    assert [str(row["id"]) for row in sources] == [target_source_id]
    assert [str(row["id"]) for row in loops] == [target_loop_id]

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="scoped needle",
            people=("Sam",),
            time_window="7d",
            reference_time=window_end,
            max_items=1,
        )
    )
    assert [str(row["id"]) for row in pack["sources"]] == [target_source_id]
    assert [str(row["id"]) for row in pack["open_loops"]] == [target_loop_id]


def test_context_pack_applies_relative_time_window_to_every_content_section() -> None:
    reference_time = datetime(2026, 7, 10, tzinfo=UTC)
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-new",
                "Time-window deployment fact.",
                valid_from="2026-07-08T00:00:00Z",
            ),
            _memory_row(
                "memory-old",
                "Time-window deployment fact.",
                valid_from="2026-06-01T00:00:00Z",
            ),
        ],
        sources=[
            {
                "id": "source-new",
                "title": "Time-window deployment source",
                "domain": "project",
                "sensitivity": "private",
                "source_created_at": "2026-07-09T00:00:00Z",
            },
            {
                "id": "source-old",
                "title": "Time-window deployment source",
                "domain": "project",
                "sensitivity": "private",
                "source_created_at": "2026-05-01T00:00:00Z",
            },
        ],
        open_loops=[
            {
                "id": "loop-new",
                "title": "Fresh deployment follow-up",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
                "opened_at": "2026-07-07T00:00:00Z",
            },
            {
                "id": "loop-old",
                "title": "Old deployment follow-up",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
                "opened_at": "2026-05-01T00:00:00Z",
            },
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="time-window deployment",
            time_window="7d",
            reference_time=reference_time,
        )
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-new"]
    assert [row["id"] for row in pack["sources"]] == ["source-new"]
    assert [row["id"] for row in pack["open_loops"]] == ["loop-new"]


def test_context_pack_threads_created_by_agents_and_run_filter_to_recall_stages() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            {
                **_memory_row("memory-openclaw-run1", "Alice agent scoped row one."),
                "created_by_agent_id": "openclaw",
                "run_id": "run-1",
            },
            {
                **_memory_row("memory-openclaw-run2", "Alice agent scoped row two."),
                "created_by_agent_id": "openclaw",
                "run_id": "run-2",
            },
            {
                **_memory_row("memory-hermes", "Alice agent scoped row three."),
                "created_by_agent_id": "hermes",
                "run_id": "run-3",
            },
        ],
        sources=[],
    )
    service = VNextRetrievalService(store)

    pack = service.compile_context_pack(
        VNextRetrievalRequest(
            query="Alice agent scoped",
            created_by_agent_ids=("openclaw",),
            filter_run_id="run-2",
        )
    )

    assert store.memory_search_kwargs[-1] == {
        "memory_types": (),
        "projects": (),
        "created_by_agent_ids": ("openclaw",),
        "run_id": "run-2",
    }
    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-openclaw-run2"]
    assert pack["trace"]["filters"]["created_by_agent_ids"] == ["openclaw"]
    assert pack["trace"]["filters"]["run_id"] == "run-2"

    # created_by filter alone returns every run from that agent.
    agent_pack = service.compile_context_pack(
        VNextRetrievalRequest(query="Alice agent scoped", created_by_agent_ids=("openclaw",))
    )
    assert {memory["id"] for memory in agent_pack["relevant_memories"]} == {
        "memory-openclaw-run1",
        "memory-openclaw-run2",
    }


def test_filter_run_id_is_independent_of_the_event_attribution_run_id() -> None:
    """request.run_id attributes the retrieval event to the caller's run; it
    must never scope which memories are retrieved (filter_run_id does)."""
    store = InMemoryVNextRetrievalStore(
        memories=[
            {
                **_memory_row("memory-other-run", "Alice run attribution row."),
                "run_id": "run-writer",
            },
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice run attribution", run_id="run-caller")
    )

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-other-run"]
    assert store.memory_search_kwargs[-1]["run_id"] is None
    compiled_events = [event for event in store.events if event["event_type"] == "retrieval.context_pack_compiled"]
    assert compiled_events[-1]["run_id"] == "run-caller"


# -- staleness notes ---------------------------------------------------------------


def test_context_pack_adds_staleness_note_for_long_unconfirmed_memories() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-stale",
                "Alice staleness check old fact.",
                last_confirmed_at="2020-01-01T00:00:00Z",
            ),
            _memory_row(
                "memory-fresh",
                "Alice staleness check fresh fact.",
                last_confirmed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            ),
            _memory_row("memory-unconfirmed", "Alice staleness check unconfirmed fact."),
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice staleness check"))

    by_id = {memory["id"]: memory for memory in pack["relevant_memories"]}
    staleness = by_id["memory-stale"]["staleness"]
    assert staleness["threshold_days"] == STALENESS_NOTE_AFTER_DAYS
    assert staleness["days_since_last_confirmed"] > STALENESS_NOTE_AFTER_DAYS
    assert "last confirmed" in staleness["note"]
    assert "staleness" not in by_id["memory-fresh"]
    assert "staleness" not in by_id["memory-unconfirmed"]


# -- contradicting evidence and recent changes --------------------------------------


def test_context_pack_populates_contradicting_evidence_from_active_beliefs() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row(
                "memory-1",
                "The deployment pipeline is not ready for production launch.",
            )
        ],
        sources=[],
        beliefs=[
            {
                "id": "belief-1",
                "memory_id": "memory-belief",
                "claim": "The deployment pipeline is ready for production launch.",
                "status": "active",
                "memory_type": "belief",
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="deployment pipeline production launch")
    )

    assert len(pack["contradicting_evidence"]) == 1
    record = pack["contradicting_evidence"][0]
    assert record["source_item"] == "memory:memory-1"
    assert record["belief_id"] == "belief-1"
    assert record["contradiction_type"] == "belief_conflict"
    assert record["recommended_action"]
    assert pack["trace"]["stages"]["contradictions"] == {
        "status": CONTRADICTIONS_STAGE_ENABLED,
        "candidate_count": 1,
    }
    # The read path must not write contradiction edges or extra events.
    assert [event["event_type"] for event in store.events] == ["retrieval.context_pack_compiled"]


def test_scoped_contradictions_deepen_beyond_200_and_bulk_load_backing_memories() -> None:
    new_memory = _memory_row(
        "memory-new",
        "The deployment pipeline is not ready for production launch.",
        project_id="alicebot",
    )
    decoy_backing = [
        _memory_row(
            f"belief-memory-decoy-{index:03d}",
            "Unrelated archived belief backing row.",
            memory_type="belief",
            project_id="hermes",
        )
        for index in range(210)
    ]
    target_backing = _memory_row(
        "belief-memory-target",
        "Deployment readiness belief backing row.",
        memory_type="belief",
        project_id="alicebot",
    )
    beliefs = [
        {
            "id": f"belief-decoy-{index:03d}",
            "memory_id": row["id"],
            "claim": "The unrelated Hermes archive is current.",
            "status": "active",
            "memory_type": "belief",
        }
        for index, row in enumerate(decoy_backing)
    ]
    beliefs.append(
        {
            "id": "belief-target",
            "memory_id": "belief-memory-target",
            "claim": "The deployment pipeline is ready for production launch.",
            "status": "active",
            "memory_type": "belief",
        }
    )
    store = InMemoryVNextRetrievalStore(
        memories=[new_memory, *decoy_backing, target_backing],
        sources=[],
        beliefs=beliefs,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="deployment pipeline production launch",
            projects=("alicebot",),
            include_sources=False,
        )
    )

    assert [row["belief_id"] for row in pack["contradicting_evidence"]] == ["belief-target"]
    # Prefix deepening performs bounded bulk reads, never one read per belief.
    assert 1 <= store.memory_bulk_reads < 10


def test_context_pack_degrades_contradictions_when_store_lacks_beliefs() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Alice degrade check row.")],
        sources=[],
    )
    # Shadow the class attribute so getattr(...) is not callable, mirroring
    # stores (like the SQLite on-ramp) that have no belief surface at all.
    store.list_beliefs = None  # type: ignore[method-assign]

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice degrade check"))

    assert pack["contradicting_evidence"] == []
    assert pack["trace"]["stages"]["contradictions"]["status"] == CONTRADICTIONS_STAGE_NO_STORE_SUPPORT


def test_context_pack_populates_recent_changes_from_memory_events() -> None:
    seeded_events = [
        {
            "id": f"event-{index}",
            "event_type": event_type,
            "actor_type": "system",
            "target_type": target_type,
            "target_id": f"memory-{index}",
            "occurred_at": f"2026-06-0{index + 1}T00:00:00Z",
        }
        for index, (event_type, target_type) in enumerate(
            [
                ("memory.created", "memory"),
                ("memory.updated", "memory"),
                ("provenance_link.created", "memory"),  # memory-targeted but not memory.*
                ("source.created", "source"),
                ("memory.created", "memory"),
                ("memory.updated", "memory"),
                ("memory.created", "memory"),
                ("memory.updated", "memory"),
                ("memory.created", "memory"),
            ]
        )
    ]
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Alice recent changes row.")],
        sources=[],
        seeded_events=seeded_events,
    )

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice recent changes"))

    recent = pack["recent_changes"]
    assert len(recent) == 5  # DEFAULT_RECENT_CHANGES_LIMIT
    assert all(change["event_type"].startswith("memory.") for change in recent)
    # Most recent events first (stub returns newest-first).
    assert recent[0]["event_id"] == "event-8"
    assert set(recent[0]) == {"event_id", "event_type", "target_id", "occurred_at", "actor_type"}
    assert pack["trace"]["stages"]["recent_changes"] == {"candidate_count": 5}


def test_scoped_recent_changes_deepen_beyond_200_and_bulk_load_targets() -> None:
    target = _memory_row(
        "memory-alicebot",
        "AliceBot release status changed.",
        project_id="alicebot",
    )
    decoys = [
        _memory_row(
            f"memory-hermes-{index:03d}",
            "Hermes unrelated status.",
            project_id="hermes",
        )
        for index in range(210)
    ]
    target_event = {
        "id": "event-alicebot",
        "event_type": "memory.updated",
        "actor_type": "system",
        "target_type": "memory",
        "target_id": "memory-alicebot",
        "occurred_at": "2026-07-01T00:00:00Z",
    }
    decoy_events = [
        {
            "id": f"event-hermes-{index:03d}",
            "event_type": "memory.updated",
            "actor_type": "system",
            "target_type": "memory",
            "target_id": row["id"],
            "occurred_at": "2026-07-02T00:00:00Z",
        }
        for index, row in enumerate(decoys)
    ]
    # The stub returns newest-first by reversing this list, so every decoy
    # ranks ahead of the one requested project event.
    store = InMemoryVNextRetrievalStore(
        memories=[target, *decoys],
        sources=[],
        seeded_events=[target_event, *decoy_events],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="AliceBot release status",
            projects=("alicebot",),
            include_sources=False,
        )
    )

    assert [row["event_id"] for row in pack["recent_changes"]] == ["event-alicebot"]
    assert 1 <= store.memory_bulk_reads < 20


# -- type-aware sections -------------------------------------------------------------


# -- entity-hop graph stage ----------------------------------------------------------


def _entity_row(entity_id: str, name: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": entity_id,
        "entity_type": "organization",
        "name": name,
        "normalized_name": name.casefold(),
        "aliases": [],
        "mention_count": 1,
    }
    row.update(overrides)
    return row


def _mention_edge(memory_id: str, entity_id: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": f"edge-{memory_id}-{entity_id}",
        "from_type": "memory",
        "from_id": memory_id,
        "to_type": "entity",
        "to_id": entity_id,
        "edge_type": "mentions",
        "observed_at": "2026-07-01T00:00:00Z",
        "valid_to": None,
    }
    row.update(overrides)
    return row


def test_entity_name_candidates_builds_ngrams_minus_stopwords() -> None:
    candidates = entity_name_candidates("What did Jane Rivera say about the Meridian acquisition?")

    # Unigrams survive unless they are stopwords; punctuation is normalized away.
    assert "jane" in candidates
    assert "meridian" in candidates
    assert "acquisition" in candidates
    assert "what" not in candidates
    assert "the" not in candidates
    # Bigrams/trigrams are generated, but never with a stopword on an edge.
    assert "jane rivera" in candidates
    assert "jane rivera say" in candidates
    assert "about the" not in candidates
    assert "the meridian" not in candidates
    # A stopword may still sit INSIDE a trigram name.
    assert "bank of america" in entity_name_candidates("Call Bank of America today")
    # Deduplicated and bounded.
    assert len(candidates) == len(set(candidates))
    long_query = " ".join(f"token{index}" for index in range(100))
    assert len(entity_name_candidates(long_query)) == ENTITY_NAME_CANDIDATE_LIMIT


def test_graph_stage_finds_entity_connected_memory_that_fts_misses() -> None:
    """THE multi-session mechanism: a past session stored a memory with zero
    lexical overlap with today's query. FTS misses it; the query resolves to
    the shared entity and the one-hop graph walk brings the memory back."""
    lexical = _memory_row("memory-lexical", "Meridian acquisition status notes.")
    # No query term appears in this text: FTS alone can never rank it.
    connected = _memory_row("memory-connected", "Legal review is blocking the Q3 close.")
    store = InMemoryVNextRetrievalStore(
        memories=[lexical, connected],
        sources=[],
        entities=[_entity_row("entity-meridian", "Meridian", mention_count=7)],
        edges=[_mention_edge("memory-connected", "entity-meridian")],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Meridian acquisition status", domains=("project",))
    )

    selected_ids = [memory["id"] for memory in pack["relevant_memories"]]
    assert "memory-connected" in selected_ids
    # Honest per-stage provenance: FTS really did miss the connected memory.
    graph_trace = pack["trace"]["stages"]["graph"]
    assert graph_trace == {
        "status": GRAPH_STAGE_ENABLED,
        "matched_entities": [
            {"id": "entity-meridian", "name": "Meridian", "entity_type": "organization", "mention_count": 7}
        ],
        "candidate_count": 1,
    }
    by_id = {record["target_id"]: record for record in pack["trace"]["selected"]}
    assert by_id["memory-connected"]["stage_ranks"] == {"graph": 1}
    assert by_id["memory-lexical"]["stage_ranks"] == {"fts": 1}
    # The pack says WHO it is about.
    assert pack["entities"] == graph_trace["matched_entities"]

    # Control: the same store without the edge never surfaces the memory.
    store.edges = []
    control = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Meridian acquisition status", domains=("project",))
    )
    assert "memory-connected" not in [memory["id"] for memory in control["relevant_memories"]]


def test_graph_stage_improves_rrf_rank_for_memory_seen_by_both_stages() -> None:
    shared = _memory_row("memory-shared", "Meridian roadmap detail three.")
    fts_only = [
        _memory_row("memory-top", "Meridian roadmap detail one."),
        _memory_row("memory-second", "Meridian roadmap detail two."),
    ]
    store = InMemoryVNextRetrievalStore(
        memories=[*fts_only, shared],
        sources=[],
        entities=[_entity_row("entity-meridian", "Meridian")],
        edges=[_mention_edge("memory-shared", "entity-meridian")],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Meridian roadmap", domains=("project",))
    )

    # FTS alone ranks memory-shared third; the graph vote lifts it to first.
    assert [memory["id"] for memory in pack["relevant_memories"]][0] == "memory-shared"
    by_id = {record["target_id"]: record for record in pack["trace"]["selected"]}
    assert by_id["memory-shared"]["stage_ranks"] == {"fts": 3, "graph": 1}
    assert by_id["memory-shared"]["rrf_score"] == pytest.approx(1.0 / (RRF_K + 3) + 1.0 / (RRF_K + 1), abs=1e-6)


def test_graph_candidates_are_ordered_by_edge_observed_at_then_memory_recency() -> None:
    older = _memory_row("memory-older-edge", "Board sync summary.", updated_at="2026-06-30T00:00:00Z")
    newer = _memory_row("memory-newer-edge", "Latest partner call notes.", updated_at="2026-06-01T00:00:00Z")
    store = InMemoryVNextRetrievalStore(
        memories=[older, newer],
        sources=[],
        entities=[_entity_row("entity-meridian", "Meridian")],
        edges=[
            _mention_edge("memory-older-edge", "entity-meridian", observed_at="2026-06-01T00:00:00Z"),
            _mention_edge("memory-newer-edge", "entity-meridian", observed_at="2026-07-01T00:00:00Z"),
        ],
    )

    rows, stage, _entities = VNextRetrievalService(store)._memory_graph_rows(
        query="Meridian", domains=[], sensitivity_allowed=["private"], limit=8
    )

    assert stage == GRAPH_STAGE_ENABLED
    # Edge recency wins even though the older-edge memory row is fresher.
    assert [row["id"] for row in rows] == ["memory-newer-edge", "memory-older-edge"]


def test_graph_stage_walks_edges_in_both_directions_and_ignores_other_edge_types() -> None:
    mentioned = _memory_row("memory-mentioned", "Sync notes alpha.")
    about = _memory_row("memory-about", "Sync notes beta.")
    unrelated = _memory_row("memory-unrelated", "Sync notes gamma.")
    store = InMemoryVNextRetrievalStore(
        memories=[mentioned, about, unrelated],
        sources=[],
        entities=[_entity_row("entity-meridian", "Meridian")],
        edges=[
            _mention_edge("memory-mentioned", "entity-meridian"),
            # Reverse direction with the 'about' type is also a valid link.
            {
                "id": "edge-reverse",
                "from_type": "entity",
                "from_id": "entity-meridian",
                "to_type": "memory",
                "to_id": "memory-about",
                "edge_type": "about",
                "observed_at": "2026-07-02T00:00:00Z",
                "valid_to": None,
            },
            # Non-mention edge types never pull memories into the stage.
            _mention_edge("memory-unrelated", "entity-meridian", edge_type="supports"),
        ],
    )

    rows, stage, _entities = VNextRetrievalService(store)._memory_graph_rows(
        query="Meridian", domains=[], sensitivity_allowed=["private"], limit=8
    )

    assert stage == GRAPH_STAGE_ENABLED
    assert {row["id"] for row in rows} == {"memory-mentioned", "memory-about"}


def test_graph_candidates_respect_status_expiry_and_scope_filters() -> None:
    searchable = _memory_row("memory-ok", "Weekly recap.", memory_type="decision")
    candidate_status = _memory_row("memory-candidate", "Unreviewed recap.", status="candidate")
    expired = _memory_row("memory-expired", "Old recap.", valid_to="2020-01-01T00:00:00Z")
    too_sensitive = _memory_row("memory-secret", "Secret recap.", sensitivity="highly_sensitive")
    wrong_type = _memory_row("memory-preference", "Preference recap.", memory_type="preference")
    wrong_project = _memory_row(
        "memory-hermes", "Hermes recap.", memory_type="decision", metadata_json={"project_id": "hermes"}
    )
    memories = [searchable, candidate_status, expired, too_sensitive, wrong_type, wrong_project]
    searchable["metadata_json"] = {"project_id": "alicebot"}
    store = InMemoryVNextRetrievalStore(
        memories=memories,
        sources=[],
        entities=[_entity_row("entity-meridian", "Meridian")],
        edges=[_mention_edge(str(row["id"]), "entity-meridian") for row in memories],
    )

    rows, stage, _entities = VNextRetrievalService(store)._memory_graph_rows(
        query="Meridian",
        domains=["project"],
        sensitivity_allowed=["private"],
        limit=8,
        memory_types=("decision",),
        projects=("alicebot",),
    )

    assert stage == GRAPH_STAGE_ENABLED
    assert [row["id"] for row in rows] == ["memory-ok"]


def test_graph_stage_disables_cleanly_when_no_entity_matches() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Roadmap notes.")],
        sources=[],
        entities=[_entity_row("entity-meridian", "Meridian")],
        edges=[_mention_edge("memory-1", "entity-meridian")],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="roadmap notes", domains=("project",))
    )

    assert pack["trace"]["stages"]["graph"] == {
        "status": GRAPH_STAGE_DISABLED_NO_ENTITY_MATCH,
        "matched_entities": [],
        "candidate_count": 0,
    }
    assert "entities" not in pack


def test_graph_stage_disables_honestly_for_stores_without_entity_support() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Meridian roadmap notes.")],
        sources=[],
    )
    # Shadow the class attribute so getattr(...) is not callable, mirroring
    # legacy/minimal stores that predate the entity substrate entirely.
    store.find_entities_by_names = None  # type: ignore[method-assign]

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Meridian roadmap", domains=("project",))
    )

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-1"]
    assert pack["trace"]["stages"]["graph"] == {
        "status": GRAPH_STAGE_DISABLED_NO_STORE_SUPPORT,
        "matched_entities": [],
        "candidate_count": 0,
    }
    assert "entities" not in pack


def test_graph_stage_caps_matched_entities_at_five_by_mention_count() -> None:
    entities = [_entity_row(f"entity-{index}", f"Meridian{index}", mention_count=index) for index in range(1, 8)]
    store = InMemoryVNextRetrievalStore(
        memories=[],
        sources=[],
        entities=entities,
        edges=[],
    )

    query = " ".join(f"Meridian{index}" for index in range(1, 8))
    _rows, stage, matched = VNextRetrievalService(store)._memory_graph_rows(
        query=query, domains=[], sensitivity_allowed=["private"], limit=8
    )

    assert stage == GRAPH_STAGE_ENABLED
    assert len(matched) == GRAPH_ENTITY_MATCH_LIMIT
    assert [entity["mention_count"] for entity in matched] == [7, 6, 5, 4, 3]


def test_graph_stage_bulk_reads_all_edges_beyond_200_in_constant_queries() -> None:
    class BulkGraphStore(InMemoryVNextRetrievalStore):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.bulk_edge_calls = 0
            self.bulk_memory_calls = 0

        def list_memory_entity_edges(self, *, entity_ids, edge_types=("mentions", "about")):
            self.bulk_edge_calls += 1
            ids = set(entity_ids)
            return [
                edge
                for edge in self.edges
                if edge.get("edge_type") in edge_types and (edge.get("to_id") in ids or edge.get("from_id") in ids)
            ]

        def get_memories_by_ids(self, memory_ids):
            self.bulk_memory_calls += 1
            ids = set(memory_ids)
            return [row for row in self.memories if row.get("id") in ids]

    memories = [_memory_row(f"memory-{index:03d}", f"Board note {index}.") for index in range(251)]
    store = BulkGraphStore(
        memories=memories,
        sources=[],
        entities=[_entity_row("entity-meridian", "Meridian")],
        edges=[_mention_edge(str(memory["id"]), "entity-meridian") for memory in memories],
    )

    rows, stage, _entities = VNextRetrievalService(store)._memory_graph_rows(
        query="Meridian", domains=[], sensitivity_allowed=["private"], limit=300
    )

    assert stage == GRAPH_STAGE_ENABLED
    assert len(rows) == 251
    assert {row["id"] for row in rows} == {memory["id"] for memory in memories}
    assert store.bulk_edge_calls == 1
    assert store.bulk_memory_calls == 1


# -- type-aware sections -------------------------------------------------------------


def test_context_pack_groups_procedures_and_routines_into_procedures_section() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[
            _memory_row("memory-procedure", "Alice grouping deploy procedure.", memory_type="procedure"),
            _memory_row("memory-routine", "Alice grouping morning routine.", memory_type="routine"),
            _memory_row("memory-belief", "Alice grouping strong belief.", memory_type="belief"),
            _memory_row("memory-decision", "Alice grouping final decision.", memory_type="decision"),
        ],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice grouping"))

    assert {item["id"] for item in pack["procedures"]} == {"memory-procedure", "memory-routine"}
    assert [item["id"] for item in pack["relevant_beliefs"]] == ["memory-belief"]
    assert [item["id"] for item in pack["decisions"]] == ["memory-decision"]


# -- per-section budget allocation report ----------------------------------------


ALL_ALLOCATION_SECTIONS = {
    "relevant_memories",
    "open_loops",
    "sources",
    "supporting_evidence",
    "contradicting_evidence",
    "item_annotations",
    "entities",
    "recent_changes",
    "supersession_context",
    "grounding",
    "derived_values",
}


def test_budget_allocation_reports_per_section_tokens_and_sums_to_estimate() -> None:
    memory = _memory_row("memory-1", "Alice allocation report memory row.")
    loop = {
        "id": "loop-1",
        "title": "Alice allocation report loop",
        "status": "open",
        "domain": "project",
        "sensitivity": "private",
    }
    source = {
        "id": "source-1",
        "source_type": "manual_text",
        "title": "Alice allocation report source",
        "content_hash": "sha256:alloc",
        "domain": "project",
        "sensitivity": "private",
    }
    store = InMemoryVNextRetrievalStore(
        memories=[memory],
        sources=[source],
        open_loops=[loop],
        provenance_links=[
            {
                "id": "link-1",
                "target_type": "memory",
                "target_id": "memory-1",
                "source_id": "source-1",
                "source_chunk_id": "chunk-1",
                "quote": "Alice allocation report memory row.",
                "evidence_role": "quoted_from",
                "confidence": 0.9,
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice allocation report", domains=("project",))
    )

    budget = pack["budget"]
    allocation = budget["allocation"]
    # Stable keys: every packed section reports, even at zero.
    assert set(allocation) == ALL_ALLOCATION_SECTIONS
    assert sum(allocation.values()) == budget["token_estimate"]
    assert allocation["relevant_memories"] == estimate_item_tokens(memory)
    assert allocation["open_loops"] == estimate_item_tokens(loop)
    assert allocation["sources"] == estimate_item_tokens(source)
    assert allocation["supporting_evidence"] == estimate_item_tokens(pack["supporting_evidence"][0])
    assert allocation["contradicting_evidence"] == 0
    assert budget["strategy"] == "balanced"
    assert pack["trace"]["budget"] == budget
    assert pack["trace"]["budget_strategy"] == "balanced"


# -- budget strategies -------------------------------------------------------------


def test_unknown_budget_strategy_is_rejected_with_choices_listed() -> None:
    store = InMemoryVNextRetrievalStore(memories=[], sources=[])

    with pytest.raises(VNextRetrievalValidationError) as excinfo:
        VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(query="Alice", budget_strategy="alphabetical")
        )

    message = str(excinfo.value)
    assert "budget_strategy" in message
    for choice in BUDGET_STRATEGIES:
        assert choice in message


def test_sources_first_flips_which_section_survives_a_tight_budget() -> None:
    memory = _memory_row(
        "memory-1",
        "Alice strategy flip memory row with deliberately long padding text so it costs more tokens.",
    )
    source = {
        "id": "source-1",
        "source_type": "manual_text",
        "title": "Alice strategy flip source",
        "content_hash": "sha256:flip",
        "domain": "project",
        "sensitivity": "private",
    }
    memory_cost = estimate_item_tokens(memory)
    source_cost = estimate_item_tokens(source)
    assert source_cost < memory_cost
    budget_tokens = memory_cost  # fits the memory alone, or the source with room to spare — never both

    def compile_with(strategy: str) -> dict[str, object]:
        store = InMemoryVNextRetrievalStore(memories=[dict(memory)], sources=[dict(source)])
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="Alice strategy flip",
                domains=("project",),
                max_tokens=budget_tokens,
                budget_strategy=strategy,
            )
        )

    balanced = compile_with("balanced")
    sources_first = compile_with("sources_first")

    # balanced packs memories first: the source no longer fits.
    assert [item["id"] for item in balanced["relevant_memories"]] == ["memory-1"]
    assert balanced["sources"] == []
    # sources_first packs sources first: the memory no longer fits.
    assert [item["id"] for item in sources_first["sources"]] == ["source-1"]
    assert sources_first["relevant_memories"] == []
    for pack in (balanced, sources_first):
        assert pack["budget"]["truncated"] is True
        assert sum(pack["budget"]["allocation"].values()) == pack["budget"]["token_estimate"]
    assert sources_first["budget"]["strategy"] == "sources_first"
    assert sources_first["trace"]["budget_strategy"] == "sources_first"


def test_recent_first_orders_memories_by_recency_before_fused_rank() -> None:
    older = _memory_row("memory-old", "Alice recency strategy row A", updated_at="2026-01-01T00:00:00Z")
    newer = _memory_row("memory-new", "Alice recency strategy row B", updated_at="2026-07-01T00:00:00Z")
    assert estimate_item_tokens(older) == estimate_item_tokens(newer)
    one_memory_budget = estimate_item_tokens(older)

    def compile_with(strategy: str, max_tokens: int | None) -> dict[str, object]:
        store = InMemoryVNextRetrievalStore(memories=[dict(older), dict(newer)], sources=[])
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="Alice recency strategy",
                domains=("project",),
                max_tokens=max_tokens,
                budget_strategy=strategy,
            )
        )

    # Without a budget the strategy still reorders the packed memories.
    assert [item["id"] for item in compile_with("balanced", None)["relevant_memories"]] == [
        "memory-old",
        "memory-new",
    ]
    assert [item["id"] for item in compile_with("recent_first", None)["relevant_memories"]] == [
        "memory-new",
        "memory-old",
    ]
    # Under a one-memory budget the strategy flips which memory survives.
    assert [item["id"] for item in compile_with("balanced", one_memory_budget)["relevant_memories"]] == ["memory-old"]
    assert [item["id"] for item in compile_with("recent_first", one_memory_budget)["relevant_memories"]] == [
        "memory-new"
    ]


def test_facts_first_boosts_fact_memory_types_to_the_front_of_packing() -> None:
    episodic = _memory_row("memory-epi-1", "Alice facts strategy row one", memory_type="episodic")
    decision = _memory_row("memory-dec-1", "Alice facts strategy row two", memory_type="decision")
    assert estimate_item_tokens(episodic) == estimate_item_tokens(decision)
    one_memory_budget = estimate_item_tokens(episodic)

    def compile_with(strategy: str, max_tokens: int | None) -> dict[str, object]:
        store = InMemoryVNextRetrievalStore(memories=[dict(episodic), dict(decision)], sources=[])
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="Alice facts strategy",
                domains=("project",),
                max_tokens=max_tokens,
                budget_strategy=strategy,
            )
        )

    assert [item["id"] for item in compile_with("facts_first", None)["relevant_memories"]] == [
        "memory-dec-1",
        "memory-epi-1",
    ]
    # Under a one-memory budget: balanced keeps the fused-rank leader, while
    # facts_first keeps the boosted decision memory instead.
    assert [item["id"] for item in compile_with("balanced", one_memory_budget)["relevant_memories"]] == ["memory-epi-1"]
    assert [item["id"] for item in compile_with("facts_first", one_memory_budget)["relevant_memories"]] == [
        "memory-dec-1"
    ]


def test_contradictions_first_lets_contradictions_survive_a_budget_that_drops_them_elsewhere() -> None:
    memory = _memory_row("memory-1", "The deployment pipeline is not ready for production launch.")
    belief = {
        "id": "belief-1",
        "memory_id": "memory-belief",
        "claim": "The deployment pipeline is ready for production launch.",
        "status": "active",
        "memory_type": "belief",
    }

    def compile_with(strategy: str, max_tokens: int | None) -> dict[str, object]:
        store = InMemoryVNextRetrievalStore(memories=[dict(memory)], sources=[], beliefs=[dict(belief)])
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="deployment pipeline production launch",
                max_tokens=max_tokens,
                budget_strategy=strategy,
            )
        )

    probe = compile_with("balanced", None)
    assert len(probe["contradicting_evidence"]) == 1
    record_cost = estimate_item_tokens(probe["contradicting_evidence"][0])
    memory_cost = estimate_item_tokens(memory)
    # The contradiction record quotes both texts, so it costs at least as
    # much as the memory row itself; a record-sized budget fits exactly one.
    assert memory_cost <= record_cost

    balanced = compile_with("balanced", record_cost)
    contradictions_first = compile_with("contradictions_first", record_cost)

    # balanced packs the memory; the contradiction record no longer fits.
    assert [item["id"] for item in balanced["relevant_memories"]] == ["memory-1"]
    assert balanced["contradicting_evidence"] == []
    # contradictions_first packs the contradiction first (derived from the
    # ranking-selected memories); the memory row itself no longer fits.
    assert len(contradictions_first["contradicting_evidence"]) == 1
    assert contradictions_first["contradicting_evidence"][0]["belief_id"] == "belief-1"
    assert contradictions_first["relevant_memories"] == []
    assert contradictions_first["budget"]["allocation"]["contradicting_evidence"] == record_cost
    assert (
        sum(contradictions_first["budget"]["allocation"].values()) == contradictions_first["budget"]["token_estimate"]
    )


# -- deterministic depth tiers ------------------------------------------------------


def test_unknown_context_depth_is_rejected_with_choices_listed() -> None:
    store = InMemoryVNextRetrievalStore(memories=[], sources=[])

    with pytest.raises(VNextRetrievalValidationError) as excinfo:
        VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice", context_depth="extreme"))

    message = str(excinfo.value)
    assert "context_depth" in message
    for choice in CONTEXT_DEPTHS:
        assert choice in message


def _minimal_tier_store() -> tuple[InMemoryVNextRetrievalStore, StubEmbeddingProvider]:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Meridian acquisition status decision.", memory_type="decision")],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Meridian acquisition source",
                "content_hash": "sha256:meridian",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
        vector_memories=[_memory_row("memory-vector", "Semantically nearby but lexically distant.")],
        beliefs=[
            {
                "id": "belief-1",
                "memory_id": "memory-belief",
                "claim": "The Meridian acquisition status decision is not final.",
                "status": "active",
                "memory_type": "belief",
            }
        ],
        entities=[_entity_row("entity-meridian", "Meridian", mention_count=7)],
        edges=[_mention_edge("memory-1", "entity-meridian")],
        seeded_events=[
            {
                "id": "event-1",
                "event_type": "memory.created",
                "actor_type": "system",
                "target_type": "memory",
                "target_id": "memory-1",
                "occurred_at": "2026-07-01T00:00:00Z",
            }
        ],
    )
    return store, StubEmbeddingProvider()


def test_minimal_depth_is_fts_only_with_honest_disabled_stage_statuses() -> None:
    store, provider = _minimal_tier_store()

    pack = VNextRetrievalService(store, embedding_provider=provider).compile_context_pack(
        VNextRetrievalRequest(query="Meridian acquisition status", domains=("project",), context_depth="minimal")
    )

    # FTS still works; vector and graph are skipped without a provider call.
    assert [item["id"] for item in pack["relevant_memories"]] == ["memory-1"]
    assert provider.embedded_texts == []
    stages = pack["trace"]["stages"]
    assert stages["vector"] == {"status": STAGE_DISABLED_MINIMAL, "candidate_count": 0}
    assert stages["graph"] == {"status": STAGE_DISABLED_MINIMAL, "matched_entities": [], "candidate_count": 0}
    assert "entities" not in pack
    # No sources, no contradictions, no recent changes, no typed sections.
    assert pack["sources"] == []
    assert stages["sources"] == {"candidate_count": 0, "status": STAGE_DISABLED_MINIMAL}
    assert pack["contradicting_evidence"] == []
    assert stages["contradictions"] == {"status": STAGE_DISABLED_MINIMAL, "candidate_count": 0}
    assert "recent_changes" not in pack
    assert stages["recent_changes"] == {"status": STAGE_DISABLED_MINIMAL, "candidate_count": 0}
    for typed_section in ("relevant_beliefs", "decisions", "procedures"):
        assert typed_section not in pack
    # Tier is recorded in the pack and the trace; the flag defaults resolve off.
    assert pack["context_depth"] == "minimal"
    assert pack["trace"]["context_depth"] == "minimal"
    assert pack["query_interpretation"]["requires_sources"] is False
    assert pack["query_interpretation"]["requires_contradictions"] is False
    # Disabled sources produce no misleading missing-source note.
    assert all(entry["kind"] != "source" for entry in pack["missing_information"])

    # Control: the same corpus at the default depth uses every stage.
    control_store, control_provider = _minimal_tier_store()
    control = VNextRetrievalService(control_store, embedding_provider=control_provider).compile_context_pack(
        VNextRetrievalRequest(query="Meridian acquisition status", domains=("project",))
    )
    assert control["context_depth"] == "low"
    assert control["trace"]["stages"]["vector"]["status"] == VECTOR_STAGE_ENABLED
    assert control["trace"]["stages"]["graph"]["status"] == GRAPH_STAGE_ENABLED
    assert [item["id"] for item in control["sources"]] == ["source-1"]
    assert len(control["recent_changes"]) == 1


def test_minimal_depth_caps_max_items_at_four() -> None:
    memories = [_memory_row(f"memory-{index}", f"Alice depth cap row {index}.") for index in range(1, 7)]
    store = InMemoryVNextRetrievalStore(memories=memories, sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice depth cap", max_items=8, context_depth="minimal")
    )
    assert len(pack["relevant_memories"]) == CONTEXT_DEPTH_MINIMAL_MAX_ITEMS

    smaller = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice depth cap", max_items=2, context_depth="minimal")
    )
    assert len(smaller["relevant_memories"]) == 2


def test_explicit_flags_override_the_minimal_tier_defaults() -> None:
    store, provider = _minimal_tier_store()

    pack = VNextRetrievalService(store, embedding_provider=provider).compile_context_pack(
        VNextRetrievalRequest(
            query="Meridian acquisition status",
            domains=("project",),
            context_depth="minimal",
            include_sources=True,
            include_contradictions=True,
        )
    )

    # Caller wins: sources and contradictions come back on, everything else
    # stays minimal (vector/graph still skipped). The fused stage record
    # reports every list it ran, even when only title_recency had rows
    # (the fake has no chunks; the chunk pass fell back to OR and still
    # found nothing).
    assert [item["id"] for item in pack["sources"]] == ["source-1"]
    assert pack["trace"]["stages"]["sources"] == {
        "source": "rrf(chunk_fts+provenance+title_recency)",
        "candidate_count": 1,
        "chunk_fts": 0,
        "provenance": 0,
        "title_recency": 1,
        "chunk_fts_source": "postgres_fts_or_fallback",
    }
    assert pack["trace"]["stages"]["contradictions"]["status"] == CONTRADICTIONS_STAGE_ENABLED
    assert pack["trace"]["stages"]["vector"]["status"] == STAGE_DISABLED_MINIMAL
    assert pack["query_interpretation"]["requires_sources"] is True
    assert pack["query_interpretation"]["requires_contradictions"] is True


def test_explicit_flags_override_the_medium_and_low_tier_defaults() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "The deployment pipeline is not ready for production launch.")],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Deployment pipeline source",
                "content_hash": "sha256:deploy",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
        beliefs=[
            {
                "id": "belief-1",
                "memory_id": "memory-belief",
                "claim": "The deployment pipeline is ready for production launch.",
                "status": "active",
                "memory_type": "belief",
            }
        ],
    )
    service = VNextRetrievalService(store)

    # medium forces contradictions on; an explicit False wins over the tier.
    medium_off = service.compile_context_pack(
        VNextRetrievalRequest(
            query="deployment pipeline production launch",
            context_depth="medium",
            include_contradictions=False,
        )
    )
    assert medium_off["contradicting_evidence"] == []
    assert medium_off["trace"]["stages"]["contradictions"]["status"] == CONTRADICTIONS_STAGE_NOT_REQUESTED

    # low includes sources by default; an explicit False wins over the tier.
    low_no_sources = service.compile_context_pack(
        VNextRetrievalRequest(query="deployment pipeline production launch", include_sources=False)
    )
    assert low_no_sources["sources"] == []
    assert low_no_sources["trace"]["stages"]["sources"]["status"] == SOURCES_STAGE_DISABLED_BY_FLAG


def test_medium_depth_forces_contradictions_on_for_non_strategic_queries() -> None:
    def build_store() -> InMemoryVNextRetrievalStore:
        return InMemoryVNextRetrievalStore(
            memories=[_memory_row("memory-1", "The deployment pipeline is not ready for production launch.")],
            sources=[],
            beliefs=[
                {
                    "id": "belief-1",
                    "memory_id": "memory-belief",
                    "claim": "The deployment pipeline is ready for production launch.",
                    "status": "active",
                    "memory_type": "belief",
                }
            ],
        )

    # "when ... timeline ..." classifies as temporal_recall, a non-strategic
    # query type: at low the contradictions stage stays off by default.
    query = "when did the deployment pipeline timeline change"
    low = VNextRetrievalService(build_store()).compile_context_pack(VNextRetrievalRequest(query=query))
    assert low["query_interpretation"]["query_type"] == "temporal_recall"
    assert low["contradicting_evidence"] == []
    assert low["trace"]["stages"]["contradictions"]["status"] == CONTRADICTIONS_STAGE_NOT_REQUESTED

    # medium is low plus the contradictions stage forced on for every query
    # type — the only default difference between the two tiers.
    medium = VNextRetrievalService(build_store()).compile_context_pack(
        VNextRetrievalRequest(query=query, context_depth="medium")
    )
    assert medium["context_depth"] == "medium"
    assert len(medium["contradicting_evidence"]) == 1
    assert medium["trace"]["stages"]["contradictions"]["status"] == CONTRADICTIONS_STAGE_ENABLED


def test_high_depth_adds_supersession_chain_notes_for_packed_memories() -> None:
    current = _memory_row(
        "memory-current",
        "Alice supersession current release gate policy.",
        supersedes="memory-v2",
    )
    version_two = _memory_row(
        "memory-v2",
        "Old release gate policy revision two.",
        status="superseded",
        supersedes="memory-v1",
    )
    version_one = _memory_row("memory-v1", "Old release gate policy revision one.", status="superseded")
    orphan = _memory_row(
        "memory-orphan",
        "Alice supersession orphan pointer row.",
        superseded_by="memory-missing",
    )
    plain = _memory_row("memory-plain", "Alice supersession plain row without pointers.")
    store = InMemoryVNextRetrievalStore(
        memories=[current, orphan, plain, version_two, version_one],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice supersession", domains=("project",), context_depth="high")
    )

    assert pack["context_depth"] == "high"
    notes = {note["memory_id"]: note for note in pack["supersession_context"]}
    assert set(notes) == {"memory-current", "memory-orphan"}
    assert notes["memory-current"]["supersedes"] == [
        {
            "id": "memory-v2",
            "title": "Old release gate policy revision two.",
            "memory_type": "semantic",
            "status": "superseded",
        },
        {
            "id": "memory-v1",
            "title": "Old release gate policy revision one.",
            "memory_type": "semantic",
            "status": "superseded",
        },
    ]
    assert notes["memory-current"]["superseded_by"] == []
    assert notes["memory-current"]["note"] == "supersedes 2 older revision(s)"
    # Unresolvable pointers degrade to id-only references.
    assert notes["memory-orphan"]["superseded_by"] == [{"id": "memory-missing"}]
    assert notes["memory-orphan"]["note"] == "superseded by 1 newer revision(s)"
    assert pack["trace"]["stages"]["supersession"] == {
        "status": SUPERSESSION_STAGE_ENABLED,
        "candidate_count": 2,
    }

    # Below high, the section and its trace stage do not exist.
    low = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice supersession", domains=("project",))
    )
    assert "supersession_context" not in low
    assert "supersession" not in low["trace"]["stages"]


def test_high_depth_supersession_chains_guard_against_cycles_and_cap_hops() -> None:
    cyclic_a = _memory_row("memory-a", "Alice cycle guard row alpha.", superseded_by="memory-b")
    cyclic_b = _memory_row("memory-b", "Cycle partner row beta.", superseded_by="memory-a")
    chain_rows = [
        _memory_row(
            f"memory-chain-{index}",
            f"Chain revision {index}.",
            status="superseded",
            supersedes=f"memory-chain-{index + 1}",
        )
        for index in range(1, 9)
    ]
    head = _memory_row("memory-head", "Alice cycle guard chain head.", supersedes="memory-chain-1")
    store = InMemoryVNextRetrievalStore(
        memories=[cyclic_a, head, cyclic_b, *chain_rows],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice cycle guard", domains=("project",), context_depth="high")
    )

    notes = {note["memory_id"]: note for note in pack["supersession_context"]}
    # The cycle stops after one hop instead of looping forever.
    assert [ref["id"] for ref in notes["memory-a"]["superseded_by"]] == ["memory-b"]
    # Long chains are capped at the hop limit.
    assert [ref["id"] for ref in notes["memory-head"]["supersedes"]] == [
        f"memory-chain-{index}" for index in range(1, 6)
    ]


def test_scoped_supersession_context_does_not_disclose_out_of_scope_ids() -> None:
    current = _memory_row(
        "memory-current",
        "Alice scoped supersession current fact.",
        project_id="alicebot",
        supersedes="memory-other-project",
    )
    other_project = _memory_row(
        "memory-other-project",
        "Hermes private historical fact.",
        project_id="hermes",
        status="superseded",
    )
    store = InMemoryVNextRetrievalStore(memories=[current, other_project], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="Alice scoped supersession",
            projects=("alicebot",),
            context_depth="high",
        )
    )

    serialized = json.dumps(pack, sort_keys=True)
    assert "Hermes private historical fact" not in serialized
    assert "memory-other-project" not in serialized


# -- validity annotations and current-version preference ----------------------------


def test_pack_items_carry_validity_only_when_temporal_signal_exists() -> None:
    plain = _memory_row("memory-plain", "Alice validity plain fact.")
    windowed = _memory_row(
        "memory-window",
        "Alice validity gym membership offer.",
        valid_from="2026-05-30T00:00:00Z",
        valid_to="2026-08-01T00:00:00Z",
    )
    open_ended = _memory_row(
        "memory-open",
        "Alice validity new address fact.",
        valid_from="2026-06-15T00:00:00Z",
    )
    sentinel = _memory_row(
        "memory-sentinel",
        "Alice validity unexpired fact.",
        valid_to="9999-12-31T23:59:59Z",
    )
    corrected = _memory_row(
        "memory-corrected",
        "Alice validity corrected commute fact.",
        metadata_json={
            "agentic_memory": {
                "lifecycle_status": "corrected",
                "corrections": [
                    {"corrected_at": "2026-06-01T00:00:00Z", "previous_text": "old"},
                    {"corrected_at": "2026-07-01T00:00:00Z", "previous_text": "older"},
                ],
            }
        },
    )
    store = InMemoryVNextRetrievalStore(
        memories=[plain, windowed, open_ended, sentinel, corrected],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice validity"))

    by_id = {memory["id"]: memory for memory in pack["relevant_memories"]}
    # Schema stability: rows without temporal/supersession signal gain NO key.
    assert "validity" not in by_id["memory-plain"]
    assert by_id["memory-window"]["validity"] == {
        "valid_from": "2026-05-30T00:00:00+00:00",
        "valid_to": "2026-08-01T00:00:00+00:00",
    }
    # Unbounded windows omit valid_to entirely.
    assert by_id["memory-open"]["validity"] == {"valid_from": "2026-06-15T00:00:00+00:00"}
    # The far-future "no expiry" stand-in (year >= VALID_TO_UNBOUNDED_YEAR)
    # is not a validity signal.
    assert "validity" not in by_id["memory-sentinel"]
    # In-place corrections surface the newest corrected_at.
    assert by_id["memory-corrected"]["validity"] == {"corrected_at": "2026-07-01T00:00:00+00:00"}
    assert pack["trace"]["supersession_reorders"] == 0


def test_pack_ranks_replacement_above_superseded_ancestor_and_traces_the_reorder() -> None:
    ancestor = _memory_row(
        "memory-old-color",
        "Alice preference check: favorite color is blue.",
        superseded_by="memory-new-color",
    )
    bystander = _memory_row("memory-bystander", "Alice preference check unrelated note.")
    replacement = _memory_row(
        "memory-new-color",
        "Alice preference check: favorite color is green.",
        supersedes="memory-old-color",
    )
    store = InMemoryVNextRetrievalStore(memories=[ancestor, bystander, replacement], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice preference check"))

    # Fused (FTS) order was ancestor, bystander, replacement; only the
    # supersession pair is reordered -- the replacement moves directly
    # above its ancestor, and the ancestor keeps its slot ahead of the
    # bystander (demote-not-drop, nothing is removed).
    assert [memory["id"] for memory in pack["relevant_memories"]] == [
        "memory-new-color",
        "memory-old-color",
        "memory-bystander",
    ]
    assert pack["trace"]["supersession_reorders"] == 1
    by_id = {memory["id"]: memory for memory in pack["relevant_memories"]}
    assert by_id["memory-old-color"]["validity"] == {
        "superseded": True,
        "superseded_by_memory_id": "memory-new-color",
    }
    assert by_id["memory-new-color"]["validity"] == {"supersedes_memory_id": "memory-old-color"}
    assert "validity" not in by_id["memory-bystander"]
    # The trace keeps the honest fused ranking; the reorder is reported
    # only through the counter.
    trace_ranks = {
        record["target_id"]: record["rank"] for record in pack["trace"]["selected"] if record["target_type"] == "memory"
    }
    assert trace_ranks == {"memory-old-color": 1, "memory-bystander": 2, "memory-new-color": 3}


def test_pack_annotates_one_sided_supersedes_pointer_via_packmate() -> None:
    # The ancestor never received the superseded_by back-pointer; only the
    # replacement's supersedes side exists. The pack-local hint still
    # annotates the ancestor and the pair still reorders.
    ancestor = _memory_row("memory-old-office", "Alice relocation office is in Austin.")
    replacement = _memory_row(
        "memory-new-office",
        "Alice relocation office moved to Denver.",
        supersedes="memory-old-office",
    )
    store = InMemoryVNextRetrievalStore(memories=[ancestor, replacement], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice relocation office"))

    assert [memory["id"] for memory in pack["relevant_memories"]] == [
        "memory-new-office",
        "memory-old-office",
    ]
    assert pack["trace"]["supersession_reorders"] == 1
    by_id = {memory["id"]: memory for memory in pack["relevant_memories"]}
    assert by_id["memory-old-office"]["validity"] == {
        "superseded": True,
        "superseded_by_memory_id": "memory-new-office",
    }


def test_pack_keeps_order_when_replacement_already_ranks_above_ancestor() -> None:
    replacement = _memory_row(
        "memory-new-plan",
        "Alice rollout plan ships in September.",
        supersedes="memory-old-plan",
    )
    ancestor = _memory_row(
        "memory-old-plan",
        "Alice rollout plan ships in July.",
        superseded_by="memory-new-plan",
    )
    store = InMemoryVNextRetrievalStore(memories=[replacement, ancestor], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice rollout plan"))

    assert [memory["id"] for memory in pack["relevant_memories"]] == [
        "memory-new-plan",
        "memory-old-plan",
    ]
    assert pack["trace"]["supersession_reorders"] == 0
    by_id = {memory["id"]: memory for memory in pack["relevant_memories"]}
    assert by_id["memory-old-plan"]["validity"]["superseded"] is True


def test_supersession_reorder_terminates_on_corrupt_pointer_cycles() -> None:
    # Corrupt data: two rows claim to supersede each other. Each side moves
    # at most once, so the reorder terminates deterministically instead of
    # looping, and both rows are annotated as superseded.
    cyclic_a = _memory_row("memory-a", "Alice cycle pair row alpha.", superseded_by="memory-b")
    cyclic_b = _memory_row("memory-b", "Alice cycle pair row beta.", superseded_by="memory-a")
    store = InMemoryVNextRetrievalStore(memories=[cyclic_a, cyclic_b], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="Alice cycle pair"))

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-a", "memory-b"]
    assert pack["trace"]["supersession_reorders"] == 2
    by_id = {memory["id"]: memory for memory in pack["relevant_memories"]}
    assert by_id["memory-a"]["validity"]["superseded"] is True
    assert by_id["memory-b"]["validity"]["superseded"] is True


def test_properly_superseded_row_is_already_excluded_from_packs_on_sqlite() -> None:
    # The product supersede flows (review supersede-existing, agentic undo)
    # retire the old row with status=superseded, and the search discipline
    # (status IN ('active','accepted')) excludes it from every stage. The
    # annotation work never needs to demote such rows -- they are absent --
    # and the replacement still carries its supersedes pointer annotation.
    store = _sqlite_retrieval_store()
    old = store.create_memory(
        {
            "memory_key": "ku.gym.old",
            "memory_type": "semantic",
            "title": "Gym membership",
            "canonical_text": "The gym membership is with FitLife near the old office.",
            "status": "active",
            "domain": "personal",
            "sensitivity": "private",
            "value": {"text": "gym membership FitLife"},
        }
    )
    replacement = store.create_memory(
        {
            "memory_key": "ku.gym.new",
            "memory_type": "semantic",
            "title": "Gym membership (updated)",
            "canonical_text": "The gym membership moved to PowerHouse.",
            "status": "active",
            "supersedes": str(old["id"]),
            "domain": "personal",
            "sensitivity": "private",
            "value": {"text": "gym membership PowerHouse"},
        }
    )
    store.update_memory(
        memory_id=str(old["id"]),
        patch={"status": "superseded", "superseded_by": str(replacement["id"])},
        actor_type="user",
    )

    pack = VNextRetrievalService(store).compile_context_pack(VNextRetrievalRequest(query="gym membership"))

    assert [memory["id"] for memory in pack["relevant_memories"]] == [str(replacement["id"])]
    assert pack["relevant_memories"][0]["validity"] == {"supersedes_memory_id": str(old["id"])}
    assert pack["trace"]["supersession_reorders"] == 0


def test_knowledge_update_pack_prefers_correction_on_sqlite() -> None:
    # Knowledge-update shape on the real store: value A is committed, a
    # correction B supersedes it, but only the pointer lands (the row is
    # never retired, so both versions stay searchable). The pack must put
    # B above the surviving A and annotate A as superseded.
    store = _sqlite_retrieval_store()
    stale = store.create_memory(
        {
            "memory_key": "preference.favorite-color",
            "memory_type": "preference",
            "title": "Favorite color",
            "canonical_text": (
                "Favorite color: the user's favorite color is blue. Favorite color blue came up again while shopping."
            ),
            "status": "active",
            "domain": "personal",
            "sensitivity": "private",
            "value": {"text": "favorite color blue"},
        }
    )
    correction = store.create_memory(
        {
            "memory_key": "preference.favorite-color.corrected",
            "memory_type": "preference",
            "title": "Favorite color (corrected)",
            "canonical_text": "Correction: the user's favorite color is green now.",
            "status": "active",
            "supersedes": str(stale["id"]),
            "domain": "personal",
            "sensitivity": "private",
            "value": {"text": "favorite color green"},
        }
    )
    store.update_memory(
        memory_id=str(stale["id"]),
        patch={"superseded_by": str(correction["id"])},
        actor_type="system",
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="What is the user's favorite color?")
    )

    ordered_ids = [memory["id"] for memory in pack["relevant_memories"]]
    assert set(ordered_ids) == {str(stale["id"]), str(correction["id"])}
    assert ordered_ids.index(str(correction["id"])) < ordered_ids.index(str(stale["id"]))
    assert pack["trace"]["supersession_reorders"] == 1
    by_id = {memory["id"]: memory for memory in pack["relevant_memories"]}
    assert by_id[str(stale["id"])]["validity"] == {
        "superseded": True,
        "superseded_by_memory_id": str(correction["id"]),
    }
    assert by_id[str(correction["id"])]["validity"] == {"supersedes_memory_id": str(stale["id"])}


def test_context_depth_low_matches_default_behavior_regression_pin() -> None:
    def build_store() -> InMemoryVNextRetrievalStore:
        return InMemoryVNextRetrievalStore(
            memories=[
                _memory_row("memory-decision", "Meridian roadmap release decision.", memory_type="decision"),
                _memory_row("memory-belief", "Meridian roadmap strong belief.", memory_type="belief"),
                _memory_row("memory-note", "Meridian roadmap plain note."),
            ],
            sources=[
                {
                    "id": "source-1",
                    "source_type": "manual_text",
                    "title": "Meridian roadmap source",
                    "content_hash": "sha256:pin",
                    "domain": "project",
                    "sensitivity": "private",
                }
            ],
            open_loops=[
                {
                    "id": "loop-1",
                    "title": "Meridian roadmap follow-up",
                    "status": "open",
                    "domain": "project",
                    "sensitivity": "private",
                }
            ],
            provenance_links=[
                {
                    "id": "link-1",
                    "target_type": "memory",
                    "target_id": "memory-decision",
                    "source_id": "source-1",
                    "source_chunk_id": "chunk-1",
                    "quote": "Meridian roadmap release decision.",
                    "evidence_role": "quoted_from",
                    "confidence": 0.9,
                }
            ],
            vector_memories=[_memory_row("memory-vector", "Semantically adjacent roadmap thought.")],
            beliefs=[
                {
                    "id": "belief-1",
                    "memory_id": "memory-belief-row",
                    "claim": "The Meridian roadmap is not a release decision.",
                    "status": "active",
                    "memory_type": "belief",
                }
            ],
            entities=[_entity_row("entity-meridian", "Meridian", mention_count=3)],
            edges=[_mention_edge("memory-note", "entity-meridian")],
            seeded_events=[
                {
                    "id": "event-1",
                    "event_type": "memory.created",
                    "actor_type": "system",
                    "target_type": "memory",
                    "target_id": "memory-decision",
                    "occurred_at": "2026-07-01T00:00:00Z",
                }
            ],
        )

    def compile_pack(**overrides: object) -> dict[str, object]:
        return VNextRetrievalService(build_store(), embedding_provider=StubEmbeddingProvider()).compile_context_pack(
            VNextRetrievalRequest(
                query="Meridian roadmap release status",
                domains=("project",),
                trace_id="trace-pin",
                **overrides,  # type: ignore[arg-type]
            )
        )

    default_pack = compile_pack()
    low_pack = compile_pack(context_depth="low")

    # Only the per-compile pack id may differ: low IS the default behavior.
    default_pack.pop("context_pack_id")
    low_pack.pop("context_pack_id")
    assert low_pack == default_pack
    assert default_pack["context_depth"] == "low"


# -- coverage mode (aggregation intent) ---------------------------------------


def _coverage_dormant_store() -> InMemoryVNextRetrievalStore:
    return InMemoryVNextRetrievalStore(
        memories=[
            _memory_row("memory-decision", "Meridian roadmap release decision.", memory_type="decision"),
            _memory_row("memory-note", "Meridian roadmap plain note."),
        ],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Meridian roadmap source",
                "content_hash": "sha256:dormant-pin",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {},
            }
        ],
        open_loops=[
            {
                "id": "loop-1",
                "title": "Meridian roadmap follow-up",
                "status": "open",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
        provenance_links=[
            {
                "id": "link-1",
                "target_type": "memory",
                "target_id": "memory-decision",
                "source_id": "source-1",
                "source_chunk_id": "chunk-1",
                "quote": "Meridian roadmap release decision.",
                "evidence_role": "quoted_from",
                "confidence": 0.9,
            }
        ],
        source_chunks=[
            {"id": "chunk-1", "source_id": "source-1", "text": "Meridian roadmap release decision recorded."}
        ],
    )


def test_ungated_query_takes_the_byte_identical_coverage_free_path(monkeypatch) -> None:
    """Regression guard: without aggregation intent, coverage mode must not exist.

    Compiles the same non-aggregation request twice — once with the real
    detector (which stays dormant) and once with the entire coverage
    feature hard-disabled — with deterministic pack ids. The two packs
    must serialize byte-identically, and no coverage vocabulary may leak
    into the pack anywhere.
    """
    stores: list[InMemoryVNextRetrievalStore] = []

    def compile_pack() -> dict[str, object]:
        counter = itertools.count(1)
        monkeypatch.setattr(vnext_retrieval_module, "uuid4", lambda: UUID(int=next(counter)))
        store = _coverage_dormant_store()
        stores.append(store)
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="Meridian roadmap release status",
                domains=("project",),
                trace_id="trace-dormant-pin",
            )
        )

    dormant_pack = compile_pack()
    monkeypatch.setattr(vnext_retrieval_module.vnext_coverage_query, "detect_aggregation_intent", lambda query: None)
    hard_disabled_pack = compile_pack()

    assert json.dumps(dormant_pack, sort_keys=True, default=str) == json.dumps(
        hard_disabled_pack, sort_keys=True, default=str
    )
    canonical_pack = json.dumps(
        dormant_pack,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    assert sha256(canonical_pack).hexdigest() == ("4b046a9dccd4b58d0970f8957e65c769619338f29ba547fe3f39eecd5d6b7b32")
    assert "coverage" not in json.dumps(dormant_pack, default=str)
    assert "aggregation" not in dormant_pack
    assert set(dormant_pack["budget"]["allocation"]) == {
        "relevant_memories",
        "open_loops",
        "sources",
        "supporting_evidence",
        "contradicting_evidence",
        "item_annotations",
        "entities",
        "recent_changes",
        "supersession_context",
        "grounding",
        "derived_values",
    }
    assert set(dormant_pack["trace"]["stages"].keys()) == {
        "fts",
        "vector",
        "graph",
        "sources",
        "open_loops",
        "contradictions",
        "recent_changes",
    }
    # Identical store call shape: exactly one memory FTS pass, no clause
    # sub-retrievals, on both runs.
    assert [store.memory_search_kwargs for store in stores] == [
        stores[0].memory_search_kwargs,
        stores[0].memory_search_kwargs,
    ]
    assert len(stores[0].memory_search_kwargs) == 1


def test_minimal_depth_keeps_coverage_mode_dormant_for_aggregation_queries() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-game", "Hosted board game night with friends.")],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="How many times did I host board game night?", context_depth="minimal")
    )

    assert "coverage" not in json.dumps(pack, default=str)
    assert len(store.memory_search_kwargs) == 1


_COVERAGE_DUPLICATE_TEXT = "friday board game night with the usual crowd we played catan and ate pizza"
_COVERAGE_INSTANCE_TEXTS = {
    "inst-1": "board game night we played azul with sam and casey at the river cafe",
    "inst-2": "board game night we hosted wingspan for the neighbors on the porch",
    "inst-3": "board game night with codenames and homemade tacos at dana's loft",
    "inst-4": "board game night featuring terraforming mars and root with the club",
    "inst-5": "board game night where gloomhaven ran long and we ordered dumplings",
    "inst-6": "board game night trying splendor and ticket to ride with visiting cousins",
}


def _instance_diversity_store() -> InMemoryVNextRetrievalStore:
    """Ten near-verbatim duplicate sessions outranking six distinct instances."""
    sources: list[dict[str, object]] = []
    source_chunks: list[dict[str, object]] = []

    def add_source(source_id: str, text: str) -> None:
        sources.append(
            {
                "id": source_id,
                "source_type": "chat_session",
                "title": f"Chat session {source_id}",
                "content_hash": f"sha256:{source_id}",
                "domain": "unknown",
                "sensitivity": "internal",
                "metadata_json": {"session_id": source_id},
            }
        )
        source_chunks.append({"id": f"chunk-{source_id}", "source_id": source_id, "text": text})

    for index in range(1, 11):
        add_source(f"dupe-{index:02d}", _COVERAGE_DUPLICATE_TEXT)
    for source_id, text in _COVERAGE_INSTANCE_TEXTS.items():
        add_source(source_id, text)
    return InMemoryVNextRetrievalStore(memories=[], sources=sources, source_chunks=source_chunks)


def test_aggregation_intent_promotes_distinct_instances_over_near_duplicates(monkeypatch) -> None:
    """The assigned scenario: 6 instances + 10 near-duplicate distractors.

    Standard retrieval at the 8-slot source limit selects only duplicates;
    under detected aggregation intent the deeper pool plus the diversity
    demotion pass captures all six distinct instances.
    """
    query = "How many times did I host board game night?"
    # max_items=16 keeps the source-stage pool deeper than the 8 selection
    # slots (the source pool is max(8, max_items)); coverage mode itself
    # never deepens the source pool.
    request = VNextRetrievalRequest(query=query, max_items=16)

    control_store = _instance_diversity_store()
    with monkeypatch.context() as patch:
        patch.setattr(vnext_retrieval_module.vnext_coverage_query, "detect_aggregation_intent", lambda q: None)
        control_pack = VNextRetrievalService(control_store).compile_context_pack(request)
    control_ids = [str(source["id"]) for source in control_pack["sources"]]
    assert control_ids == [f"dupe-{index:02d}" for index in range(1, 9)]
    assert "coverage" not in json.dumps(control_pack, default=str)

    coverage_store = _instance_diversity_store()
    pack = VNextRetrievalService(coverage_store).compile_context_pack(request)

    selected_ids = [str(source["id"]) for source in pack["sources"]]
    assert selected_ids == ["dupe-01", *_COVERAGE_INSTANCE_TEXTS, "dupe-02"]
    assert pack["trace"]["stages"]["coverage_mode"] == {
        "source": "coverage_mode",
        "intent": "count",
        "trigger": "how many",
        "sub_intent": "frequency",
        "clauses": 1,
        "clause_candidate_count": 0,
        "diversity_status": "enabled",
        "diversity_demotions": 9,
        "memory_demotions": 0,
        "source_demotions": 9,
        "card_promotions": 0,
        "candidate_instance_count": {
            "count": 0,
            "unit": "deduplicated_memory_candidate_groups",
            "basis": "bounded_scoped_fts_candidates",
            "query_basis": "context_pack_query",
            "matching_criteria": "searchable scoped memories matched by the reported FTS mode",
            "deduplication": "source_chunk_then_source_then_memory_id",
            "fts_source": "postgres_fts_or_fallback",
            "rows_examined": 0,
            "rollup_cards_excluded": 0,
            "candidate_cap": 96,
            "scope_filtered": False,
            "candidate_prefix_exhausted": True,
            "more_candidate_groups_may_exist": False,
            "is_answer": False,
            "supports_numeric_sum": False,
        },
    }
    # An OR-fallback statistic with no selected accepted roll-up stays in the
    # diagnostic trace and never opens a reader-facing budget section.
    assert "aggregation" not in pack
    assert "aggregation" not in pack["budget"]["allocation"]
    assert pack["budget"]["token_estimate"] == sum(pack["budget"]["allocation"].values())
    # Single-clause aggregation: no clause sub-retrievals beyond the main
    # FTS pass (strict miss + OR fallback on the empty memories fixture).
    assert len(coverage_store.memory_search_kwargs) == len(control_store.memory_search_kwargs)
    demoted = [
        record
        for record in pack["trace"]["selected"]
        if record["target_type"] == "source" and record["target_id"].startswith("dupe-")
    ]
    assert {record["target_id"] for record in demoted} == {"dupe-01", "dupe-02"}


def test_multi_clause_aggregation_backfills_clause_only_memory_into_freed_slots(monkeypatch) -> None:
    """Clause sub-retrieval rows fill slots the group-diversity pass frees.

    The clause-only memory never displaces a fused winner on score (that
    configuration measurably regressed coverage); it enters the pool right
    behind the winners and wins a slot only because a same-source repeat
    was demoted.
    """
    query = "How many hours did I spend on hiking and swimming last month?"

    def build_store() -> InMemoryVNextRetrievalStore:
        # 24 fillers fill the deepened main pool (max_items=4 -> 4*2*3)
        # so the swim memory is truncated out of the main FTS list; the
        # first two fillers share a provenance source, freeing one slot
        # under group diversity. Filler text matches the main query and
        # clause 1 ("on" in "session") but never clause 2.
        fillers = [
            _memory_row(
                f"memory-filler-{index:02d}",
                f"Weekly bread baking session notes volume {index}.",
                metadata_json={"source_id": "src-shared" if index <= 2 else f"src-{index:02d}"},
            )
            for index in range(1, 25)
        ]
        swim = _memory_row("memory-swim", "Swimming laps review.", metadata_json={"source_id": "src-swim"})
        return InMemoryVNextRetrievalStore(memories=[*fillers, swim], sources=[])

    control_store = build_store()
    with monkeypatch.context() as patch:
        patch.setattr(vnext_retrieval_module.vnext_coverage_query, "detect_aggregation_intent", lambda q: None)
        control_pack = VNextRetrievalService(control_store).compile_context_pack(
            VNextRetrievalRequest(query=query, max_items=4)
        )
    control_ids = [str(memory["id"]) for memory in control_pack["relevant_memories"]]
    assert control_ids == ["memory-filler-01", "memory-filler-02", "memory-filler-03", "memory-filler-04"]
    assert len(control_store.memory_search_kwargs) == 1

    coverage_store = build_store()
    pack = VNextRetrievalService(coverage_store).compile_context_pack(VNextRetrievalRequest(query=query, max_items=4))

    selected_ids = [str(memory["id"]) for memory in pack["relevant_memories"]]
    # filler-02 (same source as filler-01) is demoted; the freed slot goes
    # to the clause-2 backfill memory, not to filler-05.
    assert selected_ids == ["memory-filler-01", "memory-filler-03", "memory-filler-04", "memory-swim"]
    coverage_stage = pack["trace"]["stages"]["coverage_mode"]
    assert coverage_stage["intent"] == "count"
    assert coverage_stage["sub_intent"] == "numeric_value"
    assert "candidate_instance_count" not in coverage_stage
    assert "aggregation" not in pack
    assert "aggregation" not in pack["budget"]["allocation"]
    assert coverage_stage["clauses"] == 2
    assert coverage_stage["clause_candidate_count"] == 5  # 4 clause-1 rows + 1 clause-2 row
    assert coverage_stage["memory_demotions"] == 1
    assert coverage_stage["source_demotions"] == 0
    assert coverage_stage["diversity_demotions"] == 1
    swim_trace = [
        record
        for record in pack["trace"]["selected"]
        if record["target_type"] == "memory" and record["target_id"] == "memory-swim"
    ]
    assert swim_trace[0]["stage_ranks"] == {"coverage_clause_2": 1}
    assert swim_trace[0]["rrf_score"] == 0.0  # honest: backfill, not fused
    # The demoted same-source repeat is reported honestly in the trace.
    assert pack["trace"]["excluded_counts"]["coverage_redundant_demoted"] == 1
    assert "memory-filler-02" not in selected_ids
    # One main FTS pass plus one per clause.
    assert len(coverage_store.memory_search_kwargs) == 3


def test_uncorroborated_count_statistic_does_not_consume_reader_budget() -> None:
    store = InMemoryVNextRetrievalStore(memories=[], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="How many bikes did I service?", max_tokens=1)
    )

    assert "aggregation" not in pack
    assert pack["budget"]["truncated"] is False
    assert pack["budget"]["dropped_item_count"] == 0
    assert "aggregation" not in pack["budget"]["allocation"]
    assert pack["budget"]["token_estimate"] == sum(pack["budget"]["allocation"].values())


# -- coverage mode: accepted roll-up card ranking -------------------------------


def _accepted_rollup_card_row(
    card_id: str,
    text: str,
    member_ids: list[str],
    *,
    topic_label: str = "board game night",
) -> dict[str, object]:
    """A memory row shaped exactly like an accepted roll-up card: the
    metadata vnext_rollups writes at proposal time plus the acceptance
    stamp accept_consolidation_candidate adds."""
    return _memory_row(
        card_id,
        text,
        metadata_json={
            "candidate_kind": "memory_rollup",
            "consolidation": {
                "proposal_kind": "rollup",
                "cluster_member_ids": list(member_ids),
                "proposed_supersede": [],
                "survivor_memory_id": None,
                "accepted": {
                    "accepted_at": "2026-07-01T00:00:00+00:00",
                    "actor_type": "user",
                    "accepted_by": None,
                    "reason": "roll-up card covers the topic",
                    "superseded_member_ids": [],
                    "skipped_members": [],
                },
                "rollup": {
                    "rollup_key": f"topic:{topic_label}",
                    "group_kind": "topic",
                    "topic_label": topic_label,
                    "revises_memory_id": None,
                },
            },
        },
        value={
            "kind": "memory_rollup",
            "text": text,
            "rollup": {
                "rollup_key": f"topic:{topic_label}",
                "group_kind": "topic",
                "topic_label": topic_label,
                "member_count": len(member_ids),
                "member_ids": list(member_ids),
                "displayed_instance_count": len(member_ids),
                "instances_truncated": False,
                "grouping_input_truncated": False,
                "grouping_input_count": len(member_ids),
                "grouping_input_total": len(member_ids),
                "grouping_input_total_exact": True,
            },
        },
    )


_ROLLUP_MEMBER_GAMES = ("azul", "wingspan", "codenames", "root", "gloomhaven")


def _rollup_card_store() -> InMemoryVNextRetrievalStore:
    """Five member instances outranking their own accepted roll-up card.

    The fake FTS returns rows in fixture order, so the members eat the
    fused ranks and the card fuses last — the round-4-measured failure
    shape (topical cards ranked below their receipts).
    """
    members = [
        _memory_row(f"memory-game-{index}", f"Board game night instance {index}: played {game}.")
        for index, game in enumerate(_ROLLUP_MEMBER_GAMES, start=1)
    ]
    card = _accepted_rollup_card_row(
        "memory-rollup-card",
        "Roll-up: board game night — 5 instances: azul; wingspan; codenames; root; gloomhaven.",
        [f"memory-game-{index}" for index in range(1, len(_ROLLUP_MEMBER_GAMES) + 1)],
    )
    return InMemoryVNextRetrievalStore(memories=[*members, card], sources=[])


def test_aggregation_intent_promotes_accepted_rollup_card_above_its_members(monkeypatch) -> None:
    """The pre-Sprint generic card-promotion posture remains unchanged."""
    request = VNextRetrievalRequest(query="How many times did I host board game night?", max_items=4)

    control_store = _rollup_card_store()
    with monkeypatch.context() as patch:
        patch.setattr(
            vnext_retrieval_module.vnext_coverage_query,
            "promote_rollup_cards",
            lambda candidates, **kwargs: (list(candidates), 0),
        )
        control_pack = VNextRetrievalService(control_store).compile_context_pack(request)
    control_ids = [str(memory["id"]) for memory in control_pack["relevant_memories"]]
    # Without the promotion the members eat every slot and the card never packs.
    assert control_ids == [f"memory-game-{index}" for index in range(1, 5)]

    pack = VNextRetrievalService(_rollup_card_store()).compile_context_pack(request)

    selected_ids = [str(memory["id"]) for memory in pack["relevant_memories"]]
    # The card takes its best member's rank; the members stay directly
    # below it as receipts (demote-not-drop: only the last slot holder
    # loses selection).
    assert selected_ids == ["memory-rollup-card", "memory-game-1", "memory-game-2", "memory-game-3"]
    coverage_stage = pack["trace"]["stages"]["coverage_mode"]
    assert coverage_stage["card_promotions"] == 1
    assert coverage_stage["sub_intent"] == "frequency"
    candidate = coverage_stage["candidate_instance_count"]
    assert candidate["count"] == 5
    assert candidate["rollup_cards_excluded"] == 1
    assert candidate["is_answer"] is False
    assert candidate["supports_numeric_sum"] is False
    assert "aggregation" not in pack
    assert "aggregation" not in pack["budget"]["allocation"]
    assert coverage_stage["memory_demotions"] == 0
    card_trace = [
        record
        for record in pack["trace"]["selected"]
        if record["target_type"] == "memory" and record["target_id"] == "memory-rollup-card"
    ]
    assert card_trace[0]["rank"] == 1
    assert card_trace[0]["selected"] is True
    # The displaced members are demoted, never dropped: they stay in the
    # candidate pool as honest trimmed_by_limit exclusions.
    assert pack["trace"]["excluded_counts"]["trimmed_by_limit"] == 2
    assert "coverage_redundant_demoted" not in pack["trace"]["excluded_counts"]


def test_frequency_members_with_multiple_occurrences_remain_trace_only() -> None:
    member_ids = [f"match-{index}" for index in range(1, 4)]
    members = [_memory_row(memory_id, f"I score goals twice in {memory_id}.") for memory_id in member_ids]
    card = _accepted_rollup_card_row(
        "goals-rollup",
        "Score goals — 3 instances: match one; match two; match three.",
        member_ids,
        topic_label="score goals",
    )
    pack = VNextRetrievalService(
        InMemoryVNextRetrievalStore(memories=[*members, card], sources=[])
    ).compile_context_pack(VNextRetrievalRequest(query="How many times did I score goals?", max_items=3))

    candidate = pack["trace"]["stages"]["coverage_mode"]["candidate_instance_count"]
    assert candidate["count"] == 3
    assert candidate["is_answer"] is False
    # Three memories/card members do not establish six occurrences (twice in
    # each memory), so the carrier never emits a reader-facing count.
    assert "aggregation" not in pack
    assert "aggregation" not in pack["budget"]["allocation"]


def test_naturally_selected_unrelated_rollup_does_not_turn_trace_count_into_answer() -> None:
    unrelated = [
        _memory_row(
            f"unrelated-{index}",
            f"Board game night unrelated candidate {index}.",
        )
        for index in range(1, 4)
    ]
    card = _accepted_rollup_card_row(
        "memory-rollup-card",
        "Roll-up: board game night - 3 instances: azul; wingspan; codenames.",
        ["actual-member-1", "actual-member-2", "actual-member-3"],
    )
    pack = VNextRetrievalService(
        InMemoryVNextRetrievalStore(memories=[*unrelated, card], sources=[])
    ).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I host board game night?",
            max_items=4,
        )
    )

    coverage = pack["trace"]["stages"]["coverage_mode"]
    assert coverage["candidate_instance_count"]["count"] == 3
    assert coverage["card_promotions"] == 0
    assert "memory-rollup-card" in {str(memory["id"]) for memory in pack["relevant_memories"]}
    assert "aggregation" not in pack
    assert "aggregation" not in pack["budget"]["allocation"]


def test_how_often_cadence_recognizes_without_changing_store_calls_or_ranking(monkeypatch) -> None:
    request = VNextRetrievalRequest(query="How often did I host board game night?", max_items=4)
    control_store = _rollup_card_store()
    with monkeypatch.context() as patch:
        patch.setattr(
            vnext_retrieval_module.vnext_coverage_query,
            "detect_aggregation_intent",
            lambda query: None,
        )
        control_pack = VNextRetrievalService(control_store).compile_context_pack(request)

    cadence_store = _rollup_card_store()
    pack = VNextRetrievalService(cadence_store).compile_context_pack(request)

    coverage_stage = pack["trace"]["stages"]["coverage_mode"]
    assert coverage_stage["sub_intent"] == "cadence"
    assert coverage_stage["clauses"] == 0
    assert coverage_stage["clause_candidate_count"] == 0
    assert coverage_stage["diversity_status"] == (
        "disabled: cadence requires rate evidence without coverage reordering"
    )
    assert coverage_stage["memory_demotions"] == 0
    assert coverage_stage["source_demotions"] == 0
    assert coverage_stage["card_promotions"] == 0
    assert "candidate_instance_count" not in coverage_stage
    assert "aggregation" not in pack
    expected_ids = [
        "memory-game-1",
        "memory-game-2",
        "memory-game-3",
        "memory-game-4",
    ]
    assert [str(memory["id"]) for memory in control_pack["relevant_memories"]] == expected_ids
    assert [str(memory["id"]) for memory in pack["relevant_memories"]] == expected_ids
    assert cadence_store.memory_search_kwargs == control_store.memory_search_kwargs
    assert cadence_store.fts_limits == control_store.fts_limits


def test_non_aggregation_query_keeps_rollup_card_ranking_dormant(monkeypatch) -> None:
    """Byte-identity dormancy: without aggregation intent the promotion
    pass must not run at all, even with an accepted card in the store."""
    stores: list[InMemoryVNextRetrievalStore] = []

    def compile_pack() -> dict[str, object]:
        counter = itertools.count(1)
        monkeypatch.setattr(vnext_retrieval_module, "uuid4", lambda: UUID(int=next(counter)))
        store = _rollup_card_store()
        stores.append(store)
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="What did we play at board game night?",
                max_items=4,
                trace_id="trace-card-dormant-pin",
            )
        )

    dormant_pack = compile_pack()

    def _promotion_bomb(candidates: object, **kwargs: object) -> object:
        raise AssertionError("promote_rollup_cards must stay dormant without aggregation intent")

    monkeypatch.setattr(vnext_retrieval_module.vnext_coverage_query, "promote_rollup_cards", _promotion_bomb)
    hard_disabled_pack = compile_pack()

    assert json.dumps(dormant_pack, sort_keys=True, default=str) == json.dumps(
        hard_disabled_pack, sort_keys=True, default=str
    )
    assert "coverage" not in json.dumps(dormant_pack, default=str)
    # Fusion order stands untouched: the members outrank the card.
    assert [str(memory["id"]) for memory in dormant_pack["relevant_memories"]] == [
        f"memory-game-{index}" for index in range(1, 5)
    ]


def test_aggregation_intent_without_cards_leaves_ordering_unchanged(monkeypatch) -> None:
    """No-cards dormancy: intent fires, but with no accepted card among the
    candidates the pack is byte-identical to a promotion-disabled run and
    the trace reports zero promotions."""

    def build_store() -> InMemoryVNextRetrievalStore:
        members = [
            _memory_row(f"memory-game-{index}", f"Board game night instance {index}: played {game}.")
            for index, game in enumerate(_ROLLUP_MEMBER_GAMES, start=1)
        ]
        return InMemoryVNextRetrievalStore(memories=members, sources=[])

    request = VNextRetrievalRequest(
        query="How many times did I host board game night?",
        max_items=4,
        trace_id="trace-no-cards-pin",
    )

    def compile_pack(store: InMemoryVNextRetrievalStore) -> dict[str, object]:
        counter = itertools.count(1)
        monkeypatch.setattr(vnext_retrieval_module, "uuid4", lambda: UUID(int=next(counter)))
        return VNextRetrievalService(store).compile_context_pack(request)

    live_pack = compile_pack(build_store())
    with monkeypatch.context() as patch:
        patch.setattr(
            vnext_retrieval_module.vnext_coverage_query,
            "promote_rollup_cards",
            lambda candidates, **kwargs: (list(candidates), 0),
        )
        disabled_pack = compile_pack(build_store())

    assert json.dumps(live_pack, sort_keys=True, default=str) == json.dumps(disabled_pack, sort_keys=True, default=str)
    assert live_pack["trace"]["stages"]["coverage_mode"]["card_promotions"] == 0
    assert [str(memory["id"]) for memory in live_pack["relevant_memories"]] == [
        f"memory-game-{index}" for index in range(1, 5)
    ]


# -- temporal-anchor stage ---------------------------------------------------------


def test_temporal_anchor_surfaces_right_dated_memory_over_stronger_lexical_hit() -> None:
    # Lexically the wrong-dated memory wins FTS rank 1; the temporal list
    # votes for the right-dated one and RRF flips the final order.
    wrong_dated = _memory_row(
        "memory-wrong-date",
        "Museum visit museum gallery exhibition museum tour",
        valid_from="2022-08-01T00:00:00Z",
    )
    right_dated = _memory_row(
        "memory-right-date",
        "Museum visit with a friend downtown",
        valid_from="2023-03-15T00:00:00Z",
    )
    store = InMemoryVNextRetrievalStore(memories=[wrong_dated, right_dated], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Which museum did I visit in March 2023?", max_items=1)
    )

    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-right-date"]
    stage = pack["trace"]["stages"]["temporal_anchor"]
    assert stage == {
        "source": "temporal_anchor",
        "status": TEMPORAL_STAGE_ENABLED,
        "window": ["2023-03-01T00:00:00+00:00", "2023-04-01T00:00:00+00:00"],
        "parsed_from": "March 2023",
        "candidate_count": 1,
    }
    selected = [record for record in pack["trace"]["selected"] if record["target_id"] == "memory-right-date"]
    assert selected[0]["stage_ranks"]["temporal_anchor"] == 1
    assert store.time_search_calls == [
        {
            "window_start": datetime(2023, 3, 1, tzinfo=UTC),
            "window_end": datetime(2023, 4, 1, tzinfo=UTC),
        }
    ]


def test_scoped_temporal_stage_deepens_beyond_200_decoys() -> None:
    decoys = [
        _memory_row(
            f"memory-alex-{index:03d}",
            "Museum visit downtown.",
            valid_from="2023-03-15T00:00:00Z",
            metadata_json={"people": ["Alex"]},
        )
        for index in range(210)
    ]
    target = _memory_row(
        "memory-sam",
        "Museum visit downtown.",
        valid_from="2023-03-15T00:00:00Z",
        metadata_json={"people": ["Sam"]},
    )
    store = InMemoryVNextRetrievalStore(memories=[*decoys, target], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="Which museum did I visit in March 2023?",
            people=("Sam",),
            max_items=1,
            include_sources=False,
        )
    )

    assert [row["id"] for row in pack["relevant_memories"]] == ["memory-sam"]
    assert pack["trace"]["stages"]["temporal_anchor"]["candidate_count"] == 1
    assert len(store.time_search_calls) == 2


def test_no_anchor_query_has_no_temporal_stage_and_no_store_call() -> None:
    # Regression guard: date-free queries must behave exactly as before —
    # no temporal trace stage, no stage_ranks entry, no store round-trip,
    # and the fused sources record keeps its pre-anchor shape.
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Kubernetes deployment pipeline notes")],
        sources=[
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Kubernetes deployment runbook",
                "content_hash": "sha256:k8s",
                "domain": "project",
                "sensitivity": "private",
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="kubernetes deployment pipeline")
    )

    assert "temporal_anchor" not in pack["trace"]["stages"]
    assert store.time_search_calls == []
    for record in pack["trace"]["selected"]:
        assert "temporal_anchor" not in record["stage_ranks"]
    assert SOURCE_STAGE_TEMPORAL not in pack["trace"]["stages"]["sources"]
    assert pack["trace"]["stages"]["sources"]["source"] == "rrf(chunk_fts+provenance+title_recency)"


def test_wrong_temporal_window_cannot_evict_strong_lexical_hits() -> None:
    # The query's date phrase points at a window that only matches an
    # unrelated memory. Fusion keeps the anchor a ranking vote: the strong
    # lexical+vector hit still wins the single slot, and with two slots
    # the unrelated row merely joins below it.
    strong = _memory_row("memory-strong", "Vendor contract decision signed with Acme")
    wrong_window = _memory_row(
        "memory-wrong-window",
        "Completely unrelated pottery class note",
        valid_from="2023-03-10T00:00:00Z",
    )
    provider = StubEmbeddingProvider()

    def build_store() -> InMemoryVNextRetrievalStore:
        return InMemoryVNextRetrievalStore(
            memories=[strong, wrong_window],
            sources=[],
            vector_memories=[strong],
        )

    single = VNextRetrievalService(build_store(), embedding_provider=provider).compile_context_pack(
        VNextRetrievalRequest(query="What vendor contract decision did we sign in March 2023?", max_items=1)
    )
    assert [memory["id"] for memory in single["relevant_memories"]] == ["memory-strong"]
    trimmed = [record for record in single["trace"]["selected"] if record["target_id"] == "memory-wrong-window"]
    assert trimmed == []  # ranked but not selected

    both = VNextRetrievalService(build_store(), embedding_provider=provider).compile_context_pack(
        VNextRetrievalRequest(query="What vendor contract decision did we sign in March 2023?", max_items=2)
    )
    assert [memory["id"] for memory in both["relevant_memories"]] == [
        "memory-strong",
        "memory-wrong-window",
    ]


def test_temporal_anchor_boosts_right_dated_source_in_fused_sources_stage() -> None:
    # Both sources surface lexically (wrong-dated first); the anchor
    # re-ranks the candidates the other lists already found — the
    # connector-stamped metadata date inside the window wins the boost.
    source_wrong = {
        "id": "source-wrong-date",
        "source_type": "chat_session",
        "title": "Museum outing chat",
        "content_hash": "sha256:wrong",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"session_id": "s1", "session_date": "2022/08/01 (Mon) 09:00"},
    }
    source_right = {
        "id": "source-right-date",
        "source_type": "chat_session",
        "title": "Museum outing chat",
        "content_hash": "sha256:right",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"session_id": "s2", "session_date": "2023/03/20 (Mon) 10:00"},
    }
    store = InMemoryVNextRetrievalStore(memories=[], sources=[source_wrong, source_right])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Which museum did I visit in March 2023?")
    )

    assert [source["id"] for source in pack["sources"]][:2] == ["source-right-date", "source-wrong-date"]
    sources_record = pack["trace"]["stages"]["sources"]
    assert sources_record[SOURCE_STAGE_TEMPORAL] == 1
    assert sources_record["source"] == "rrf(chunk_fts+provenance+title_recency+temporal_anchor)"


def test_temporal_stage_degrades_honestly_for_stores_without_time_search() -> None:
    class NoTimeSearchStore(InMemoryVNextRetrievalStore):
        search_memories_by_time = None  # store predates the method

    store = NoTimeSearchStore(
        memories=[_memory_row("memory-1", "Museum visit with a friend downtown")],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Which museum did I visit in March 2023?")
    )

    stage = pack["trace"]["stages"]["temporal_anchor"]
    assert stage["status"] == TEMPORAL_STAGE_DISABLED_NO_STORE_SUPPORT
    assert stage["candidate_count"] == 0
    # Recall itself is unaffected: the FTS stage still answers.
    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-1"]
    for record in pack["trace"]["selected"]:
        assert "temporal_anchor" not in record["stage_ranks"]


def test_minimal_depth_skips_the_temporal_stage_with_honest_status() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Museum visit downtown", valid_from="2023-03-15T00:00:00Z")],
        sources=[],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Which museum did I visit in March 2023?", context_depth="minimal")
    )

    stage = pack["trace"]["stages"]["temporal_anchor"]
    assert stage["status"] == STAGE_DISABLED_MINIMAL
    assert stage["candidate_count"] == 0
    assert store.time_search_calls == []


def test_reference_time_resolves_relative_phrases_deterministically() -> None:
    # "last week" against the caller-provided reference (a Tuesday) is the
    # previous ISO week; the dated memory surfaces through the temporal
    # list alone (zero lexical overlap with the query).
    dated = _memory_row(
        "memory-vendor-call",
        "Vendor kickoff call summary",
        valid_from="2023-04-12T00:00:00Z",
    )
    store = InMemoryVNextRetrievalStore(memories=[dated], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="what happened last week",
            reference_time=datetime(2023, 4, 18, 3, 31, tzinfo=UTC),
        )
    )

    stage = pack["trace"]["stages"]["temporal_anchor"]
    assert stage["window"] == ["2023-04-10T00:00:00+00:00", "2023-04-17T00:00:00+00:00"]
    assert stage["parsed_from"] == "last week"
    assert [memory["id"] for memory in pack["relevant_memories"]] == ["memory-vendor-call"]


def test_before_today_window_excludes_rows_first_seen_today() -> None:
    # "before today" is an open window ending at today's start, so rows
    # whose only event signal is a same-day ingest timestamp cannot ride
    # the temporal list into fusion (regression: the phrase must not parse
    # as the "today" window itself).
    ingested_today = _memory_row(
        "memory-ingested-today",
        "Airline booking note",
        first_seen_at="2023-04-18T03:00:00Z",
    )
    older = _memory_row(
        "memory-older",
        "Airline booking confirmation from spring",
        first_seen_at="2023-04-02T09:00:00Z",
    )
    store = InMemoryVNextRetrievalStore(memories=[ingested_today, older], sources=[])

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="Which airline did I book before today?",
            reference_time=datetime(2023, 4, 18, 3, 31, tzinfo=UTC),
        )
    )

    stage = pack["trace"]["stages"]["temporal_anchor"]
    assert stage["parsed_from"] == "before today"
    assert stage["window"][1] == "2023-04-18T00:00:00+00:00"
    assert stage["candidate_count"] == 1
    older_record = [record for record in pack["trace"]["selected"] if record["target_id"] == "memory-older"]
    assert older_record[0]["stage_ranks"]["temporal_anchor"] == 1
    today_record = [record for record in pack["trace"]["selected"] if record["target_id"] == "memory-ingested-today"]
    assert "temporal_anchor" not in today_record[0]["stage_ranks"]


class OccurrenceReaderStore(InMemoryVNextRetrievalStore):
    def __init__(
        self,
        *,
        memories: list[dict[str, object]],
        units: list[dict[str, object]],
        evidence: list[dict[str, object]],
        coverage: dict[str, object] | None,
        unresolved: list[dict[str, object]] | None = None,
        sources: list[dict[str, object]] | None = None,
        source_chunks: list[dict[str, object]] | None = None,
        internal_unit_cap: int | None = None,
        internal_evidence_cap: int | None = None,
        internal_unresolved_cap: int | None = None,
        snapshot_proof: Mapping[str, object] | None = None,
        fail_snapshot_end: bool = False,
        skip_probed_unit_on_followup: bool = False,
        skip_probed_evidence_on_followup: bool = False,
        skip_probed_unresolved_on_followup: bool = False,
    ) -> None:
        super().__init__(
            memories=memories,
            sources=sources or [],
            source_chunks=source_chunks or [],
        )
        self.occurrence_units = sorted(units, key=lambda row: str(row["id"]))
        self.occurrence_evidence = evidence
        self.occurrence_coverage = coverage
        self.unresolved_occurrence_claims = sorted(unresolved or [], key=lambda row: str(row["id"]))
        self.internal_unit_cap = internal_unit_cap
        self.internal_evidence_cap = internal_evidence_cap
        self.internal_unresolved_cap = internal_unresolved_cap
        self.snapshot_proof = dict(
            snapshot_proof
            or {
                "proof": "occurrence_read_snapshot_v1",
                "acquired": True,
                "backend": "sqlite",
                "mode": "transaction_snapshot",
                "lifecycle_as_of": datetime(
                    2026,
                    7,
                    25,
                    12,
                    tzinfo=UTC,
                ),
            }
        )
        self.fail_snapshot_end = fail_snapshot_end
        self.skip_probed_unit_on_followup = skip_probed_unit_on_followup
        self.skip_probed_evidence_on_followup = skip_probed_evidence_on_followup
        self.skip_probed_unresolved_on_followup = skip_probed_unresolved_on_followup
        self.snapshot_calls = 0
        self.snapshot_end_calls = 0
        self.occurrence_search_calls: list[dict[str, object]] = []
        self.evidence_search_calls: list[dict[str, object]] = []
        self.unresolved_search_calls: list[dict[str, object]] = []

    def begin_occurrence_read_snapshot(self) -> dict[str, object]:
        self.snapshot_calls += 1
        return dict(self.snapshot_proof)

    def end_occurrence_read_snapshot(self) -> None:
        self.snapshot_end_calls += 1
        if self.fail_snapshot_end:
            raise RuntimeError("snapshot cleanup failed")

    def search_accepted_occurrence_units_by_selector(
        self,
        *,
        selector_key: str,
        projects: tuple[str, ...] | None = None,
        domains: tuple[str, ...] | None = None,
        sensitivity_allowed: tuple[str, ...] | None = None,
        occurred_at_start: datetime | None = None,
        occurred_at_end: datetime | None = None,
        include_timeless: bool = False,
        as_of: datetime | None = None,
        after_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        probe_was_seen = any(
            call["after_id"] == after_id and call["limit"] == 1 for call in self.occurrence_search_calls
        )
        self.occurrence_search_calls.append(
            {
                "selector_key": selector_key,
                "projects": projects,
                "domains": domains,
                "sensitivity_allowed": sensitivity_allowed,
                "occurred_at_start": occurred_at_start,
                "occurred_at_end": occurred_at_end,
                "include_timeless": include_timeless,
                "as_of": as_of,
                "after_id": after_id,
                "limit": limit,
            }
        )
        wanted_projects = set(projects or ())
        wanted_domains = set(domains or ())
        wanted_sensitivity = set(sensitivity_allowed or ())
        rows = [
            row
            for row in self.occurrence_units
            if (after_id is None or str(row["id"]) > after_id)
            and selector_key
            in set(
                row.get("predicate_json", {}).get("selector_keys", [])
                if isinstance(row.get("predicate_json"), Mapping)
                else ()
            )
            and (not wanted_projects or wanted_projects.intersection(row.get("project_scope", [])))
            and (not wanted_domains or row.get("domain") in wanted_domains)
            and (not wanted_sensitivity or row.get("sensitivity") in wanted_sensitivity)
            and _occurrence_test_row_overlaps(
                row,
                occurred_at_start=occurred_at_start,
                occurred_at_end=occurred_at_end,
                include_timeless=include_timeless,
            )
            and _occurrence_test_lifecycle_visible(row, as_of=as_of)
        ]
        effective_limit = min(limit, self.internal_unit_cap) if self.internal_unit_cap is not None else limit
        page = rows[:effective_limit]
        if self.skip_probed_unit_on_followup and probe_was_seen and limit > 1 and page:
            return page[1:]
        return page

    def list_accepted_occurrence_units(
        self,
        *,
        projects: tuple[str, ...] | None = None,
        domains: tuple[str, ...] | None = None,
        sensitivity_allowed: tuple[str, ...] | None = None,
        occurred_at_start: datetime | None = None,
        occurred_at_end: datetime | None = None,
        include_timeless: bool = False,
        as_of: datetime | None = None,
        after_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        probe_was_seen = any(
            call["after_id"] == after_id and call["limit"] == 1 for call in self.occurrence_search_calls
        )
        self.occurrence_search_calls.append(
            {
                "selector_key": None,
                "projects": projects,
                "domains": domains,
                "sensitivity_allowed": sensitivity_allowed,
                "occurred_at_start": occurred_at_start,
                "occurred_at_end": occurred_at_end,
                "include_timeless": include_timeless,
                "as_of": as_of,
                "after_id": after_id,
                "limit": limit,
            }
        )
        wanted_projects = set(projects or ())
        wanted_domains = set(domains or ())
        wanted_sensitivity = set(sensitivity_allowed or ())
        rows = [
            row
            for row in self.occurrence_units
            if (after_id is None or str(row["id"]) > after_id)
            and (not wanted_projects or wanted_projects.intersection(row.get("project_scope", [])))
            and (not wanted_domains or row.get("domain") in wanted_domains)
            and (not wanted_sensitivity or row.get("sensitivity") in wanted_sensitivity)
            and _occurrence_test_row_overlaps(
                row,
                occurred_at_start=occurred_at_start,
                occurred_at_end=occurred_at_end,
                include_timeless=include_timeless,
            )
            and _occurrence_test_lifecycle_visible(row, as_of=as_of)
        ]
        effective_limit = min(limit, self.internal_unit_cap) if self.internal_unit_cap is not None else limit
        page = rows[:effective_limit]
        if self.skip_probed_unit_on_followup and probe_was_seen and limit > 1 and page:
            return page[1:]
        return page

    def search_accepted_occurrence_units(
        self,
        *,
        query: str,
        exact_count_key: str | None = None,
        projects: tuple[str, ...] | None = None,
        domains: tuple[str, ...] | None = None,
        sensitivity_allowed: tuple[str, ...] | None = None,
        occurred_at_start: datetime | None = None,
        occurred_at_end: datetime | None = None,
        include_timeless: bool = False,
        as_of: datetime | None = None,
        after_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        probe_was_seen = any(
            call["after_id"] == after_id and call["limit"] == 1 for call in self.occurrence_search_calls
        )
        self.occurrence_search_calls.append(
            {
                "query": query,
                "exact_count_key": exact_count_key,
                "projects": projects,
                "domains": domains,
                "sensitivity_allowed": sensitivity_allowed,
                "occurred_at_start": occurred_at_start,
                "occurred_at_end": occurred_at_end,
                "include_timeless": include_timeless,
                "as_of": as_of,
                "after_id": after_id,
                "limit": limit,
            }
        )
        rows = [
            row
            for row in self.occurrence_units
            if (after_id is None or str(row["id"]) > after_id)
            and (exact_count_key is None or str(row.get("count_key") or "") == exact_count_key)
            and _occurrence_test_row_overlaps(
                row,
                occurred_at_start=occurred_at_start,
                occurred_at_end=occurred_at_end,
                include_timeless=include_timeless,
            )
        ]
        effective_limit = min(limit, self.internal_unit_cap) if self.internal_unit_cap is not None else limit
        page = rows[:effective_limit]
        if self.skip_probed_unit_on_followup and probe_was_seen and limit > 1 and page:
            return page[1:]
        return page

    def list_occurrence_evidence_for_units(
        self,
        occurrence_ids: tuple[str, ...] | list[str],
        *,
        as_of: datetime | None = None,
        after_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        probe_was_seen = any(call["after_id"] == after_id and call["limit"] == 1 for call in self.evidence_search_calls)
        self.evidence_search_calls.append(
            {
                "occurrence_ids": tuple(occurrence_ids),
                "as_of": as_of,
                "after_id": after_id,
                "limit": limit,
            }
        )
        wanted = set(occurrence_ids)
        rows = [
            row
            for row in sorted(
                self.occurrence_evidence,
                key=lambda item: str(item.get("id") or ""),
            )
            if str(row.get("occurrence_id")) in wanted and (after_id is None or str(row.get("id") or "") > after_id)
        ]
        effective_limit = min(limit, self.internal_evidence_cap) if self.internal_evidence_cap is not None else limit
        page = rows[:effective_limit]
        if self.skip_probed_evidence_on_followup and probe_was_seen and limit > 1 and page:
            return page[1:]
        return page

    def get_source_chunks_by_ids(
        self,
        source_chunk_ids: tuple[str, ...] | list[str],
    ) -> list[dict[str, object]]:
        wanted = set(source_chunk_ids)
        return [row for row in self.source_chunks if str(row.get("id")) in wanted]

    def get_occurrence_coverage(self) -> dict[str, object] | None:
        return self.occurrence_coverage

    def list_accepted_occurrence_extraction_dispositions_for_claims(
        self,
        claim_ids: tuple[str, ...] | list[str],
        *,
        limit: int = 201,
    ) -> list[dict[str, object]]:
        del claim_ids, limit
        return []

    def summarize_occurrence_extraction_accounting(
        self,
        *,
        extractor_version: str,
        source_ids: tuple[str, ...] | list[str] | None = None,
    ) -> dict[str, object]:
        del source_ids
        metadata = (
            self.occurrence_coverage.get("metadata_json") if isinstance(self.occurrence_coverage, Mapping) else None
        )
        if not isinstance(metadata, Mapping):
            return {"complete": False, "items": []}
        unresolved_ids = [str(row["id"]) for row in self.unresolved_occurrence_claims]
        unit_ids = [str(row["id"]) for row in self.occurrence_units]
        claim_ids = sorted(
            {
                str(row["claim_id"])
                for row in [
                    *self.occurrence_units,
                    *self.unresolved_occurrence_claims,
                ]
                if row.get("claim_id") is not None
            }
            | {str(row["id"]) for row in self.unresolved_occurrence_claims if row.get("id") is not None}
        )
        unresolved = bool(unresolved_ids)
        return {
            "extractor_version": extractor_version,
            "source_ids": list(metadata["source_ids"]),
            "source_chunk_ids": list(metadata["source_chunk_ids"]),
            "current_chunk_count": 1,
            "reviewed_current_count": 1,
            "missing_count": 0,
            "stale_count": 0,
            "unresolved_count": len(unresolved_ids),
            "unreviewed_count": 0,
            "invalid_accepted_count": 0,
            "invalid_receipt_count": 0,
            "unanchored_memory_count": 0,
            "unanchored_memory_ids": [],
            "accounted_memory_count": len(self.memories),
            "accounted_memory_ids": sorted(str(row["id"]) for row in self.memories),
            "snapshot_digest": metadata["snapshot_digest"],
            "disposition_digest": metadata["disposition_digest"],
            "complete": True,
            "items": [
                {
                    "source_id": _OCCURRENCE_TEST_SOURCE_ID,
                    "source_chunk_id": _OCCURRENCE_TEST_CHUNK_ID,
                    "snapshot_sha256": "c" * 64,
                    "disposition_id": _OCCURRENCE_TEST_DISPOSITION_ID,
                    "disposition": ("unresolved_claims" if unresolved else "accepted_occurrences"),
                    "review_status": "accepted",
                    "review_version": 1,
                    "predicate_keys": sorted(
                        {
                            str(selector)
                            for row in [
                                *self.occurrence_units,
                                *self.unresolved_occurrence_claims,
                            ]
                            if isinstance(row.get("predicate_json"), Mapping)
                            for selector in row["predicate_json"].get(
                                "selector_keys",
                                [],
                            )
                        }
                    ),
                    "claim_ids": claim_ids,
                    "occurrence_ids": unit_ids,
                    "status": ("complete_with_unresolved_claims" if unresolved else "complete"),
                }
            ],
        }

    def list_unresolved_occurrence_claims(
        self,
        *,
        count_key: str | None,
        projects: tuple[str, ...] | None = None,
        domains: tuple[str, ...] | None = None,
        sensitivity_allowed: tuple[str, ...] | None = None,
        occurred_at_start: datetime | None = None,
        occurred_at_end: datetime | None = None,
        include_timeless: bool = False,
        as_of: datetime | None = None,
        after_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        probe_was_seen = any(
            call["after_id"] == after_id and call["limit"] == 1 for call in self.unresolved_search_calls
        )
        self.unresolved_search_calls.append(
            {
                "count_key": count_key,
                "projects": projects,
                "domains": domains,
                "sensitivity_allowed": sensitivity_allowed,
                "occurred_at_start": occurred_at_start,
                "occurred_at_end": occurred_at_end,
                "include_timeless": include_timeless,
                "as_of": as_of,
                "after_id": after_id,
                "limit": limit,
            }
        )
        rows = [
            row
            for row in self.unresolved_occurrence_claims
            if (count_key is None or row.get("count_key") == count_key)
            and (after_id is None or str(row["id"]) > after_id)
            and _occurrence_test_row_overlaps(
                row,
                occurred_at_start=occurred_at_start,
                occurred_at_end=occurred_at_end,
                include_timeless=include_timeless,
            )
        ]
        effective_limit = (
            min(limit, self.internal_unresolved_cap) if self.internal_unresolved_cap is not None else limit
        )
        page = rows[:effective_limit]
        if self.skip_probed_unresolved_on_followup and probe_was_seen and limit > 1 and page:
            return page[1:]
        return page


def _occurrence_test_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _occurrence_test_lifecycle_visible(
    row: Mapping[str, object],
    *,
    as_of: datetime | None,
) -> bool:
    updated_at = _occurrence_test_datetime(row.get("updated_at"))
    return as_of is None or updated_at is None or updated_at <= as_of


def _occurrence_test_row_overlaps(
    row: Mapping[str, object],
    *,
    occurred_at_start: datetime | None,
    occurred_at_end: datetime | None,
    include_timeless: bool,
) -> bool:
    row_start = _occurrence_test_datetime(row.get("occurred_at_start"))
    row_end = _occurrence_test_datetime(row.get("occurred_at_end"))
    if row_start is None and row_end is None:
        return include_timeless
    effective_start = row_start or row_end
    effective_end = row_end or row_start
    assert effective_start is not None
    assert effective_end is not None
    return not (
        (occurred_at_start is not None and effective_end < occurred_at_start)
        or (occurred_at_end is not None and effective_start > occurred_at_end)
    )


def _occurrence_test_predicate() -> dict[str, object]:
    return build_occurrence_predicate_atom(
        action="service",
        object_leaf="bike",
    )


def _occurrence_test_unit_aggregation(
    occurrence_key: str,
) -> dict[str, object]:
    return {
        "schema": OCCURRENCE_AGGREGATION_SCHEMA,
        "members": [
            {
                "basis": "event_instance",
                "identity_basis": "occurrence_key",
                "member_identity": occurrence_key,
            }
        ],
    }


def _occurrence_test_claim_aggregation() -> dict[str, object]:
    return {
        "schema": OCCURRENCE_AGGREGATION_SCHEMA,
        "bases": [
            {
                "basis": "event_instance",
                "identity_basis": "occurrence_key",
            }
        ],
    }


def _resign_occurrence_test_unit(
    unit: dict[str, object],
    evidence_rows: list[dict[str, object]],
) -> None:
    evidence_digest = sha256(
        "|".join(
            occurrence_evidence_facts_digest(row)
            for row in sorted(
                evidence_rows,
                key=lambda row: (
                    str(row["evidence_key"]),
                    str(row["id"]),
                ),
            )
        ).encode()
    ).hexdigest()
    unit["reviewed_evidence_count"] = len(evidence_rows)
    unit["reviewed_evidence_digest"] = evidence_digest
    unit_receipt = occurrence_unit_review_receipt_digest(
        unit,
        action=str(unit["review_receipt_action"]),
        reviewer_id=str(unit["reviewer_id"]),
        reason=str(unit["review_reason"]),
        review_version=int(unit["review_version"]),
        evidence_digest=evidence_digest,
    )
    unit["review_receipt_digest"] = unit_receipt
    for row in evidence_rows:
        row["unit_review_receipt_digest"] = unit_receipt
        row["review_receipt_digest"] = occurrence_evidence_review_receipt_digest(
            row,
            action=str(row["review_receipt_action"]),
            reviewer_id=str(row["reviewer_id"]),
            reason=str(row["review_reason"]),
            unit_review_receipt_digest=unit_receipt,
        )


def _retarget_occurrence_test_unit(
    unit: dict[str, object],
    evidence_rows: list[dict[str, object]],
    *,
    action: str,
    object_leaf: str,
    count_key: str,
    canonical_text: str,
) -> None:
    unit["count_key"] = count_key
    unit["canonical_text"] = canonical_text
    unit["predicate_json"] = build_occurrence_predicate_atom(
        action=action,
        object_leaf=object_leaf,
    )
    _resign_occurrence_test_unit(unit, evidence_rows)


def _occurrence_test_unresolved_claim(
    claim_id: str,
    *,
    quantity_min: int = 1,
    quantity_max: int | None = 1,
    range_kind: str = "exact",
    action: str = "service",
    object_leaf: str = "bike",
    count_key: str = "bike service",
    occurred_at_start: str | None = "2026-05-01T00:00:00Z",
    occurred_at_end: str | None = "2026-05-01T00:00:00Z",
) -> dict[str, object]:
    return {
        "id": claim_id,
        "user_id": "user-1",
        "claim_key": f"fixture:{claim_id}",
        "count_key": count_key,
        "canonical_text": f"Unresolved {count_key} occurrence.",
        "quantity_min": quantity_min,
        "quantity_max": quantity_max,
        "range_kind": range_kind,
        "resolution_status": "pending",
        "resolution_decision": "ambiguous",
        "identity_basis": "ambiguous",
        "resolved_occurrence_id": None,
        "review_status": "candidate",
        "predicate_json": build_occurrence_predicate_atom(
            action=action,
            object_leaf=object_leaf,
        ),
        "aggregation_json": _occurrence_test_claim_aggregation(),
        "domain": "personal",
        "sensitivity": "private",
        "project_scope": [],
        "occurred_at_start": occurred_at_start,
        "occurred_at_end": occurred_at_end,
    }


def _reviewed_occurrence_rows(
    count: int = 2,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    memories: list[dict[str, object]] = []
    units: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for index in range(1, count + 1):
        occurrence_id = f"occurrence-{index:03d}"
        memory_id = f"memory-occurrence-{index:03d}"
        evidence_id = f"evidence-{index:03d}"
        evidence_key = f"bike-service-evidence-{index:03d}"
        quote = f"bike service {index}"
        quote_sha256 = sha256(quote.encode()).hexdigest()
        review_reason = "reviewed occurrence evidence"
        memories.append(
            _memory_row(
                memory_id,
                f"Bike service occurrence {index}",
                domain="personal",
                sensitivity="private",
                project_id="bike",
            )
        )
        occurrence_key = f"{index:064x}"
        unit: dict[str, object] = {
            "id": occurrence_id,
            "user_id": "user-1",
            "claim_id": f"claim-{index:03d}",
            "claim_ordinal": 1,
            "occurrence_key": occurrence_key,
            "count_key": "bike service",
            "canonical_text": f"Bike service occurrence {index}",
            "unit_value": 1,
            "review_status": "accepted",
            "identity_status": "resolved",
            "ambiguity_group_key": None,
            "predicate_json": _occurrence_test_predicate(),
            "aggregation_json": _occurrence_test_unit_aggregation(occurrence_key),
            "domain": "personal",
            "sensitivity": "private",
            "project_scope": ["bike"],
            "occurred_at_start": "2026-01-10T12:00:00Z",
            "occurred_at_end": "2026-01-10T12:00:00Z",
            "reviewed_at": "2026-07-01T00:00:00Z",
            "reviewer_id": "reviewer-1",
            "review_reason": review_reason,
            "review_receipt_action": "accepted",
            "review_version": 1,
            "superseded_by": None,
            "retired_at": None,
        }
        evidence_row: dict[str, object] = {
            "id": evidence_id,
            "user_id": "user-1",
            "claim_id": f"claim-{index:03d}",
            "occurrence_id": occurrence_id,
            "memory_id": memory_id,
            "source_id": None,
            "source_chunk_id": None,
            "evidence_key": evidence_key,
            "evidence_role": "supports",
            "quote": quote,
            "quote_sha256": quote_sha256,
            "review_status": "accepted",
            "review_receipt_action": "accepted",
            "reviewer_id": "reviewer-1",
            "review_reason": review_reason,
        }
        _resign_occurrence_test_unit(unit, [evidence_row])
        units.append(unit)
        evidence.append(evidence_row)
    return memories, units, evidence


def _reviewed_occurrence_with_shared_evidence(
    evidence_count: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    memories, units, _evidence = _reviewed_occurrence_rows(1)
    unit = units[0]
    evidence: list[dict[str, object]] = []
    memories = []
    for index in range(1, evidence_count + 1):
        memory_id = f"memory-shared-{index:04d}"
        evidence_id = f"evidence-shared-{index:04d}"
        evidence_key = f"bike-service-shared-{index:04d}"
        quote_sha256 = sha256(f"shared bike service evidence {index}".encode()).hexdigest()
        memories.append(
            _memory_row(
                memory_id,
                f"Bike service evidence carrier {index}",
                domain="personal",
                sensitivity="private",
                project_id="bike",
            )
        )
        evidence.append(
            {
                "id": evidence_id,
                "user_id": "user-1",
                "claim_id": unit["claim_id"],
                "occurrence_id": unit["id"],
                "memory_id": memory_id,
                "source_id": None,
                "source_chunk_id": None,
                "evidence_key": evidence_key,
                "evidence_role": "supports",
                "quote": f"shared bike service evidence {index}",
                "quote_sha256": quote_sha256,
                "review_status": "accepted",
                "review_receipt_action": "accepted",
                "reviewer_id": "reviewer-1",
                "review_reason": "reviewed occurrence evidence",
            }
        )
    _resign_occurrence_test_unit(unit, evidence)
    return memories, units, evidence


def _complete_occurrence_coverage() -> dict[str, object]:
    accounting = {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": _OCCURRENCE_TEST_EXTRACTOR_VERSION,
        "source_ids": [_OCCURRENCE_TEST_SOURCE_ID],
        "source_chunk_ids": [_OCCURRENCE_TEST_CHUNK_ID],
        "snapshot_digest": "a" * 64,
        "disposition_digest": "b" * 64,
    }
    coverage: dict[str, object] = {
        "id": "coverage-1",
        "user_id": "user-1",
        "coverage_mode": "complete_history",
        "coverage_started_at": "2020-01-01T00:00:00Z",
        "historical_review_status": "reviewed",
        "complete_through": "2026-12-31T23:59:59Z",
        "review_version": 1,
        "reviewer_id": "reviewer-1",
        "review_reason": "Reviewed the complete occurrence history.",
        "metadata_json": accounting,
    }
    coverage["review_receipt_digest"] = occurrence_coverage_review_receipt_digest(
        coverage_id=str(coverage["id"]),
        user_id=str(coverage["user_id"]),
        review_version=int(coverage["review_version"]),
        coverage_mode=str(coverage["coverage_mode"]),
        coverage_started_at=str(coverage["coverage_started_at"]),
        historical_review_status=str(coverage["historical_review_status"]),
        complete_through=str(coverage["complete_through"]),
        reviewer_id=str(coverage["reviewer_id"]),
        reason=str(coverage["review_reason"]),
        accounting_metadata=accounting,
    )
    return coverage


def _forward_occurrence_coverage() -> dict[str, object]:
    coverage: dict[str, object] = {
        "id": "coverage-forward",
        "user_id": "user-1",
        "coverage_mode": "forward_only",
        "coverage_started_at": "2026-01-01T00:00:00Z",
        "historical_review_status": "not_reviewed",
        "complete_through": None,
        "review_version": 1,
        "reviewer_id": "reviewer-1",
        "review_reason": "Reviewed forward-only occurrence coverage.",
        "metadata_json": {},
    }
    coverage["review_receipt_digest"] = occurrence_coverage_review_receipt_digest(
        coverage_id=str(coverage["id"]),
        user_id=str(coverage["user_id"]),
        review_version=int(coverage["review_version"]),
        coverage_mode=str(coverage["coverage_mode"]),
        coverage_started_at=str(coverage["coverage_started_at"]),
        historical_review_status=str(coverage["historical_review_status"]),
        complete_through=None,
        reviewer_id=str(coverage["reviewer_id"]),
        reason=str(coverage["review_reason"]),
        accounting_metadata=None,
    )
    return coverage


def _configure_sqlite_occurrence_coverage(
    store: SQLiteVNextStore,
    *,
    complete_through: datetime,
) -> None:
    extractor_version = _OCCURRENCE_TEST_EXTRACTOR_VERSION
    chunks = store.conn.execute(
        """
        SELECT chunk.id
        FROM source_chunks AS chunk
        JOIN sources AS source
          ON source.id = chunk.source_id
         AND source.user_id = chunk.user_id
        WHERE chunk.user_id = ?
          AND source.deleted_at IS NULL
        ORDER BY chunk.id ASC
        """,
        (store.user_id,),
    ).fetchall()
    for (source_chunk_id,) in chunks:
        evidence_rows = store.conn.execute(
            """
            SELECT
              claim.id,
              claim.resolution_status,
              claim.review_status,
              evidence.occurrence_id
            FROM occurrence_evidence AS evidence
            JOIN occurrence_claims AS claim
              ON claim.id = evidence.claim_id
             AND claim.user_id = evidence.user_id
            WHERE evidence.user_id = ?
              AND evidence.source_chunk_id = ?
              AND evidence.evidence_role = 'supports'
              AND evidence.review_status IN ('candidate', 'accepted')
            ORDER BY claim.id ASC, evidence.occurrence_id ASC
            """,
            (store.user_id, str(source_chunk_id)),
        ).fetchall()
        claim_ids = sorted({str(row[0]) for row in evidence_rows})
        occurrence_ids = sorted(
            {
                str(row[3])
                for row in evidence_rows
                if row[3] is not None and row[1] == "resolved" and row[2] == "accepted"
            }
        )
        has_unresolved = any(row[1] == "pending" and row[2] == "candidate" for row in evidence_rows)
        disposition = (
            "no_occurrence" if not evidence_rows else "unresolved_claims" if has_unresolved else "accepted_occurrences"
        )
        recorded, _created = store.record_occurrence_extraction_disposition(
            source_chunk_id=str(source_chunk_id),
            extractor_version=extractor_version,
            disposition=disposition,
            claim_ids=claim_ids,
            occurrence_ids=occurrence_ids,
        )
        if recorded["review_status"] == "candidate":
            store.review_occurrence_extraction_disposition(
                disposition_id=str(recorded["id"]),
                action="accepted",
                reviewer_id="reviewer-1",
                reason="Reviewed complete retrieval accounting fixture.",
                expected_review_version=int(recorded["review_version"]),
            )
    accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
    )
    accounting_metadata = {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": extractor_version,
        "source_ids": accounting["source_ids"],
        "source_chunk_ids": accounting["source_chunk_ids"],
        "snapshot_digest": accounting["snapshot_digest"],
        "disposition_digest": accounting["disposition_digest"],
    }
    store.ensure_occurrence_coverage(started_at="2020-01-01T00:00:00Z")
    store.review_occurrence_coverage(
        coverage_mode="complete_history",
        historical_review_status="reviewed",
        reviewer_id="reviewer-1",
        reason="Reviewed complete bike-service history.",
        coverage_started_at="2020-01-01T00:00:00Z",
        complete_through=complete_through,
        accounting_metadata=accounting_metadata,
        expected_review_version=0,
    )


def _create_sqlite_reviewed_occurrence(
    store: SQLiteVNextStore,
    *,
    index: int,
    occurred_at: str,
    count_key: str = "bike service",
    canonical_text: str | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    text = canonical_text or f"Bike service occurrence {index}."
    if count_key == "bike service":
        predicate = build_occurrence_predicate_atom(
            action="service",
            object_leaf="bike",
        )
    elif count_key == "attend parties":
        predicate = build_occurrence_predicate_atom(
            action="attend",
            object_leaf="parties",
        )
    else:
        raise AssertionError(f"unsupported retrieval fixture count key: {count_key}")
    source = store.create_source(
        {
            "source_type": "document",
            "content_hash": f"sha256:bike-service-{index}",
            "domain": "personal",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["bike"]},
        }
    )
    source_chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": text,
        }
    )
    memory = store.create_memory(
        {
            "memory_key": f"bike-service-{index}",
            "value": {"text": text},
            "status": "active",
            "canonical_text": text,
            "domain": "personal",
            "sensitivity": "private",
            "project_id": "bike",
            "metadata_json": {
                "project_scope": ["bike"],
                "source_chunk_id": str(source_chunk["id"]),
            },
        }
    )
    claim, _created = store.get_or_create_occurrence_claim(
        {
            "claim_key": f"bike-service-claim-{index}",
            "count_key": count_key,
            "canonical_text": text,
            "quantity_min": 1,
            "quantity_max": 1,
            "range_kind": "exact",
            "predicate_json": predicate,
            "aggregation_json": _occurrence_test_claim_aggregation(),
            "resolution_decision": "new",
            "identity_basis": "exact_time",
            "occurred_at_start": occurred_at,
            "occurred_at_end": occurred_at,
            "domain": "personal",
            "sensitivity": "private",
            "project_scope": ["bike"],
        }
    )
    occurrence_key = f"{index:064x}"
    unit, _created = store.get_or_create_occurrence_unit(
        {
            "claim_id": str(claim["id"]),
            "claim_ordinal": 1,
            "occurrence_key": occurrence_key,
            "count_key": count_key,
            "canonical_text": text,
            "identity_status": "resolved",
            "predicate_json": predicate,
            "aggregation_json": _occurrence_test_unit_aggregation(occurrence_key),
            "occurred_at_start": occurred_at,
            "occurred_at_end": occurred_at,
            "domain": "personal",
            "sensitivity": "private",
            "project_scope": ["bike"],
        }
    )
    store.create_occurrence_evidence(
        {
            "claim_id": str(claim["id"]),
            "occurrence_id": str(unit["id"]),
            "memory_id": str(memory["id"]),
            "source_id": str(source["id"]),
            "source_chunk_id": str(source_chunk["id"]),
            "evidence_key": f"bike-service-evidence-{index}",
            "evidence_role": "supports",
            "quote": text,
        }
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer-1",
        reason="Verified occurrence identity.",
    )
    accepted = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reviewer_id="reviewer-1",
        reason="Verified occurrence evidence.",
    )
    return memory, accepted


def _create_sqlite_pending_occurrence_claim(
    store: SQLiteVNextStore,
    *,
    index: int,
    occurred_at: str,
) -> tuple[dict[str, object], dict[str, object]]:
    predicate = _occurrence_test_predicate()
    source = store.create_source(
        {
            "source_type": "document",
            "content_hash": f"sha256:bike-service-pending-{index}",
            "domain": "personal",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["bike"]},
        }
    )
    source_chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": f"Pending bike service occurrence {index}.",
        }
    )
    memory = store.create_memory(
        {
            "memory_key": f"bike-service-pending-{index}",
            "value": {"text": f"Pending bike service occurrence {index}."},
            "status": "active",
            "canonical_text": f"Pending bike service occurrence {index}.",
            "domain": "personal",
            "sensitivity": "private",
            "project_id": "bike",
            "metadata_json": {
                "project_scope": ["bike"],
                "source_chunk_id": str(source_chunk["id"]),
            },
        }
    )
    claim, _created = store.get_or_create_occurrence_claim(
        {
            "claim_key": f"bike-service-pending-claim-{index}",
            "count_key": "bike service",
            "canonical_text": f"Pending bike service occurrence {index}.",
            "quantity_min": 1,
            "quantity_max": 1,
            "range_kind": "exact",
            "predicate_json": predicate,
            "aggregation_json": _occurrence_test_claim_aggregation(),
            "resolution_decision": "ambiguous",
            "identity_basis": "ambiguous",
            "occurred_at_start": occurred_at,
            "occurred_at_end": occurred_at,
            "domain": "personal",
            "sensitivity": "private",
            "project_scope": ["bike"],
        }
    )
    store.create_occurrence_evidence(
        {
            "claim_id": str(claim["id"]),
            "occurrence_id": None,
            "memory_id": str(memory["id"]),
            "source_id": str(source["id"]),
            "source_chunk_id": str(source_chunk["id"]),
            "evidence_key": f"bike-service-pending-evidence-{index}",
            "evidence_role": "supports",
            "quote": f"Pending bike service occurrence {index}.",
        }
    )
    return memory, claim


def test_sqlite_occurrence_reader_does_not_turn_two_units_into_exact_one_when_evidence_expires() -> None:
    store = _sqlite_retrieval_store()
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    _live_memory, _live_unit = _create_sqlite_reviewed_occurrence(
        store,
        index=1,
        occurred_at="2026-07-01T12:00:00Z",
    )
    stale_memory, _stale_unit = _create_sqlite_reviewed_occurrence(
        store,
        index=2,
        occurred_at="2026-07-02T12:00:00Z",
    )
    _configure_sqlite_occurrence_coverage(
        store,
        complete_through=reference_time,
    )
    store.conn.execute(
        "UPDATE memories SET valid_to = ? WHERE id = ?",
        ("2026-07-10T00:00:00Z", str(stale_memory["id"])),
    )
    store.conn.commit()

    candidates = store.search_accepted_occurrence_units(
        query="How many times did I service my bike?",
        projects=("bike",),
        domains=("personal",),
        sensitivity_allowed=("private",),
        occurred_at_end=reference_time,
        include_timeless=True,
        as_of=reference_time,
    )
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            projects=("bike",),
            domains=("personal",),
            sensitivity_allowed=("private",),
            reference_time=reference_time,
        )
    )

    assert len(candidates) == 2
    assert "aggregation" not in pack


def test_sqlite_occurrence_reader_keeps_stale_pending_claim_as_exactness_blocker() -> None:
    store = _sqlite_retrieval_store()
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    _live_memory, _live_unit = _create_sqlite_reviewed_occurrence(
        store,
        index=1,
        occurred_at="2026-07-01T12:00:00Z",
    )
    stale_memory, pending_claim = _create_sqlite_pending_occurrence_claim(
        store,
        index=2,
        occurred_at="2026-07-02T12:00:00Z",
    )
    store.conn.execute(
        "UPDATE memories SET valid_to = ? WHERE id = ?",
        ("2026-07-10T00:00:00Z", str(stale_memory["id"])),
    )
    store.conn.commit()
    _configure_sqlite_occurrence_coverage(
        store,
        complete_through=reference_time,
    )

    unresolved = store.list_unresolved_occurrence_claims(
        count_key="bike service",
        projects=("bike",),
        domains=("personal",),
        sensitivity_allowed=("private",),
        occurred_at_end=reference_time,
        include_timeless=True,
        as_of=reference_time,
    )
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            projects=("bike",),
            domains=("personal",),
            sensitivity_allowed=("private",),
            reference_time=reference_time,
        )
    )

    assert [row["id"] for row in unresolved] == [pending_claim["id"]]
    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["lower_bound"] == 1
    assert pack["aggregation"]["upper_bound"] == 2
    assert "count" not in pack["aggregation"]


def test_sqlite_occurrence_reader_batches_more_than_999_evidence_carriers(
    monkeypatch,
) -> None:
    store = _sqlite_retrieval_store()
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    owner_memory, accepted_unit = _create_sqlite_reviewed_occurrence(
        store,
        index=1,
        occurred_at="2026-07-01T12:00:00Z",
    )
    claim_id = str(accepted_unit["claim_id"])
    occurrence_id = str(accepted_unit["id"])
    owner_metadata = owner_memory["metadata_json"]
    assert isinstance(owner_metadata, Mapping)
    source_chunk_id = str(owner_metadata["source_chunk_id"])
    source_id = str(
        store.conn.execute(
            "SELECT source_id FROM source_chunks WHERE id = ?",
            (source_chunk_id,),
        ).fetchone()[0]
    )
    for index in range(2, 1_002):
        memory = store.create_memory(
            {
                "memory_key": f"bike-service-carrier-{index}",
                "value": {"text": f"Additional bike service evidence {index}."},
                "status": "active",
                "canonical_text": (f"Additional bike service evidence {index}."),
                "domain": "personal",
                "sensitivity": "private",
                "project_id": "bike",
                "metadata_json": {
                    "project_scope": ["bike"],
                    "source_chunk_id": source_chunk_id,
                },
            }
        )
        store.create_occurrence_evidence(
            {
                "claim_id": claim_id,
                "occurrence_id": occurrence_id,
                "memory_id": str(memory["id"]),
                "source_id": source_id,
                "source_chunk_id": source_chunk_id,
                "evidence_key": f"bike-service-carrier-{index}",
                "evidence_role": "supports",
                "quote": f"Additional bike service evidence {index}.",
            }
        )
    store.refresh_occurrence_unit_evidence(
        occurrence_id=occurrence_id,
        reason="Reviewed the complete carrier set.",
        reviewer_id="reviewer-1",
        expected_review_version=int(accepted_unit["review_version"]),
    )
    store.conn.commit()
    _configure_sqlite_occurrence_coverage(
        store,
        complete_through=reference_time,
    )

    memory_batch_sizes: list[int] = []
    original_get_memories = store.get_memories_by_ids

    def recording_get_memories(
        memory_ids: tuple[str, ...],
    ) -> list[dict[str, object]]:
        memory_batch_sizes.append(len(memory_ids))
        return original_get_memories(memory_ids)

    monkeypatch.setattr(
        store,
        "get_memories_by_ids",
        recording_get_memories,
    )
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            projects=("bike",),
            domains=("personal",),
            sensitivity_allowed=("private",),
            reference_time=reference_time,
        )
    )

    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 1
    assert pack["aggregation"]["provenance"][0]["reviewed_evidence_count"] == 1_001
    assert len(pack["aggregation"]["provenance"][0]["evidence"]) == 1_001
    assert memory_batch_sizes
    assert max(memory_batch_sizes) <= 200
    assert memory_batch_sizes[:6] == [200, 200, 200, 200, 200, 1]


def test_sqlite_occurrence_reader_refetches_the_complete_discovered_count_key() -> None:
    store = _sqlite_retrieval_store()
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    _create_sqlite_reviewed_occurrence(
        store,
        index=1,
        occurred_at="2026-07-01T12:00:00Z",
        count_key="attend parties",
        canonical_text="I went to a party.",
    )
    _create_sqlite_reviewed_occurrence(
        store,
        index=2,
        occurred_at="2026-07-02T12:00:00Z",
        count_key="attend parties",
        canonical_text="I celebrated with friends.",
    )
    store.conn.commit()
    _configure_sqlite_occurrence_coverage(
        store,
        complete_through=reference_time,
    )

    discovery = store.search_accepted_occurrence_units(
        query="How many times did I attend parties?",
        domains=("personal",),
        sensitivity_allowed=("private",),
        occurred_at_end=reference_time,
        include_timeless=True,
        as_of=reference_time,
    )
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I attend parties?",
            domains=("personal",),
            sensitivity_allowed=("private",),
            reference_time=reference_time,
        )
    )

    assert len(discovery) == 2
    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 2
    assert len(pack["aggregation"]["occurrence_unit_ids"]) == 2


def test_occurrence_reader_emits_exact_signed_count_without_proposal_inference(
    monkeypatch,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows()
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    def proposal_bomb(**_kwargs: object) -> object:
        raise AssertionError("query-time occurrence proposal inference is forbidden")

    monkeypatch.setattr(
        vnext_retrieval_module.vnext_occurrences,
        "build_occurrence_proposal",
        proposal_bomb,
    )
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            domains=("personal",),
            projects=("bike",),
            reference_time=reference_time,
        )
    )

    aggregation = pack["aggregation"]
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["exact"] is True
    assert aggregation["count"] == 2
    assert aggregation["lower_bound"] == aggregation["upper_bound"] == 2
    assert aggregation["occurrence_unit_ids"] == [
        "occurrence-001",
        "occurrence-002",
    ]
    assert aggregation["answer_sufficient"] is True
    assert "user_id" not in aggregation
    assert all(item["reviewed_evidence_count"] == len(item["evidence"]) == 1 for item in aggregation["provenance"])
    assert all(
        item["evidence"][0]["unit_review_receipt_digest"] == item["review_receipt_digest"]
        for item in aggregation["provenance"]
    )
    assert store.occurrence_search_calls[0]["projects"] == ("bike",)
    assert store.occurrence_search_calls[0]["domains"] == ("personal",)
    assert store.occurrence_search_calls[0]["occurred_at_end"] == reference_time
    assert store.occurrence_search_calls[0]["include_timeless"] is True
    assert store.unresolved_search_calls[0]["count_key"] is None
    assert store.unresolved_search_calls[0]["occurred_at_end"] == reference_time
    assert store.unresolved_search_calls[0]["include_timeless"] is True
    lifecycle_values = [
        *(call["as_of"] for call in store.occurrence_search_calls),
        *(call["as_of"] for call in store.unresolved_search_calls),
        *(call["as_of"] for call in store.evidence_search_calls),
    ]
    lifecycle_clock = lifecycle_values[0]
    assert isinstance(lifecycle_clock, datetime)
    assert lifecycle_clock.tzinfo is not None
    assert lifecycle_clock != reference_time
    assert all(value is lifecycle_clock for value in lifecycle_values)
    assert aggregation["coverage"]["requested_end"] == reference_time.isoformat()
    assert "aggregation" in pack["budget"]["allocation"]
    assert store.snapshot_calls == 1
    assert store.snapshot_end_calls == 1


def test_occurrence_reader_meets_a_stored_past_surface_with_a_present_query() -> None:
    # "visited" and "visit" fold onto the same reviewed canonical leaf, so the
    # write side and the query side reach the same selector instead of missing
    # each other over inflection alone.
    memories, units, evidence = _reviewed_occurrence_rows(1)
    units[0]["count_key"] = "visited museum"
    units[0]["canonical_text"] = "I visited the museum."
    units[0]["predicate_json"] = build_occurrence_predicate_atom(
        action="visited",
        object_leaf="museum",
    )
    _resign_occurrence_test_unit(units[0], evidence)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I visit museums?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 1
    assert pack["aggregation"]["accepted_units"] == {
        "matching": 1,
        "disjoint_proven": 0,
        "relation_unknown": 0,
    }
    assert any(call["selector_key"] is None for call in store.occurrence_search_calls)
    assert all(call["as_of"] is store.occurrence_search_calls[0]["as_of"] for call in store.occurrence_search_calls)


@pytest.mark.parametrize(
    ("stored_action", "stored_object", "count_key", "canonical_text"),
    [
        # The original target: a reviewed predicate that simply is not the one
        # being asked about. Sharing the reviewed ``visit`` leaf with the query
        # is exactly what makes this the sharpest case.
        ("visited", "gallery", "visited gallery", "I visited the gallery."),
        # An unreviewed surface, which proves nothing in either direction.
        ("polished", "meteorite", "polished meteorite", "I polished the meteorite."),
    ],
)
def test_occurrence_reader_never_emits_selector_only_exact_zero_for_unknown_surface(
    stored_action: str,
    stored_object: str,
    count_key: str,
    canonical_text: str,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    units[0]["count_key"] = count_key
    units[0]["canonical_text"] = canonical_text
    units[0]["predicate_json"] = build_occurrence_predicate_atom(
        action=stored_action,
        object_leaf=stored_object,
    )
    _resign_occurrence_test_unit(units[0], evidence)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I visit museums?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert any(call["selector_key"] is None for call in store.occurrence_search_calls)
    assert all(call["as_of"] is store.occurrence_search_calls[0]["as_of"] for call in store.occurrence_search_calls)


def test_occurrence_reader_exact_aggregation_obeys_the_content_token_budget() -> None:
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)

    def compile_pack(*, max_tokens: int | None = None) -> dict[str, object]:
        memories, units, evidence = _reviewed_occurrence_rows(1)
        return VNextRetrievalService(
            OccurrenceReaderStore(
                memories=memories,
                units=units,
                evidence=evidence,
                coverage=_complete_occurrence_coverage(),
            )
        ).compile_context_pack(
            VNextRetrievalRequest(
                query="How many times did I service my bike?",
                reference_time=reference_time,
                max_tokens=max_tokens,
            )
        )

    unconstrained = compile_pack()
    exact_budget = int(unconstrained["budget"]["token_estimate"])

    exact_fit = compile_pack(max_tokens=exact_budget)
    assert exact_fit["aggregation"] == unconstrained["aggregation"]
    assert exact_fit["budget"]["token_budget"] == exact_budget
    assert exact_fit["budget"]["token_estimate"] == exact_budget
    assert exact_fit["budget"]["allocation"]["aggregation"] > 0
    assert sum(exact_fit["budget"]["allocation"].values()) == exact_budget
    assert exact_fit["budget"]["truncated"] is False
    assert exact_fit["budget"]["dropped_item_count"] == 0

    one_token_short = compile_pack(max_tokens=exact_budget - 1)
    assert "aggregation" not in one_token_short
    assert one_token_short["budget"]["token_budget"] == exact_budget - 1
    assert one_token_short["budget"]["token_estimate"] <= exact_budget - 1
    assert one_token_short["budget"]["allocation"]["aggregation"] == 0
    assert sum(one_token_short["budget"]["allocation"].values()) == (one_token_short["budget"]["token_estimate"])
    assert one_token_short["budget"]["truncated"] is True
    assert one_token_short["budget"]["dropped_item_count"] == 1


def test_occurrence_reader_accepts_signed_evidence_from_a_linked_claim() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    assert evidence[0]["claim_id"] == units[0]["claim_id"]
    evidence[0]["claim_id"] = "claim-linked-to-existing-unit"
    evidence[0]["evidence_claim_review_status"] = "accepted"
    evidence[0]["evidence_claim_resolution_status"] = "resolved"
    evidence[0]["evidence_claim_resolution_decision"] = "link_existing"
    evidence[0]["evidence_claim_resolved_occurrence_id"] = units[0]["id"]
    _resign_occurrence_test_unit(units[0], [evidence[0]])
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 1
    assert pack["aggregation"]["occurrence_unit_ids"] == ["occurrence-001"]


@pytest.mark.parametrize(
    "claim_metadata",
    [
        {},
        {
            "evidence_claim_review_status": "candidate",
            "evidence_claim_resolution_status": "resolved",
            "evidence_claim_resolution_decision": "link_existing",
            "evidence_claim_resolved_occurrence_id": "occurrence-001",
        },
        {
            "evidence_claim_review_status": "accepted",
            "evidence_claim_resolution_status": "pending",
            "evidence_claim_resolution_decision": "link_existing",
            "evidence_claim_resolved_occurrence_id": "occurrence-001",
        },
        {
            "evidence_claim_review_status": "accepted",
            "evidence_claim_resolution_status": "resolved",
            "evidence_claim_resolution_decision": "new",
            "evidence_claim_resolved_occurrence_id": "occurrence-001",
        },
        {
            "evidence_claim_review_status": "accepted",
            "evidence_claim_resolution_status": "resolved",
            "evidence_claim_resolution_decision": "link_existing",
            "evidence_claim_resolved_occurrence_id": "occurrence-other",
        },
    ],
)
def test_occurrence_reader_rejects_unauthorized_cross_claim_evidence(
    claim_metadata: dict[str, object],
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    evidence[0]["claim_id"] = "claim-unrelated-same-envelope"
    evidence[0].update(claim_metadata)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack


def test_occurrence_reader_all_time_counts_timeless_and_excludes_future_units() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(3)
    units[1]["occurred_at_start"] = None
    units[1]["occurred_at_end"] = None
    units[2]["occurred_at_start"] = "2026-08-01T12:00:00Z"
    units[2]["occurred_at_end"] = "2026-08-01T12:00:00Z"
    for unit in units:
        _resign_occurrence_test_unit(
            unit,
            [row for row in evidence if row["occurrence_id"] == unit["id"]],
        )
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 2
    assert pack["aggregation"]["occurrence_unit_ids"] == [
        "occurrence-001",
        "occurrence-002",
    ]
    assert store.occurrence_search_calls[0]["include_timeless"] is True


def test_occurrence_reader_explicit_window_fails_closed_on_timeless_unit() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    units[0]["occurred_at_start"] = "2026-07-22T12:00:00Z"
    units[0]["occurred_at_end"] = "2026-07-22T12:00:00Z"
    units[1]["occurred_at_start"] = None
    units[1]["occurred_at_end"] = None
    for unit in units:
        _resign_occurrence_test_unit(
            unit,
            [row for row in evidence if row["occurrence_id"] == unit["id"]],
        )
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike this week?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    # Timeless rows are deliberately fetched so their unknown interval
    # membership cannot be silently converted into an exact dated answer.
    assert store.occurrence_search_calls[0]["include_timeless"] is True


def test_occurrence_reader_normalizes_naive_relative_reference_once(
    monkeypatch,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    units[0]["occurred_at_start"] = "2026-07-22T12:00:00Z"
    units[0]["occurred_at_end"] = "2026-07-22T12:00:00Z"
    _resign_occurrence_test_unit(units[0], [evidence[0]])
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )
    observed_reference_times: list[datetime] = []
    real_parse_temporal_anchor = vnext_retrieval_module.parse_temporal_anchor

    def recording_parse_temporal_anchor(
        query: str,
        *,
        reference_time: datetime,
    ) -> vnext_retrieval_module.TemporalAnchor | None:
        observed_reference_times.append(reference_time)
        return real_parse_temporal_anchor(
            query,
            reference_time=reference_time,
        )

    monkeypatch.setattr(
        vnext_retrieval_module,
        "parse_temporal_anchor",
        recording_parse_temporal_anchor,
    )
    provider = StubEmbeddingProvider()
    query = "How many times did I service my bike this week?"
    pack = VNextRetrievalService(
        store,
        embedding_provider=provider,
    ).compile_context_pack(
        VNextRetrievalRequest(
            query=query,
            reference_time=datetime(2026, 7, 24, 12, 0),
        )
    )

    normalized = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    assert pack["aggregation"]["count"] == 1
    assert observed_reference_times == [datetime(2026, 7, 24, 12, 0)]
    assert store.occurrence_search_calls[0]["occurred_at_end"] == normalized
    assert store.unresolved_search_calls[0]["occurred_at_end"] == normalized
    assert pack["aggregation"]["coverage"]["requested_end"] == normalized.isoformat()
    assert provider.embedded_texts == [query]


def test_occurrence_reader_preserves_event_clocks_and_uses_current_snapshot_lifecycle(
    monkeypatch,
) -> None:
    scope_clock = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    anchor_clock = datetime(2026, 7, 24, 12, 1, tzinfo=UTC)

    class AdvancingDateTime(datetime):
        calls = 0

        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            cls.calls += 1
            value = scope_clock if cls.calls == 1 else anchor_clock
            return value if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(
        vnext_retrieval_module,
        "datetime",
        AdvancingDateTime,
    )
    memories, units, evidence = _reviewed_occurrence_rows(1)
    units[0]["occurred_at_start"] = "2026-07-24T10:00:00Z"
    units[0]["occurred_at_end"] = "2026-07-24T10:00:00Z"
    _resign_occurrence_test_unit(units[0], [evidence[0]])
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        snapshot_proof={
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
            "lifecycle_as_of": anchor_clock,
        },
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike today?",
            time_window="7d",
        )
    )

    assert pack["aggregation"]["count"] == 1
    assert store.occurrence_search_calls[0]["occurred_at_start"] == datetime(
        2026,
        7,
        24,
        tzinfo=UTC,
    )
    assert store.occurrence_search_calls[0]["occurred_at_end"] == scope_clock
    lifecycle_values = [
        *(call["as_of"] for call in store.occurrence_search_calls),
        *(call["as_of"] for call in store.evidence_search_calls),
        *(call["as_of"] for call in store.unresolved_search_calls),
    ]
    assert lifecycle_values
    assert all(value is anchor_clock for value in lifecycle_values)


def test_occurrence_reader_uses_snapshot_clock_instead_of_lagging_host_for_exact_zero(
    monkeypatch,
) -> None:
    app_clock = datetime(2026, 7, 24, 11, 59, tzinfo=UTC)
    lifecycle_clock = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    reference_clock = datetime(2026, 7, 24, 13, 0, tzinfo=UTC)

    class LaggingDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            return app_clock if tz is not None else app_clock.replace(tzinfo=None)

    monkeypatch.setattr(
        vnext_retrieval_module,
        "datetime",
        LaggingDateTime,
    )
    memories, units, evidence = _reviewed_occurrence_rows(1)
    units[0]["updated_at"] = lifecycle_clock
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        snapshot_proof={
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "postgres",
            "mode": "repeatable_read_read_only",
            "snapshot_id": "10:20:",
            "lifecycle_as_of": lifecycle_clock,
        },
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=reference_clock,
        )
    )

    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 1
    assert {call["as_of"] for call in store.occurrence_search_calls} == {lifecycle_clock}
    assert {call["occurred_at_end"] for call in store.occurrence_search_calls} == {reference_clock}


def test_occurrence_reader_uses_snapshot_clock_for_finite_range_lower_bound(
    monkeypatch,
) -> None:
    app_clock = datetime(2026, 7, 24, 11, 59, tzinfo=UTC)
    lifecycle_clock = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)

    class LaggingDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            return app_clock if tz is not None else app_clock.replace(tzinfo=None)

    monkeypatch.setattr(
        vnext_retrieval_module,
        "datetime",
        LaggingDateTime,
    )
    memories, units, evidence = _reviewed_occurrence_rows(2)
    units[0]["updated_at"] = datetime(
        2026,
        7,
        24,
        11,
        58,
        tzinfo=UTC,
    )
    units[1]["updated_at"] = lifecycle_clock
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=[
            _occurrence_test_unresolved_claim(
                "claim-finite-upper",
                quantity_min=1,
                quantity_max=1,
            )
        ],
        snapshot_proof={
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "postgres",
            "mode": "repeatable_read_read_only",
            "snapshot_id": "10:20:",
            "lifecycle_as_of": lifecycle_clock,
        },
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(
                2026,
                7,
                24,
                13,
                tzinfo=UTC,
            ),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["lower_bound"] == 2
    assert pack["aggregation"]["upper_bound"] == 3
    assert "count" not in pack["aggregation"]


def test_occurrence_reader_timeless_unresolved_claim_prevents_all_time_exact() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=[
            _occurrence_test_unresolved_claim(
                "claim-timeless",
                occurred_at_start=None,
                occurred_at_end=None,
            )
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["lower_bound"] == 1
    assert pack["aggregation"]["upper_bound"] == 2


def test_occurrence_reader_rejects_expired_memory_evidence(
    monkeypatch,
) -> None:
    app_clock = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    lifecycle_clock = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            return app_clock if tz is not None else app_clock.replace(tzinfo=None)

    monkeypatch.setattr(
        vnext_retrieval_module,
        "datetime",
        FixedDateTime,
    )
    memories, units, evidence = _reviewed_occurrence_rows(1)
    # The memory was still live at the historical question clock, but it is
    # not live at the current review snapshot. A historical reference_time
    # must never resurrect it.
    memories[0]["valid_to"] = "2026-07-24T00:00:00Z"
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        snapshot_proof={
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
            "lifecycle_as_of": lifecycle_clock,
        },
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=app_clock,
        )
    )

    assert "aggregation" not in pack
    assert {call["as_of"] for call in store.occurrence_search_calls} == {lifecycle_clock}
    assert {call["as_of"] for call in store.evidence_search_calls} == {lifecycle_clock}


@pytest.mark.parametrize(
    ("field_name", "mismatched_value"),
    [
        ("domain", "work"),
        ("sensitivity", "public"),
        ("project_id", "different-project"),
    ],
)
def test_occurrence_reader_requires_evidence_to_match_its_unit_envelope(
    field_name: str,
    mismatched_value: str,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    memories[0][field_name] = mismatched_value
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack


@pytest.mark.parametrize("carrier_kind", ["memory", "source", "source_chunk"])
def test_occurrence_reader_rejects_cross_user_evidence_carriers(
    carrier_kind: str,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    sources: list[dict[str, object]] = []
    source_chunks: list[dict[str, object]] = []
    if carrier_kind == "memory":
        memories[0]["user_id"] = "different-user"
    else:
        evidence[0]["memory_id"] = None
        evidence[0]["source_id"] = "source-occurrence"
        sources.append(
            {
                "id": "source-occurrence",
                "user_id": ("different-user" if carrier_kind == "source" else "user-1"),
                "domain": "personal",
                "sensitivity": "private",
                "deleted_at": None,
                "metadata_json": {"project_id": "bike"},
            }
        )
        if carrier_kind == "source_chunk":
            evidence[0]["source_chunk_id"] = "chunk-occurrence"
            source_chunks.append(
                {
                    "id": "chunk-occurrence",
                    "user_id": "different-user",
                    "source_id": "source-occurrence",
                    "text": "Bike service evidence",
                }
            )
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        sources=sources,
        source_chunks=source_chunks,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack


def test_occurrence_reader_rejects_mismatched_source_chunk_evidence() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    evidence[0]["memory_id"] = None
    evidence[0]["source_id"] = "source-occurrence"
    evidence[0]["source_chunk_id"] = "chunk-occurrence"
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        sources=[
            {
                "id": "source-occurrence",
                "domain": "personal",
                "sensitivity": "private",
                "deleted_at": None,
                "metadata_json": {"project_id": "bike"},
            }
        ],
        source_chunks=[
            {
                "id": "chunk-occurrence",
                "source_id": "different-source",
                "text": "Bike service evidence",
            }
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack


def test_occurrence_reader_pages_the_full_unit_substrate_before_counting() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(201)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["count"] == 201
    assert len(pack["aggregation"]["occurrence_unit_ids"]) == 201
    assert [call["after_id"] for call in store.occurrence_search_calls] == [
        None,
        "occurrence-200",
        "occurrence-201",
        None,
        "occurrence-200",
        "occurrence-201",
    ]
    assert [call["limit"] for call in store.occurrence_search_calls] == [
        200,
        200,
        1,
        200,
        200,
        1,
    ]
    assert {call["selector_key"] for call in store.occurrence_search_calls[:3]} == {None}
    assert {call["selector_key"] for call in store.occurrence_search_calls[3:]} == {"v1|a=exact:service|o=exact:bike"}


def test_occurrence_reader_unit_cap_boundary_and_overflow_are_honest(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        vnext_retrieval_module,
        "OCCURRENCE_SEARCH_MAX_UNITS",
        2,
    )
    memories, units, evidence = _reviewed_occurrence_rows(2)
    boundary_store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )
    boundary = VNextRetrievalService(boundary_store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    overflow_memories, overflow_units, overflow_evidence = _reviewed_occurrence_rows(3)
    _retarget_occurrence_test_unit(
        overflow_units[2],
        [overflow_evidence[2]],
        action="service",
        object_leaf="car",
        count_key="car service",
        canonical_text="Car service occurrence.",
    )
    overflow_store = OccurrenceReaderStore(
        memories=overflow_memories,
        units=overflow_units,
        evidence=overflow_evidence,
        coverage=_complete_occurrence_coverage(),
    )
    overflow = VNextRetrievalService(overflow_store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert boundary["aggregation"]["answer_kind"] == "exact"
    assert boundary["aggregation"]["count"] == 2
    assert boundary["aggregation"]["saturated"] is False
    assert overflow["aggregation"]["answer_kind"] == "at_least"
    assert overflow["aggregation"]["lower_bound"] == 2
    assert overflow["aggregation"]["upper_bound"] is None
    assert overflow["aggregation"]["saturated"] is True
    assert overflow_store.occurrence_search_calls[-1]["limit"] == 1


def test_occurrence_reader_evidence_cap_boundary_and_overflow_are_honest(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        vnext_retrieval_module,
        "OCCURRENCE_EVIDENCE_MAX_ROWS",
        2,
    )
    evidence_saturation: list[bool] = []
    real_builder = vnext_retrieval_module.vnext_occurrences.build_occurrence_aggregation

    def recording_builder(**kwargs: object) -> dict[str, object] | None:
        evidence_saturation.append(bool(kwargs["evidence_saturated"]))
        return real_builder(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        vnext_retrieval_module.vnext_occurrences,
        "build_occurrence_aggregation",
        recording_builder,
    )
    memories, units, evidence = _reviewed_occurrence_with_shared_evidence(2)
    boundary_store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )
    boundary = VNextRetrievalService(boundary_store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    overflow_memories, overflow_units, overflow_evidence = _reviewed_occurrence_with_shared_evidence(3)
    overflow_store = OccurrenceReaderStore(
        memories=overflow_memories,
        units=overflow_units,
        evidence=overflow_evidence,
        coverage=_complete_occurrence_coverage(),
    )
    overflow = VNextRetrievalService(overflow_store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert boundary["aggregation"]["answer_kind"] == "exact"
    assert boundary["aggregation"]["count"] == 1
    assert evidence_saturation == [False, True]
    assert "aggregation" not in overflow
    assert [call["limit"] for call in boundary_store.evidence_search_calls] == [
        2,
        1,
    ]
    assert [call["limit"] for call in overflow_store.evidence_search_calls] == [
        2,
        1,
    ]


def test_occurrence_reader_pages_past_an_internal_evidence_cap() -> None:
    memories, units, evidence = _reviewed_occurrence_with_shared_evidence(2)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        internal_evidence_cap=1,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 1
    assert [(call["after_id"], call["limit"]) for call in store.evidence_search_calls] == [
        (None, 200),
        ("evidence-shared-0001", 1),
        ("evidence-shared-0001", 200),
        ("evidence-shared-0002", 1),
    ]


def test_occurrence_reader_rejects_evidence_page_that_skips_the_probe() -> None:
    memories, units, evidence = _reviewed_occurrence_with_shared_evidence(4)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        internal_evidence_cap=2,
        skip_probed_evidence_on_followup=True,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert [call["after_id"] for call in store.evidence_search_calls] == [
        None,
        "evidence-shared-0002",
        "evidence-shared-0002",
    ]


def test_occurrence_reader_probes_past_an_internal_one_row_unit_cap() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        internal_unit_cap=1,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["count"] == 2
    assert [call["after_id"] for call in store.occurrence_search_calls] == [
        None,
        "occurrence-001",
        "occurrence-001",
        "occurrence-002",
        None,
        "occurrence-001",
        "occurrence-001",
        "occurrence-002",
    ]
    assert [call["limit"] for call in store.occurrence_search_calls] == [
        200,
        1,
        200,
        1,
        200,
        1,
        200,
        1,
    ]


def test_occurrence_reader_rejects_a_unit_page_that_skips_the_probed_row() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(4)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        internal_unit_cap=2,
        skip_probed_unit_on_followup=True,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert [call["after_id"] for call in store.occurrence_search_calls] == [
        None,
        "occurrence-002",
        "occurrence-002",
    ]


def test_occurrence_reader_reports_finite_ambiguity_as_a_range() -> None:
    memories, units, evidence = _reviewed_occurrence_rows()
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=[
            _occurrence_test_unresolved_claim(
                "claim-unresolved",
                quantity_max=2,
                range_kind="bounded",
            )
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["lower_bound"] == 2
    assert pack["aggregation"]["upper_bound"] == 4
    assert "count" not in pack["aggregation"]
    assert pack["aggregation"]["answer_sufficient"] is False


def test_occurrence_reader_pages_all_scoped_unresolved_claims() -> None:
    memories, units, evidence = _reviewed_occurrence_rows()
    unresolved = [_occurrence_test_unresolved_claim(f"claim-unresolved-{index:03d}") for index in range(1, 202)]
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=unresolved,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["lower_bound"] == 2
    assert pack["aggregation"]["upper_bound"] == 203
    assert [call["after_id"] for call in store.unresolved_search_calls] == [
        None,
        "claim-unresolved-200",
        "claim-unresolved-201",
    ]


def test_occurrence_reader_unresolved_cap_boundary_and_overflow_are_honest(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        vnext_retrieval_module,
        "OCCURRENCE_UNRESOLVED_MAX_CLAIMS",
        2,
    )
    memories, units, evidence = _reviewed_occurrence_rows()

    def unresolved_rows(count: int) -> list[dict[str, object]]:
        return [_occurrence_test_unresolved_claim(f"claim-cap-{index}") for index in range(1, count + 1)]

    boundary_store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=unresolved_rows(2),
    )
    boundary = VNextRetrievalService(boundary_store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )
    overflow_store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=unresolved_rows(3),
    )
    overflow = VNextRetrievalService(overflow_store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert boundary["aggregation"]["answer_kind"] == "range"
    assert boundary["aggregation"]["lower_bound"] == 2
    assert boundary["aggregation"]["upper_bound"] == 4
    assert overflow["aggregation"]["answer_kind"] == "at_least"
    assert overflow["aggregation"]["lower_bound"] == 2
    assert overflow["aggregation"]["upper_bound"] is None
    assert overflow["aggregation"]["unresolved_claims"]["saturated"] is True


def test_occurrence_reader_probes_past_an_internal_one_row_unresolved_cap() -> None:
    memories, units, evidence = _reviewed_occurrence_rows()
    unresolved = [_occurrence_test_unresolved_claim(f"claim-capped-{index}") for index in range(1, 3)]
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=unresolved,
        internal_unresolved_cap=1,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["lower_bound"] == 2
    assert pack["aggregation"]["upper_bound"] == 4
    assert [call["after_id"] for call in store.unresolved_search_calls] == [
        None,
        "claim-capped-1",
        "claim-capped-1",
        "claim-capped-2",
    ]


def test_occurrence_reader_rejects_unresolved_page_skipping_probed_row() -> None:
    memories, units, evidence = _reviewed_occurrence_rows()
    unresolved = [_occurrence_test_unresolved_claim(f"claim-skipped-{index}") for index in range(1, 5)]
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=unresolved,
        internal_unresolved_cap=2,
        skip_probed_unresolved_on_followup=True,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert [call["after_id"] for call in store.unresolved_search_calls] == [
        None,
        "claim-skipped-2",
        "claim-skipped-2",
    ]


def test_occurrence_reader_dormancy_preserves_pack_bytes(monkeypatch) -> None:
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)

    def compile_pack(store: InMemoryVNextRetrievalStore) -> dict[str, object]:
        counter = itertools.count(1)
        monkeypatch.setattr(
            vnext_retrieval_module,
            "uuid4",
            lambda: UUID(int=next(counter)),
        )
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="How many times did I service my bike?",
                reference_time=reference_time,
                trace_id="trace-occurrence-dormant",
            )
        )

    legacy = compile_pack(
        InMemoryVNextRetrievalStore(
            memories=[_memory_row("memory-1", "I serviced my bike once.")],
            sources=[],
        )
    )
    migrated_empty_store = OccurrenceReaderStore(
        memories=[_memory_row("memory-1", "I serviced my bike once.")],
        units=[],
        evidence=[],
        coverage=_forward_occurrence_coverage(),
    )
    migrated_empty = compile_pack(migrated_empty_store)

    assert json.dumps(legacy, sort_keys=True, default=str) == json.dumps(migrated_empty, sort_keys=True, default=str)
    assert "aggregation" not in migrated_empty
    assert "aggregation" not in migrated_empty["budget"]["allocation"]
    # One complete-set read plus one selector read, both empty.
    assert len(migrated_empty_store.occurrence_search_calls) == 2


def test_complete_occurrence_reader_emits_signed_exact_zero() -> None:
    store = OccurrenceReaderStore(
        memories=[],
        units=[],
        evidence=[],
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    aggregation = pack["aggregation"]
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["count"] == 0
    assert aggregation["lower_bound"] == aggregation["upper_bound"] == 0
    assert aggregation["occurrence_unit_ids"] == []
    assert aggregation["counted_member_keys"] == []
    assert aggregation["provenance"] == []


def test_empty_occurrence_store_preserves_base_advancing_clock_bytes(
    monkeypatch,
) -> None:
    scope_clock = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    anchor_clock = datetime(2026, 7, 24, 12, 1, tzinfo=UTC)

    class AdvancingDateTime(datetime):
        calls = 0

        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def]
            cls.calls += 1
            value = scope_clock if cls.calls == 1 else anchor_clock
            return value if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(
        vnext_retrieval_module,
        "datetime",
        AdvancingDateTime,
    )
    real_resolve_scope = vnext_retrieval_module._resolve_retrieval_scope
    real_parse_anchor = vnext_retrieval_module.parse_temporal_anchor
    observed_scope_ends: list[datetime | None] = []
    observed_anchor_references: list[datetime] = []

    def recording_resolve_scope(
        request: VNextRetrievalRequest,
    ) -> object:
        resolved = real_resolve_scope(request)
        observed_scope_ends.append(resolved.window_end)
        return resolved

    def recording_parse_anchor(
        query: str,
        *,
        reference_time: datetime,
    ) -> vnext_retrieval_module.TemporalAnchor | None:
        observed_anchor_references.append(reference_time)
        return real_parse_anchor(query, reference_time=reference_time)

    monkeypatch.setattr(
        vnext_retrieval_module,
        "_resolve_retrieval_scope",
        recording_resolve_scope,
    )
    monkeypatch.setattr(
        vnext_retrieval_module,
        "parse_temporal_anchor",
        recording_parse_anchor,
    )

    def compile_pack(
        store: InMemoryVNextRetrievalStore,
    ) -> tuple[dict[str, object], datetime | None, datetime]:
        AdvancingDateTime.calls = 0
        observed_scope_ends.clear()
        observed_anchor_references.clear()
        counter = itertools.count(1)
        monkeypatch.setattr(
            vnext_retrieval_module,
            "uuid4",
            lambda: UUID(int=next(counter)),
        )
        pack = VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(
                query="How many times did I service my bike today?",
                time_window="7d",
                trace_id="trace-occurrence-clock-dormant",
            )
        )
        assert len(observed_scope_ends) == 1
        assert len(observed_anchor_references) == 1
        return (
            pack,
            observed_scope_ends[0],
            observed_anchor_references[0],
        )

    memory = _memory_row(
        "memory-1",
        "I serviced my bike once today.",
        valid_from="2026-07-24T10:00:00Z",
    )
    legacy, legacy_scope_end, legacy_anchor_reference = compile_pack(
        InMemoryVNextRetrievalStore(memories=[memory], sources=[])
    )
    migrated_empty_store = OccurrenceReaderStore(
        memories=[memory],
        units=[],
        evidence=[],
        coverage=_forward_occurrence_coverage(),
        snapshot_proof={
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
            "lifecycle_as_of": anchor_clock,
        },
    )
    migrated, migrated_scope_end, migrated_anchor_reference = compile_pack(migrated_empty_store)

    assert legacy_scope_end == migrated_scope_end == scope_clock
    assert legacy_anchor_reference == migrated_anchor_reference == anchor_clock
    assert json.dumps(legacy, sort_keys=True, default=str) == json.dumps(
        migrated,
        sort_keys=True,
        default=str,
    )
    assert "aggregation" not in migrated
    assert {call["as_of"] for call in migrated_empty_store.occurrence_search_calls} == {anchor_clock}


@pytest.mark.parametrize(
    ("query", "context_depth", "expected_provider_calls"),
    [
        (
            "Tell me about my bike service history.",
            "high",
            ["Tell me about my bike service history."],
        ),
        (
            "How many times did I service my bike?",
            "minimal",
            [],
        ),
    ],
)
def test_live_occurrence_seam_is_byte_dormant_outside_the_reader_gate(
    monkeypatch,
    query: str,
    context_depth: str,
    expected_provider_calls: list[str],
) -> None:
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    memories, units, evidence = _reviewed_occurrence_rows(2)
    legacy_store = InMemoryVNextRetrievalStore(
        memories=[dict(row) for row in memories],
        sources=[],
    )
    occurrence_store = OccurrenceReaderStore(
        memories=[dict(row) for row in memories],
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    def compile_pack(
        store: InMemoryVNextRetrievalStore,
    ) -> tuple[dict[str, object], StubEmbeddingProvider]:
        counter = itertools.count(1)
        monkeypatch.setattr(
            vnext_retrieval_module,
            "uuid4",
            lambda: UUID(int=next(counter)),
        )
        provider = StubEmbeddingProvider()
        pack = VNextRetrievalService(
            store,
            embedding_provider=provider,
        ).compile_context_pack(
            VNextRetrievalRequest(
                query=query,
                context_depth=context_depth,
                reference_time=reference_time,
                trace_id="trace-live-occurrence-dormancy",
            )
        )
        return pack, provider

    legacy_pack, legacy_provider = compile_pack(legacy_store)
    occurrence_pack, occurrence_provider = compile_pack(occurrence_store)

    assert json.dumps(occurrence_pack, sort_keys=True, default=str) == json.dumps(
        legacy_pack,
        sort_keys=True,
        default=str,
    )
    assert legacy_provider.embedded_texts == expected_provider_calls
    assert occurrence_provider.embedded_texts == expected_provider_calls
    assert occurrence_store.snapshot_calls == 0
    assert occurrence_store.snapshot_end_calls == 0
    assert occurrence_store.occurrence_search_calls == []
    assert occurrence_store.evidence_search_calls == []
    assert occurrence_store.unresolved_search_calls == []
    assert "aggregation" not in occurrence_pack
    assert "aggregation" not in occurrence_pack["budget"]["allocation"]


def test_internal_occurrence_memory_metadata_is_byte_dormant_for_non_count_pack(
    monkeypatch,
) -> None:
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    plain = _memory_row(
        "memory-multi-event",
        "I baked cookies and attended a dinner party.",
        metadata_json={},
    )
    annotated = dict(plain)
    annotated["metadata_json"] = {
        "occurrence_candidate_texts": [
            "[USER]: I baked cookies on March 3, 2026.",
            "[USER]: I attended a dinner party on March 4, 2026.",
        ],
        "occurrence_proposals": [
            {"claim_id": "claim-bake", "count_key": "bake cookie"},
            {"claim_id": "claim-party", "count_key": "attend party"},
        ],
    }

    def compile_pack(
        memory: dict[str, object],
    ) -> tuple[dict[str, object], list[str]]:
        counter = itertools.count(1)
        monkeypatch.setattr(
            vnext_retrieval_module,
            "uuid4",
            lambda: UUID(int=next(counter)),
        )
        provider = StubEmbeddingProvider()
        pack = VNextRetrievalService(
            InMemoryVNextRetrievalStore(memories=[memory], sources=[]),
            embedding_provider=provider,
        ).compile_context_pack(
            VNextRetrievalRequest(
                query="Tell me about baking and dinner parties.",
                reference_time=reference_time,
                trace_id="trace-internal-occurrence-metadata-dormant",
            )
        )
        return pack, provider.embedded_texts

    control, control_calls = compile_pack(plain)
    candidate, candidate_calls = compile_pack(annotated)

    assert json.dumps(candidate, sort_keys=True, default=str) == json.dumps(
        control,
        sort_keys=True,
        default=str,
    )
    assert candidate_calls == control_calls


def test_active_occurrence_reader_adds_no_embedding_or_reranker_calls(
    monkeypatch,
) -> None:
    reference_time = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    memories, units, evidence = _reviewed_occurrence_rows(2)
    legacy_store = InMemoryVNextRetrievalStore(
        memories=[dict(row) for row in memories],
        sources=[],
    )
    occurrence_store = OccurrenceReaderStore(
        memories=[dict(row) for row in memories],
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    def compile_pack(
        store: InMemoryVNextRetrievalStore,
    ) -> tuple[
        dict[str, object],
        StubEmbeddingProvider,
        StubRerankProvider,
    ]:
        counter = itertools.count(1)
        monkeypatch.setattr(
            vnext_retrieval_module,
            "uuid4",
            lambda: UUID(int=next(counter)),
        )
        embedding = StubEmbeddingProvider()
        reranker = StubRerankProvider()
        pack = VNextRetrievalService(
            store,
            embedding_provider=embedding,
            reranker_provider=reranker,
        ).compile_context_pack(
            VNextRetrievalRequest(
                query="How many times did I service my bike?",
                context_depth="high",
                reference_time=reference_time,
                trace_id="trace-active-occurrence-call-parity",
            )
        )
        return pack, embedding, reranker

    legacy_pack, legacy_embedding, legacy_reranker = compile_pack(legacy_store)
    occurrence_pack, occurrence_embedding, occurrence_reranker = compile_pack(occurrence_store)

    assert legacy_embedding.embedded_texts == occurrence_embedding.embedded_texts
    assert legacy_embedding.embedded_texts == ["How many times did I service my bike?"]
    assert legacy_reranker.prompts == occurrence_reranker.prompts
    assert len(legacy_reranker.prompts) == 1
    assert "aggregation" not in legacy_pack
    assert occurrence_pack["aggregation"]["answer_kind"] == "exact"
    assert set(occurrence_pack) == {*legacy_pack, "aggregation"}
    for key in legacy_pack:
        if key not in {"budget", "trace"}:
            assert occurrence_pack[key] == legacy_pack[key]


def test_occurrence_reader_requires_a_coherent_read_snapshot() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        snapshot_proof={
            "proof": "occurrence_read_snapshot_v1",
            "acquired": False,
        },
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 1
    assert store.snapshot_end_calls == 1
    assert store.occurrence_search_calls == []


@pytest.mark.parametrize(
    "snapshot_proof",
    [
        {
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
        },
        {
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
            "lifecycle_as_of": "not-a-timestamp",
        },
        {
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
            "lifecycle_as_of": datetime(2026, 7, 24, 12),
        },
        {
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "repeatable_read_read_only",
            "lifecycle_as_of": datetime(
                2026,
                7,
                24,
                12,
                tzinfo=UTC,
            ),
        },
        {
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "postgres",
            "mode": "repeatable_read_read_only",
            "lifecycle_as_of": datetime(
                2026,
                7,
                24,
                12,
                tzinfo=UTC,
            ),
        },
        {
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "custom",
            "mode": "transaction_snapshot",
            "lifecycle_as_of": datetime(
                2026,
                7,
                24,
                12,
                tzinfo=UTC,
            ),
        },
    ],
    ids=[
        "missing-clock",
        "invalid-clock",
        "naive-clock",
        "sqlite-mode-mismatch",
        "postgres-missing-snapshot-id",
        "unknown-backend",
    ],
)
def test_occurrence_reader_rejects_invalid_snapshot_lifecycle_proof(
    snapshot_proof: Mapping[str, object],
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        snapshot_proof=snapshot_proof,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 13, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 1
    assert store.snapshot_end_calls == 1
    assert store.occurrence_search_calls == []


def test_occurrence_reader_normalizes_aware_iso_snapshot_clock_to_utc() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        snapshot_proof={
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
            "lifecycle_as_of": "2026-07-24T14:00:00+02:00",
        },
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 13, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["count"] == 1
    assert {call["as_of"] for call in store.occurrence_search_calls} == {datetime(2026, 7, 24, 12, tzinfo=UTC)}


def test_occurrence_reader_fails_closed_when_snapshot_cleanup_fails() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        fail_snapshot_end=True,
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 1
    assert store.snapshot_end_calls == 1


def test_occurrence_reader_stays_dormant_for_non_count_and_minimal_queries() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )
    non_count = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Tell me about my bike service history.")
    )
    minimal = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            context_depth="minimal",
        )
    )

    assert "aggregation" not in non_count
    assert "aggregation" not in minimal
    assert store.occurrence_search_calls == []


def test_occurrence_reader_rejects_a_generic_fuzzy_count_key_overlap() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    _retarget_occurrence_test_unit(
        units[0],
        [evidence[0]],
        action="service",
        object_leaf="car",
        count_key="car service",
        canonical_text="Car service occurrence",
    )
    memories[0]["canonical_text"] = "Car service occurrence"
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert any(call["selector_key"] is None for call in store.occurrence_search_calls)
    assert any(call["selector_key"] == "v1|a=exact:service|o=exact:bike" for call in store.occurrence_search_calls)


@pytest.mark.parametrize(
    ("query", "count_key"),
    [
        ("How many times did I visit the year?", "visit month"),
        ("How many times did I spend time?", "spend year"),
        ("How many times did I work this month?", "work year"),
    ],
)
def test_occurrence_matcher_never_discards_persisted_temporal_object_tokens(
    query: str,
    count_key: str,
) -> None:
    intent = vnext_retrieval_module.vnext_coverage_query.detect_aggregation_intent(query)
    assert intent is not None
    anchor = vnext_retrieval_module.parse_temporal_anchor(
        query,
        reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
    )

    assert (
        vnext_retrieval_module._occurrence_query_matches_count_key(
            query,
            intent=intent,
            count_key=count_key,
            anchor=anchor,
        )
        is False
    )


@pytest.mark.parametrize(
    ("query", "count_key"),
    [
        ("How many times did I visit the year?", "visit year"),
        ("How many times did I spend time?", "spend time"),
        ("How many times did I service my bike this week?", "bike service"),
    ],
)
def test_occurrence_matcher_removes_only_proven_query_grammar(
    query: str,
    count_key: str,
) -> None:
    intent = vnext_retrieval_module.vnext_coverage_query.detect_aggregation_intent(query)
    assert intent is not None
    anchor = vnext_retrieval_module.parse_temporal_anchor(
        query,
        reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
    )

    assert vnext_retrieval_module._occurrence_query_matches_count_key(
        query,
        intent=intent,
        count_key=count_key,
        anchor=anchor,
    )


@pytest.mark.parametrize(
    ("past_tense", "canonical"),
    [
        ("passed", "pass"),
        ("missed", "miss"),
        ("crossed", "cross"),
        ("buzzed", "buzz"),
        ("serviced", "service"),
    ],
)
def test_occurrence_token_root_handles_regular_ed_endings(
    past_tense: str,
    canonical: str,
) -> None:
    assert vnext_retrieval_module._occurrence_token_root(past_tense) == canonical


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I not service my bike?",
        "How many times did I never service my bike?",
        "How many times did I avoid servicing my bike?",
        "How many times did I fail to service my bike?",
        "How many times was I without servicing my bike?",
        "How many times didn't I service my bike?",
        "How many times did I skip servicing my bike?",
        "How many times did I miss a bike service?",
        "How many times did I cancel my bike service?",
        "How many times did I refuse to service my bike?",
        "How many times was I unable to service my bike?",
        "How many times did I intend to service my bike?",
        "How many times did I plan to service my bike?",
        "How many times did I almost service my bike?",
        "How many times did I try to service my bike?",
        "How many times did I want to service my bike?",
    ],
)
def test_occurrence_reader_stays_dormant_for_unsupported_query_polarity(
    query: str,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query=query,
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 0
    assert store.snapshot_end_calls == 0
    assert store.occurrence_search_calls == []
    assert store.evidence_search_calls == []


@pytest.mark.parametrize(
    "query",
    [
        "How many times did Bob visit the museum?",
        "How many times did my partner visit the museum?",
        "How many times did Alice visit the museum?",
        "How many times was the museum visited?",
    ],
)
def test_occurrence_reader_never_attributes_user_units_to_another_actor(
    query: str,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    for unit in units:
        unit["count_key"] = "visit museum"
        unit["canonical_text"] = "I visited the museum."
    for memory in memories:
        memory["canonical_text"] = "I visited the museum."
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query=query,
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 0
    assert store.occurrence_search_calls == []


def test_occurrence_reader_does_not_answer_distinct_object_cardinality() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    for index, unit in enumerate(units):
        _retarget_occurrence_test_unit(
            unit,
            [evidence[index]],
            action="visit",
            object_leaf="museum",
            count_key="visit museum",
            canonical_text="I visited the same museum.",
        )
    for memory in memories:
        memory["canonical_text"] = "I visited the same museum."
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many museums did I visit?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 1
    assert store.snapshot_end_calls == 1


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I visit the museum with Bob?",
        "How many times did I visit the art museum?",
        "How many times did I visit the museum in Paris?",
        "How many times did I visit the museum for work?",
    ],
)
def test_occurrence_reader_rejects_unsigned_query_qualifiers(
    query: str,
) -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    for index, unit in enumerate(units):
        _retarget_occurrence_test_unit(
            unit,
            [evidence[index]],
            action="visit",
            object_leaf="museum",
            count_key="visit museum",
            canonical_text="I visited the museum.",
        )
    for memory in memories:
        memory["canonical_text"] = "I visited the museum."
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query=query,
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 1
    assert store.snapshot_end_calls == 1
    assert store.evidence_search_calls


def test_occurrence_reader_rejects_overbounded_natural_query_qualifiers() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    for index, unit in enumerate(units):
        _retarget_occurrence_test_unit(
            unit,
            [evidence[index]],
            action="paint",
            object_leaf="fence",
            count_key="paint fence",
            canonical_text="I painted the fence.",
        )
    for memory in memories:
        memory["canonical_text"] = "I painted the fence."
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query=(
                "How many times did I paint the ancient blue cracked "
                "detailed enormous heavy ornate polished weathered fence?"
            ),
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack
    assert store.snapshot_calls == 0
    assert store.occurrence_search_calls == []


def test_occurrence_reader_reports_mixed_predicates_as_a_lower_bound() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    _retarget_occurrence_test_unit(
        units[1],
        [evidence[1]],
        action="service",
        object_leaf="car",
        count_key="car service",
        canonical_text="Car service occurrence.",
    )
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "at_least"
    assert pack["aggregation"]["lower_bound"] == 1
    assert pack["aggregation"]["upper_bound"] is None
    assert pack["aggregation"]["accepted_units"] == {
        "matching": 1,
        "disjoint_proven": 0,
        "relation_unknown": 1,
    }


def test_occurrence_reader_does_not_hide_a_shared_token_sibling() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(2)
    _retarget_occurrence_test_unit(
        units[1],
        [evidence[1]],
        action="service",
        object_leaf="car",
        count_key="car service",
        canonical_text="Car service occurrence.",
    )
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "at_least"
    assert pack["aggregation"]["lower_bound"] == 1
    assert pack["aggregation"]["accepted_units"]["relation_unknown"] == 1
    assert any(call["selector_key"] is None for call in store.occurrence_search_calls)


def test_occurrence_reader_different_key_pending_claim_preserves_louvre_lower_bound() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    _retarget_occurrence_test_unit(
        units[0],
        [evidence[0]],
        action="visit",
        object_leaf="louvre",
        count_key="visit louvre",
        canonical_text="Visited the Louvre.",
    )
    memories[0]["canonical_text"] = "Visited the Louvre."
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
        unresolved=[
            _occurrence_test_unresolved_claim(
                "claim-compound-tour",
                action="tour",
                object_leaf="montmartre",
                count_key="tour montmartre",
            )
        ],
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I visit the Louvre?",
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["lower_bound"] == 1
    assert pack["aggregation"]["upper_bound"] == 2
    assert "count" not in pack["aggregation"]
    assert store.unresolved_search_calls[0]["count_key"] is None


def test_occurrence_reader_rejects_stale_or_scope_leaking_evidence() -> None:
    memories, units, evidence = _reviewed_occurrence_rows(1)
    evidence[0]["unit_review_receipt_digest"] = "f" * 64
    memories[0]["project_id"] = "secret-project"
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I service my bike?",
            projects=("bike",),
            reference_time=datetime(2026, 7, 24, 12, 0, tzinfo=UTC),
        )
    )

    assert "aggregation" not in pack


# ---------------------------------------------------------------------------
# Occurrence query-plan grammar: ordinary English shapes, and the shapes the
# parser refuses on purpose. Every case here is asserted at the plan level,
# where a wrong selector would be produced, rather than at the aggregation
# level, where a wrong selector is currently masked by the zero-match guard.
# ---------------------------------------------------------------------------


_OCCURRENCE_PLAN_REFERENCE_TIME = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def _occurrence_plan_for(query: str) -> vnext_retrieval_module._OccurrenceQueryPlan | None:
    intent = vnext_retrieval_module.vnext_coverage_query.detect_aggregation_intent(query)
    anchor = vnext_retrieval_module.parse_temporal_anchor(
        query,
        reference_time=_OCCURRENCE_PLAN_REFERENCE_TIME,
    )
    return vnext_retrieval_module._occurrence_query_plan(query, intent, anchor=anchor)


def _occurrence_plan_atoms(
    plan: vnext_retrieval_module._OccurrenceQueryPlan,
) -> list[tuple[str, str, tuple[str, ...]]]:
    return [
        (
            str(atom["action"]["leaf"]),
            str(atom["object"]["leaf"]),
            tuple(str(value) for value in atom["object"]["qualifiers"]),
        )
        for atom in plan.predicate_atoms
    ]


@pytest.mark.parametrize(
    ("query", "plain"),
    [
        (
            "How many times did I visit the museum in total?",
            "How many times did I visit the museum?",
        ),
        (
            "How many times have I visited the museum altogether?",
            "How many times have I visited the museum?",
        ),
        (
            "How many books did I read in total?",
            "How many books did I read?",
        ),
        (
            "How many cakes did I bake in all?",
            "How many cakes did I bake?",
        ),
        (
            "How many pizzas did I make overall?",
            "How many pizzas did I make?",
        ),
        (
            "How many times did I bake bread, in total?",
            "How many times did I bake bread?",
        ),
        (
            "How many books did I read in total, altogether?",
            "How many books did I read?",
        ),
    ],
)
def test_a_trailing_summative_adverbial_reaches_the_plain_count_plan(
    query: str,
    plain: str,
) -> None:
    """ "... in total" restates the whole history; it cannot change a count."""

    plan = _occurrence_plan_for(query)
    plain_plan = _occurrence_plan_for(plain)

    assert plain_plan is not None
    assert plan is not None
    assert plan.selector_keys == plain_plan.selector_keys
    assert plan.aggregation_basis == plain_plan.aggregation_basis
    assert _occurrence_plan_atoms(plan) == _occurrence_plan_atoms(plain_plan)
    # The adverbial must not survive as an object qualifier: a stored unit
    # carries no "in"/"total" qualifier, so leaving it here would silently
    # guarantee a non-match.
    for _action, _object_leaf, qualifiers in _occurrence_plan_atoms(plan):
        assert "total" not in qualifiers
        assert "in" not in qualifiers


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("How many times did I check the total?", ("check", "total", ())),
        ("How many overalls did I buy?", ("acquire", "overall", ())),
        ("How many times did I paint the hall?", ("paint", "hall", ())),
    ],
)
def test_a_summative_adverbial_never_eats_a_real_object_head(
    query: str,
    expected: tuple[str, str, tuple[str, ...]],
) -> None:
    """Only unambiguously adverbial trailing forms are removed."""

    plan = _occurrence_plan_for(query)

    assert plan is not None
    assert _occurrence_plan_atoms(plan) == [expected]


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I visit the museum yesterday in total?",
        "How many books did I read last year in total?",
        "How many times did I bake bread this week altogether?",
    ],
)
def test_a_summative_adverbial_leaves_a_resolved_window_still_bounding_the_read(
    query: str,
) -> None:
    """Removing the adverbial re-exposes a temporal anchor to the stripper.

    The window itself is enforced by the reader from the anchor, not by the
    plan, so the plan must be the plain one AND the anchor must still be
    present for the read to stay bounded.
    """

    anchor = vnext_retrieval_module.parse_temporal_anchor(
        query,
        reference_time=_OCCURRENCE_PLAN_REFERENCE_TIME,
    )
    plan = _occurrence_plan_for(query)

    assert anchor is not None
    assert anchor.window_start is not None and anchor.window_end is not None
    assert plan is not None
    for _action, _object_leaf, qualifiers in _occurrence_plan_atoms(plan):
        assert qualifiers == ()


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I visit the museum last summer?",
        "How many times did I visit the museum this weekend?",
        "How many times did I go swimming yesterday morning?",
        "How many times did I read the paper last night?",
        "How many times did I visit the museum the following week?",
        "How many times did I visit the museum a week ago?",
        "How many times did I bake bread recently?",
        "How many times did I visit the museum next month?",
        # Bare time adverbs and date names the anchor cannot resolve without
        # an anchoring preposition, so nothing upstream removes them.
        "How many times did I visit the museum tonight?",
        "How many times did I visit the museum earlier?",
        "How many times did I visit the museum Saturday?",
        "How many times did I bake bread August?",
        "How many times did I visit the museum summer?",
    ],
)
def test_an_unresolved_temporal_tail_never_becomes_the_counted_object(
    query: str,
) -> None:
    """A window the anchor could not resolve must not be read as an object.

    Both outcomes of accepting one are wrong: heading on the time noun
    counts a predicate nobody asked about, and dropping it counts over all
    time, which answers a strictly broader question.
    """

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I visit the museum again?",
        "How many times did I visit the museum briefly?",
        "How many times did I visit the museum together?",
        "How many times did I visit the museum alone?",
        "How many times did I visit the museum twice?",
        "How many times did I visit the museum myself?",
        "How many times did I ride my bike home?",
        "How many times did I bake bread over?",
    ],
)
def test_an_adverbial_tail_never_becomes_the_counted_object(query: str) -> None:
    """An adverb is never the thing a count question counts."""

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I visit the museum, the gallery?",
        "How many times did I visit the museum (with Bob)?",
        "How many times did I read the book; the magazine?",
    ],
)
def test_punctuation_inside_an_object_phrase_is_refused(query: str) -> None:
    """A bare noun phrase has no internal punctuation.

    Without this, "the museum, the gallery" heads on "gallery" and quietly
    drops the museum, which is a selector that means something else.
    """

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I visit the museum where Bob works?",
        "How many times did I visit the museum that I like?",
        "How many times did I visit the museum I like?",
        "How many times did I visit the museum when Bob called?",
        "How many times did I visit the museum because it rained?",
    ],
)
def test_a_subordinate_clause_never_becomes_the_counted_object(query: str) -> None:
    """A clause narrows the question and its verb is not the object head."""

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I visit the museum 2023?",
        "How many times did I visit the museum summer 2023?",
        "How many times did I run 5k?",
        "How many times did I eat at 3 restaurants?",
        "How many times did I visit the café?",
        "How many times did I visit the museum 東京?",
    ],
)
def test_an_object_narrowing_the_tokenizer_would_discard_is_refused(
    query: str,
) -> None:
    """A discarded token is the one failure mode that widens the question.

    "the museum 2023" must not silently become the all-time question, and a
    wholly non-ASCII object must not vanish into an unqualified head.
    """

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many bikes do I currently have?",
        "How many cars do I still own?",
        "How many bikes have I got?",
        "How many cars have we got?",
        "How many times do I go to the gym in a typical week?",
        "How many times did I visit the gym regularly?",
        "How many times did I visit the museum typically?",
        "How many books did I read on average?",
        "How many times did I swim weekly?",
        "How many times did I swim regularly?",
    ],
)
def test_present_state_and_habitual_rate_questions_are_refused(query: str) -> None:
    """Neither family is a count of stored completed events.

    A present-tense state question asks what is true now; the substrate
    stores acquisitions, not an inventory, so counting them would over-count
    anything since sold or given away. A habitual-rate question asks for a
    rate, and the substrate holds no denominator to divide by.
    """

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I read it?",
        "How many times did I watch them?",
        "How many times did I buy one?",
        "How many times did I clean everything?",
    ],
)
def test_a_referring_expression_never_becomes_the_counted_object(query: str) -> None:
    """An unresolvable referent would make the literal token the object."""

    assert _occurrence_plan_for(query) is None


def test_a_prepositional_narrowing_stays_in_the_query_qualifiers() -> None:
    """The narrowing is kept, never dropped, so the match can only narrow.

    ``build_occurrence_aggregation`` compares qualifier tuples exactly, so
    carrying "with Bob" into the atom is what stops a "museum with Bob"
    question from counting plain museum visits.
    """

    narrowed = _occurrence_plan_for("How many times did I visit the museum with Bob?")
    plain = _occurrence_plan_for("How many times did I visit the museum?")

    assert narrowed is not None and plain is not None
    assert _occurrence_plan_atoms(plain) == [("visit", "museum", ())]
    assert _occurrence_plan_atoms(narrowed) == [("visit", "museum", ("bob", "with"))]
    assert _occurrence_plan_atoms(narrowed) != _occurrence_plan_atoms(plain)


@pytest.mark.parametrize(
    "query",
    [
        "How many books did I buy from the bookstore?",
        "How many cakes did I bake for the party?",
        "How many movies did I watch with my sister?",
        "How many meals did I eat at the restaurant?",
        "How many books did I read for work?",
    ],
)
def test_an_object_cardinality_tail_the_schema_cannot_express_is_refused(
    query: str,
) -> None:
    """The object-cardinality action must still end the question.

    A summative adverbial and a resolvable temporal phrase are removed
    before this point. Any other trailing complement narrows the question
    in a way the predicate schema records nothing about, so admitting it
    and ignoring it would count a strictly larger set.
    """

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I go to the gym?",
        "How many times did I eat out?",
        "How many times did I pick up the parcel?",
    ],
)
def test_a_multiword_action_no_write_path_can_produce_is_refused(query: str) -> None:
    """A verb-plus-particle leaf is unreachable from the write path.

    ``vnext_occurrence_write`` only ever hands the taxonomy a single verb
    token, so an ``a=exact:go_to`` selector searches for a predicate that
    cannot exist.
    """

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I bake and cook?",
        "How many books did I read from my mum and dad?",
        "How many cakes and pies did I bake?",
    ],
)
def test_coordination_stays_refused_in_a_count_query(query: str) -> None:
    """ "and" is under-determined between union and intersection here."""

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I and my wife visit the museum?",
        "How many times did we and the kids visit the zoo?",
        "How many times did I and Bob bake bread?",
        "How many times did I and my brother watch movies?",
        "How many times have I and my wife visited the museum?",
    ],
)
def test_a_coordinated_subject_never_becomes_the_counted_action(
    query: str,
) -> None:
    """A coordinated SUBJECT is the case only the query-level bail catches.

    ``_OCCURRENCE_QUERY_WORD`` matches the literal token "and", so in "how
    many times did I and my wife visit the museum" the conjunction lands in
    the ACTION capture, not the object phrase. The object parser's own "and"
    check never sees it and the plan comes out as ``a=exact:and`` with a
    perfectly ordinary-looking object. Predicate and object coordination are
    refused elsewhere; this shape reaches nothing else.
    """

    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    ("query", "plain"),
    [
        (
            "How many times did I visit the museum in total.",
            "How many times did I visit the museum?",
        ),
        (
            "How many times did I visit the museum in total?!",
            "How many times did I visit the museum?",
        ),
        (
            "How many times did I visit the museum in total!",
            "How many times did I visit the museum?",
        ),
        (
            "How many books did I read altogether.",
            "How many books did I read?",
        ),
    ],
)
def test_a_summative_adverbial_is_stripped_under_sentence_punctuation(
    query: str,
    plain: str,
) -> None:
    """Callers only normalize away "?", so the pattern owns the rest.

    A trailing "." or "!" must not leave the adverbial sitting in the object
    phrase, which is the exact defect the strip exists to remove.
    """

    plan = _occurrence_plan_for(query)
    plain_plan = _occurrence_plan_for(plain)

    assert plain_plan is not None
    assert plan is not None
    assert _occurrence_plan_atoms(plan) == _occurrence_plan_atoms(plain_plan)
    for _action, _object_leaf, qualifiers in _occurrence_plan_atoms(plan):
        assert "total" not in qualifiers
        assert "in" not in qualifiers


@pytest.mark.parametrize(
    ("query", "plain"),
    [
        (
            "How many times did I visit the museum in total in March?",
            "How many times did I visit the museum?",
        ),
        (
            "How many times did I visit the museum in total last month?",
            "How many times did I visit the museum?",
        ),
        (
            "How many books did I read in total in 2023?",
            "How many books did I read?",
        ),
        (
            "How many times did I bake bread altogether this week?",
            "How many times did I bake bread?",
        ),
    ],
)
def test_a_summative_adverbial_is_stripped_on_either_side_of_the_anchor(
    query: str,
    plain: str,
) -> None:
    """The adverbial reads naturally before OR after the temporal phrase.

    Stripping only before the anchor resolves leaves "... in total in March"
    carrying ("in", "total") as object qualifiers once the anchor text is
    removed, so the strip runs again on the anchor-free text. The window
    itself stays enforced by the reader from the anchor.
    """

    anchor = vnext_retrieval_module.parse_temporal_anchor(
        query,
        reference_time=_OCCURRENCE_PLAN_REFERENCE_TIME,
    )
    plan = _occurrence_plan_for(query)
    plain_plan = _occurrence_plan_for(plain)

    assert anchor is not None
    assert plain_plan is not None
    assert plan is not None
    assert _occurrence_plan_atoms(plan) == _occurrence_plan_atoms(plain_plan)
    for _action, _object_leaf, qualifiers in _occurrence_plan_atoms(plan):
        assert qualifiers == ()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "How many books did I read in total, altogether",
            "How many books did I read",
        ),
        (
            "How many books did I read in total, altogether, overall",
            "How many books did I read",
        ),
        (
            "How many times did I visit the museum in total.",
            "How many times did I visit the museum",
        ),
        (
            "How many times did I visit the museum overall!",
            "How many times did I visit the museum",
        ),
        # A real object head is never an adverbial tail.
        (
            "How many times did I check the total",
            "How many times did I check the total",
        ),
        (
            "How many times did I visit the museum",
            "How many times did I visit the museum",
        ),
    ],
)
def test_the_summative_strip_peels_a_stacked_tail_in_one_call(
    text: str,
    expected: str,
) -> None:
    """The helper's own contract, independent of how often it is called.

    ``_occurrence_query_plan`` happens to invoke it twice (once before the
    anchor stripper and once after), which would mask a single-pass peel. This
    asserts the function fully peels on its own, so the bound stays honest.
    """

    assert vnext_retrieval_module._occurrence_query_without_summative_tail(text) == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("How many times did I check the total.", ("check", "total", ())),
        ("How many times did I check the total?", ("check", "total", ())),
    ],
)
def test_punctuation_tolerance_never_eats_a_real_object_head(
    query: str,
    expected: tuple[str, str, tuple[str, ...]],
) -> None:
    plan = _occurrence_plan_for(query)

    assert plan is not None
    assert _occurrence_plan_atoms(plan) == [expected]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("How many times did I host board game night?", ("host", "night", ("board", "game"))),
        ("How many times did I attend the movie night?", ("attend", "night", ("movie",))),
        ("How many times did I read the morning paper?", ("read", "paper", ("morning",))),
        ("How many times did I clean my home?", ("clean", "home", ())),
        ("How many times did I call my family?", ("call", "family", ())),
        ("How many times did I visit the art museum?", ("visit", "museum", ("art",))),
    ],
)
def test_an_ordinary_noun_head_that_reads_temporal_still_parses(
    query: str,
    expected: tuple[str, str, tuple[str, ...]],
) -> None:
    """The temporal refusal keys on the shape, not on a list of time nouns.

    "night", "morning" and "home" are ordinary object heads the write path
    stores verbatim; only a time-restricting modifier standing beside them,
    or a word that can only be a time adverb, makes the phrase temporal.
    """

    plan = _occurrence_plan_for(query)

    assert plan is not None
    assert _occurrence_plan_atoms(plan) == [expected]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("How many online orders did I place?", ("place", "order", ("online",))),
        ("How many solo albums did I buy?", ("acquire", "album", ("solo",))),
        ("How many offline backups did I make?", ("make", "backup", ("offline",))),
    ],
)
def test_an_attributive_modifier_is_not_mistaken_for_an_adverb(
    query: str,
    expected: tuple[str, str, tuple[str, ...]],
) -> None:
    """ "online" modifies a countable noun; only as a HEAD is it adverbial.

    Refusing these words outright would drop ordinary noun phrases, so the
    refusal is scoped to head position instead.
    """

    plan = _occurrence_plan_for(query)

    assert plan is not None
    assert _occurrence_plan_atoms(plan) == [expected]


@pytest.mark.parametrize(
    "query",
    [
        "How many times did I shop online?",
        "How many times did I work offline?",
        "How many times did I travel overseas?",
    ],
)
def test_a_modifier_standing_as_the_head_names_no_countable_object(
    query: str,
) -> None:
    assert _occurrence_plan_for(query) is None


@pytest.mark.parametrize(
    ("query", "expected_selectors"),
    [
        (
            "How many times did I buy anything?",
            ("v1|a=exact:acquire|o=*",),
        ),
        (
            "How many times did I visit the museum or the gallery?",
            ("v1|a=exact:visit|o=exact:museum", "v1|a=exact:visit|o=exact:gallery"),
        ),
        (
            "How many times did I bake or cook bread?",
            ("v1|a=exact:bake|o=exact:bread", "v1|a=exact:cook|o=exact:bread"),
        ),
    ],
)
def test_the_established_wildcard_and_or_shapes_still_plan(
    query: str,
    expected_selectors: tuple[str, ...],
) -> None:
    plan = _occurrence_plan_for(query)

    assert plan is not None
    assert plan.selector_keys == expected_selectors


def test_a_summative_adverbial_query_reaches_the_signed_occurrence_reader() -> None:
    """End to end: the adverbial no longer costs the whole aggregation."""

    memories, units, evidence = _reviewed_occurrence_rows(2)
    for index, unit in enumerate(units):
        _retarget_occurrence_test_unit(
            unit,
            [evidence[index]],
            action="visit",
            object_leaf="museum",
            count_key="visit museum",
            canonical_text="I visited the museum.",
        )
    for memory in memories:
        memory["canonical_text"] = "I visited the museum."
    store = OccurrenceReaderStore(
        memories=memories,
        units=units,
        evidence=evidence,
        coverage=_complete_occurrence_coverage(),
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I visit the museum in total?",
            reference_time=_OCCURRENCE_PLAN_REFERENCE_TIME,
        )
    )

    assert pack["aggregation"]["kind"] == "occurrence_count"
    assert pack["aggregation"]["lower_bound"] == 2
    assert any(call["selector_key"] == "v1|a=exact:visit|o=exact:museum" for call in store.occurrence_search_calls)
