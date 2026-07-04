from __future__ import annotations

from datetime import UTC, datetime
import re

import pytest

from alicebot_api.vnext_embeddings import VNextEmbeddingProviderError
from alicebot_api.vnext_retrieval import (
    CONTRADICTIONS_STAGE_ENABLED,
    CONTRADICTIONS_STAGE_NO_STORE_SUPPORT,
    EXCLUSION_REASON_TOKEN_BUDGET,
    RRF_K,
    STALENESS_NOTE_AFTER_DAYS,
    VECTOR_STAGE_DISABLED_NO_PROVIDER,
    VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest,
    VNextRetrievalService,
    classify_query,
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
    ) -> None:
        self.memories = memories
        self.sources = sources
        self.open_loops = open_loops or []
        self.provenance_links = provenance_links or []
        self.vector_memories = vector_memories
        self.beliefs = beliefs
        self.events: list[dict[str, object]] = list(seeded_events or [])
        self.memory_search_domains: object = _UNSET
        self.source_search_domains: object = _UNSET
        self.open_loop_domains: object = _UNSET
        self.memory_search_kwargs: list[dict[str, object]] = []

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
    ) -> list[dict[str, object]]:
        del sensitivity_allowed, include_expired
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
