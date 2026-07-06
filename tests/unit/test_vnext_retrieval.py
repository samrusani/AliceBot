from __future__ import annotations

from datetime import UTC, datetime
import re
import sqlite3
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_embeddings import VNextEmbeddingProviderError
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
    RRF_K,
    SOURCES_STAGE_DISABLED_BY_FLAG,
    STAGE_DISABLED_MINIMAL,
    STALENESS_NOTE_AFTER_DAYS,
    SUPERSESSION_STAGE_ENABLED,
    VECTOR_STAGE_DISABLED_NO_PROVIDER,
    VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest,
    VNextRetrievalService,
    VNextRetrievalValidationError,
    classify_query,
    entity_name_candidates,
    estimate_item_tokens,
    query_terms,
    reciprocal_rank_fusion,
)


_UNSET = object()


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
    ) -> None:
        self.memories = memories
        self.sources = sources
        self.open_loops = open_loops or []
        self.provenance_links = provenance_links or []
        self.vector_memories = vector_memories
        self.beliefs = beliefs
        self.entities = entities or []
        self.edges = edges or []
        self.events: list[dict[str, object]] = list(seeded_events or [])
        self.memory_search_domains: object = _UNSET
        self.source_search_domains: object = _UNSET
        self.open_loop_domains: object = _UNSET
        self.memory_search_kwargs: list[dict[str, object]] = []
        self.fts_match_any_queries: list[str] = []

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
            rows = [
                row
                for row in rows
                if row.get("project_id") in projects
                or (
                    isinstance(row.get("metadata_json"), dict)
                    and row["metadata_json"].get("project_id") in projects
                )
            ]
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
            if entity.get("normalized_name") in names
            or any(alias in names for alias in entity.get("aliases", []))
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
    assert pack["trace"]["fusion"] == {"algorithm": "reciprocal_rank_fusion", "k": RRF_K}
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
    assert pack["trace"]["vector_stage"].startswith("disabled: query embedding failed")
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
        estimate_item_tokens({key: value for key, value in row.items() if key != "deleted_at"})
        for row in memories[:2]
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
        VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(query="Alice", max_tokens=0)
        )


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

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice minimal store")
    )

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
        "source": "postgres_fts_or_fallback",
        "candidate_count": 1,
    }


def test_keyword_query_that_and_matches_does_not_use_the_fallback_on_sqlite() -> None:
    store = _sqlite_retrieval_store()
    memory = _commit_announcement_decision(store)

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice announcement")
    )

    assert [item["id"] for item in pack["relevant_memories"]] == [memory["id"]]
    assert pack["trace"]["stages"]["fts"] == {"source": "postgres_fts", "candidate_count": 1}


def test_single_token_miss_does_not_fire_the_or_fallback() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Unrelated note")], sources=[]
    )

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="kubernetes")
    )

    assert pack["relevant_memories"] == []
    assert pack["trace"]["stages"]["fts"] == {"source": "postgres_fts", "candidate_count": 0}
    assert store.fts_match_any_queries == []


def test_multi_token_miss_retries_once_with_match_any_and_reports_fallback_source() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Unrelated note")], sources=[]
    )

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
    compiled_events = [
        event for event in store.events if event["event_type"] == "retrieval.context_pack_compiled"
    ]
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

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice staleness check")
    )

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


def test_context_pack_degrades_contradictions_when_store_lacks_beliefs() -> None:
    store = InMemoryVNextRetrievalStore(
        memories=[_memory_row("memory-1", "Alice degrade check row.")],
        sources=[],
    )
    # Shadow the class attribute so getattr(...) is not callable, mirroring
    # stores (like the SQLite on-ramp) that have no belief surface at all.
    store.list_beliefs = None  # type: ignore[method-assign]

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice degrade check")
    )

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

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice recent changes")
    )

    recent = pack["recent_changes"]
    assert len(recent) == 5  # DEFAULT_RECENT_CHANGES_LIMIT
    assert all(change["event_type"].startswith("memory.") for change in recent)
    # Most recent events first (stub returns newest-first).
    assert recent[0]["event_id"] == "event-8"
    assert set(recent[0]) == {"event_id", "event_type", "target_id", "occurred_at", "actor_type"}
    assert pack["trace"]["stages"]["recent_changes"] == {"candidate_count": 5}


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
    assert by_id["memory-shared"]["rrf_score"] == pytest.approx(
        1.0 / (RRF_K + 3) + 1.0 / (RRF_K + 1), abs=1e-6
    )


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
    entities = [
        _entity_row(f"entity-{index}", f"Meridian{index}", mention_count=index) for index in range(1, 8)
    ]
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

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(query="Alice grouping")
    )

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
    assert [item["id"] for item in compile_with("balanced", one_memory_budget)["relevant_memories"]] == [
        "memory-old"
    ]
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
    assert [item["id"] for item in compile_with("balanced", one_memory_budget)["relevant_memories"]] == [
        "memory-epi-1"
    ]
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
        sum(contradictions_first["budget"]["allocation"].values())
        == contradictions_first["budget"]["token_estimate"]
    )


# -- deterministic depth tiers ------------------------------------------------------


def test_unknown_context_depth_is_rejected_with_choices_listed() -> None:
    store = InMemoryVNextRetrievalStore(memories=[], sources=[])

    with pytest.raises(VNextRetrievalValidationError) as excinfo:
        VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(query="Alice", context_depth="extreme")
        )

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
    assert stages["sources"] == {"source": "store_lexical", "candidate_count": 0, "status": STAGE_DISABLED_MINIMAL}
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
    # stays minimal (vector/graph still skipped).
    assert [item["id"] for item in pack["sources"]] == ["source-1"]
    assert pack["trace"]["stages"]["sources"] == {"source": "store_lexical", "candidate_count": 1}
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
