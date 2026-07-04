from __future__ import annotations

import re

import pytest

from alicebot_api.vnext_embeddings import VNextEmbeddingProviderError
from alicebot_api.vnext_retrieval import (
    RRF_K,
    VECTOR_STAGE_DISABLED_NO_PROVIDER,
    VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest,
    VNextRetrievalService,
    classify_query,
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
    ) -> None:
        self.memories = memories
        self.sources = sources
        self.open_loops = open_loops or []
        self.provenance_links = provenance_links or []
        self.vector_memories = vector_memories
        self.events: list[dict[str, object]] = []
        self.memory_search_domains: object = _UNSET
        self.source_search_domains: object = _UNSET
        self.open_loop_domains: object = _UNSET

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def _memory_text(self, row: dict[str, object]) -> str:
        parts = [row.get(key) for key in ("title", "canonical_text", "summary")]
        return " ".join(part for part in parts if isinstance(part, str)).casefold()

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, object]]:
        del query, sensitivity_allowed
        self.memory_search_domains = domains
        return self.memories[:limit]

    def search_memories_fts(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        del sensitivity_allowed
        self.memory_search_domains = domains
        terms = [term.casefold() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+", query)]
        rows = [row for row in self.memories if any(term in self._memory_text(row) for term in terms)]
        return rows[:limit]

    def search_memories_vector(
        self,
        *,
        query_vector: list[float],
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        del query_vector, domains, sensitivity_allowed
        if self.vector_memories is None:
            return []
        return self.vector_memories[:limit]

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
        del from_id, to_id
        return []


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
    assert pack["contradicting_evidence"] == []
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
