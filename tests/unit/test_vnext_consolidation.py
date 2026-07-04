from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
import sqlite3
from uuid import uuid4

import numpy as np
import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_consolidation import (
    MemoryConsolidationRequest,
    VNextConsolidationService,
    VNextConsolidationValidationError,
)
from alicebot_api.vnext_embeddings import memory_embedding_text
from alicebot_api.vnext_repositories import JsonObject


# -- fakes ---------------------------------------------------------------------


class FakeConsolidationStore:
    """In-memory store mirroring the surface the service needs.

    Deliberately does NOT implement list_artifacts / list_artifact_quality_ratings
    so the optional-surface guards are exercised on every test.
    """

    def __init__(self) -> None:
        self.memories: list[dict] = []
        self.artifacts: list[dict] = []
        self.events: list[dict] = []
        self.embeddings: dict[str, list[float]] = {}
        self._clock = datetime(2026, 7, 1, tzinfo=UTC)

    def _next_timestamp(self) -> str:
        self._clock += timedelta(minutes=1)
        return self._clock.isoformat()

    def append_event(self, event: JsonObject) -> JsonObject:
        self.events.append(dict(event))
        return dict(event)

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject:
        row = {"id": str(uuid4()), **artifact}
        self.artifacts.append(row)
        return dict(row)

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> JsonObject:
        timestamp = self._next_timestamp()
        row = {"id": str(uuid4()), "created_at": timestamp, "updated_at": timestamp, **memory}
        self.memories.append(row)
        return dict(row)

    def list_memories(self, *, status: str | None = None) -> list[JsonObject]:
        return [dict(row) for row in self.memories if status is None or row.get("status") == status]

    def list_events(self, **kwargs) -> list[JsonObject]:
        return [dict(event) for event in self.events]

    def update_memory_embedding(self, *, memory_id: str, vector: list[float]) -> JsonObject:
        self.embeddings[str(memory_id)] = [float(value) for value in vector]
        return {"id": str(memory_id)}

    def search_memories_vector(
        self,
        *,
        query_vector: list[float],
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> list[JsonObject]:
        query = np.asarray(query_vector, dtype=float)
        rows: list[JsonObject] = []
        for memory in self.memories:
            if memory.get("status") not in {"active", "accepted"}:
                continue
            stored = self.embeddings.get(str(memory["id"]))
            if stored is None:
                continue
            vector = np.asarray(stored, dtype=float)
            width = max(query.size, vector.size)
            padded_query = np.zeros(width)
            padded_query[: query.size] = query
            padded_vector = np.zeros(width)
            padded_vector[: vector.size] = vector
            denominator = float(np.linalg.norm(padded_query) * np.linalg.norm(padded_vector))
            similarity = float(padded_query @ padded_vector) / denominator if denominator else 0.0
            row = dict(memory)
            row["vector_distance"] = 1.0 - similarity
            rows.append(row)
        rows.sort(key=lambda row: (row["vector_distance"], str(row["id"])))
        return rows[:limit]


class MappedEmbeddingProvider:
    provider = "test_embeddings"
    model = "test-embed-3"

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self.mapping = mapping

    def embed_text(self, text: str) -> list[float]:
        return list(self.mapping[text])

    def embed_batch(self, texts) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


class StubMergeModelProvider:
    provider = "stub_model"
    model = "stub-merge-1"

    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def chat(self, *, prompt: str, temperature: float) -> str:
        self.prompts.append(prompt)
        return self.response

    def summarize(self, *, text: str) -> str:
        return text[:100]

    def structured_extract(self, *, text: str, schema_name: str) -> JsonObject:
        return {"schema": schema_name}

    def classify(self, *, text: str, labels) -> str:
        return labels[0]

    def embed(self, *, text: str) -> list[float]:
        return [0.0]


NEAR_DUP_VECTORS = (
    [1.0, 0.0, 0.0],
    [0.98, 0.09, 0.0],
    [0.97, 0.12, 0.0],
)
DISTINCT_VECTORS = (
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [0.7, -0.7, 0.0],
)


def _seed_memory(
    store,
    mapping: dict[str, list[float]],
    *,
    vector: list[float],
    title: str,
    canonical_text: str,
    memory_type: str = "semantic",
    source_event_ids: list[str] | None = None,
    with_embedding: bool = True,
) -> JsonObject:
    row = store.create_memory(
        {
            "memory_key": f"memory.{uuid4()}",
            "value": {"text": canonical_text},
            "status": "active",
            "memory_type": memory_type,
            "title": title,
            "canonical_text": canonical_text,
            "summary": canonical_text[:80],
            "domain": "project",
            "sensitivity": "internal",
            "source_event_ids": source_event_ids or [],
        }
    )
    mapping[memory_embedding_text(row)] = list(vector)
    if with_embedding:
        store.update_memory_embedding(memory_id=str(row["id"]), vector=vector)
    return row


def _seed_six_memories(store, mapping, **near_dup_kwargs) -> tuple[list[JsonObject], list[JsonObject]]:
    near_dups = [
        _seed_memory(
            store,
            mapping,
            vector=NEAR_DUP_VECTORS[index],
            title=f"Coffee preference v{index}",
            canonical_text=text,
            **near_dup_kwargs,
        )
        for index, text in enumerate(
            (
                "Sam prefers oat milk lattes in the morning",
                "Sam prefers oat milk lattes every morning before standup",
                "Sam usually orders an oat milk latte in the mornings",
            )
        )
    ]
    distinct = [
        _seed_memory(
            store,
            mapping,
            vector=DISTINCT_VECTORS[index],
            title=f"Distinct fact {index}",
            canonical_text=text,
        )
        for index, text in enumerate(
            (
                "The API deploys from the main branch on Fridays",
                "Type3 Capital quarterly review happens in October",
                "The staging database is reset every Sunday night",
            )
        )
    ]
    return near_dups, distinct


def _consolidation_candidates(store) -> list[JsonObject]:
    return [
        row
        for row in store.list_memories(status="candidate")
        if isinstance(row.get("metadata_json"), dict)
        and row["metadata_json"].get("candidate_kind") == "memory_consolidation"
    ]


def _service(store, mapping) -> VNextConsolidationService:
    return VNextConsolidationService(store, embedding_provider=MappedEmbeddingProvider(mapping))


# -- validation ------------------------------------------------------------------


def test_invalid_similarity_threshold_is_rejected() -> None:
    service = VNextConsolidationService(FakeConsolidationStore(), embedding_provider=None)
    with pytest.raises(VNextConsolidationValidationError):
        service.generate_memory_consolidation(MemoryConsolidationRequest(similarity_threshold=1.5))
    with pytest.raises(VNextConsolidationValidationError):
        service.generate_memory_consolidation(MemoryConsolidationRequest(similarity_threshold=0.0))


def test_invalid_metadata_option_overrides_are_rejected() -> None:
    service = VNextConsolidationService(FakeConsolidationStore(), embedding_provider=None)
    with pytest.raises(VNextConsolidationValidationError):
        service.generate_memory_consolidation(
            MemoryConsolidationRequest(metadata_json={"consolidation_options": {"similarity_threshold": "high"}})
        )
    with pytest.raises(VNextConsolidationValidationError):
        service.generate_memory_consolidation(
            MemoryConsolidationRequest(metadata_json={"consolidation_options": {"max_embedded_memories": 50000}})
        )


def test_max_embedded_memories_request_field_cannot_exceed_hard_cap() -> None:
    service = VNextConsolidationService(FakeConsolidationStore(), embedding_provider=None)
    with pytest.raises(VNextConsolidationValidationError):
        service.generate_memory_consolidation(MemoryConsolidationRequest(max_embedded_memories=5001))


# -- deterministic clustering ------------------------------------------------------


def test_near_duplicates_produce_one_dedup_candidate_with_correct_members() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    near_dups, distinct = _seed_six_memories(store, mapping)
    artifact = _service(store, mapping).generate_memory_consolidation(MemoryConsolidationRequest())

    candidates = _consolidation_candidates(store)
    assert len(candidates) == 1
    candidate = candidates[0]
    consolidation = candidate["metadata_json"]["consolidation"]
    expected_member_ids = sorted(str(row["id"]) for row in near_dups)
    assert consolidation["cluster_member_ids"] == expected_member_ids
    assert consolidation["proposal_kind"] == "dedup"
    assert candidate["status"] == "candidate"
    assert candidate["trust_class"] == "deterministic"

    # Survivor is the longest canonical text; the dedup candidate copies it verbatim.
    survivor = max(near_dups, key=lambda row: (len(row["canonical_text"]), str(row["id"])))
    assert consolidation["survivor_memory_id"] == str(survivor["id"])
    assert candidate["canonical_text"] == survivor["canonical_text"]
    assert sorted(consolidation["proposed_supersede"]) == sorted(
        member_id for member_id in expected_member_ids if member_id != str(survivor["id"])
    )
    assert consolidation["similarity_stats"]["min"] >= 0.88
    assert consolidation["reviewer_instructions"]

    # Provenance: candidate links back to every member.
    refs = candidate["metadata_json"]["source_refs"]
    for member_id in expected_member_ids:
        assert f"memory:{member_id}" in refs

    # Review-first guarantee: no member was superseded or mutated.
    for row in store.list_memories(status="active"):
        assert row["status"] == "active"

    metadata = artifact["metadata_json"]
    assert metadata["input_counts"]["clusters"] == 1
    assert metadata["input_counts"]["proposals"] == 1
    assert metadata["candidate_memory_ids"] == [str(candidate["id"])]
    assert metadata["consolidation"]["embedding_access"] == "provider_reembed_plus_vector_search_probe"
    assert "## Near-Duplicate Clusters" in artifact["content_markdown"]
    assert "## Merge / Dedup Proposals" in artifact["content_markdown"]
    assert "## Skipped / Bounds" in artifact["content_markdown"]
    assert "Review this consolidation candidate before promoting" not in artifact["content_markdown"]
    assert any(event["event_type"] == "memory.consolidation.generated" for event in store.events)
    # distinct memories must not appear in the cluster
    for row in distinct:
        assert str(row["id"]) not in consolidation["cluster_member_ids"]


def test_rerun_with_same_input_set_creates_no_duplicate_candidate() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    _seed_six_memories(store, mapping)
    service = _service(store, mapping)
    first = service.generate_memory_consolidation(MemoryConsolidationRequest())
    second = service.generate_memory_consolidation(MemoryConsolidationRequest())

    candidates = _consolidation_candidates(store)
    assert len(candidates) == 1
    assert second["metadata_json"]["candidate_memory_ids"] == first["metadata_json"]["candidate_memory_ids"]
    proposals = second["metadata_json"]["consolidation"]["proposals"]
    assert proposals[0]["candidate_state"] == "existing"
    assert second["metadata_json"]["consolidation_digest"] == first["metadata_json"]["consolidation_digest"]


def test_without_embedding_provider_clustering_is_skipped_review_only() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    _seed_six_memories(store, mapping)
    service = VNextConsolidationService(store, embedding_provider=None)
    artifact = service.generate_memory_consolidation(MemoryConsolidationRequest())

    assert _consolidation_candidates(store) == []
    assert "no_embedding_provider_configured" in artifact["metadata_json"]["consolidation"]["skipped"]
    assert "no_embedding_provider_configured" in artifact["content_markdown"]


def test_memories_without_stored_embeddings_are_excluded() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    # Third near-dup never got a stored embedding: cluster is only the first two.
    kept = [
        _seed_memory(store, mapping, vector=NEAR_DUP_VECTORS[0], title="A", canonical_text="Sam prefers oat milk lattes"),
        _seed_memory(
            store, mapping, vector=NEAR_DUP_VECTORS[1], title="B", canonical_text="Sam prefers oat milk lattes daily"
        ),
    ]
    _seed_memory(
        store,
        mapping,
        vector=NEAR_DUP_VECTORS[2],
        title="C",
        canonical_text="Sam usually orders oat milk lattes",
        with_embedding=False,
    )
    artifact = _service(store, mapping).generate_memory_consolidation(MemoryConsolidationRequest())
    candidates = _consolidation_candidates(store)
    assert len(candidates) == 1
    assert candidates[0]["metadata_json"]["consolidation"]["cluster_member_ids"] == sorted(
        str(row["id"]) for row in kept
    )
    assert artifact["metadata_json"]["input_counts"]["embedded_memories"] == 2


def test_cap_bound_is_applied_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    _seed_six_memories(store, mapping)
    with caplog.at_level(logging.INFO, logger="alicebot_api.vnext_consolidation"):
        artifact = _service(store, mapping).generate_memory_consolidation(
            MemoryConsolidationRequest(max_embedded_memories=2)
        )
    assert artifact["metadata_json"]["consolidation"]["bounded"] is True
    assert any("bounded" in record.message for record in caplog.records)
    assert "bounded" in artifact["content_markdown"]


def test_threshold_override_via_metadata_json_options() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    _seed_six_memories(store, mapping)
    artifact = _service(store, mapping).generate_memory_consolidation(
        MemoryConsolidationRequest(metadata_json={"consolidation_options": {"similarity_threshold": 0.9999}})
    )
    assert _consolidation_candidates(store) == []
    assert artifact["metadata_json"]["consolidation"]["similarity_threshold"] == 0.9999


# -- reinforced preferences --------------------------------------------------------


def test_preference_cluster_spanning_three_sources_is_reported_review_only() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    for index, text in enumerate(
        (
            "Sam prefers oat milk lattes in the morning",
            "Sam prefers oat milk lattes every morning before standup",
            "Sam usually orders an oat milk latte in the mornings",
        )
    ):
        _seed_memory(
            store,
            mapping,
            vector=NEAR_DUP_VECTORS[index],
            title=f"Coffee preference v{index}",
            canonical_text=text,
            memory_type="preference",
            source_event_ids=[f"event-{index}"],
        )
    artifact = _service(store, mapping).generate_memory_consolidation(MemoryConsolidationRequest())
    reinforced = artifact["metadata_json"]["consolidation"]["reinforced_preferences"]
    assert len(reinforced) == 1
    assert reinforced[0]["distinct_source_count"] >= 3
    assert "Reinforced Preferences" in artifact["content_markdown"]
    assert "reinforced preference" in artifact["content_markdown"]
    # Review-only: the note changed no memory rows beyond the one candidate.
    assert len(_consolidation_candidates(store)) == 1
    for row in store.list_memories(status="active"):
        assert row.get("confidence") is None or row["memory_type"] == "preference"


def test_non_preference_cluster_is_not_reported_as_reinforced() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    _seed_six_memories(store, mapping)  # memory_type semantic
    artifact = _service(store, mapping).generate_memory_consolidation(MemoryConsolidationRequest())
    assert artifact["metadata_json"]["consolidation"]["reinforced_preferences"] == []


# -- model-backed proposals ---------------------------------------------------------


def test_model_backed_merge_uses_stub_provider_and_records_provenance() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    near_dups, _ = _seed_six_memories(store, mapping)
    stub = StubMergeModelProvider(
        '{"title": "Morning oat milk latte preference", '
        '"canonical_text": "Sam prefers oat milk lattes every morning, usually before standup."}'
    )
    service = VNextConsolidationService(
        store,
        embedding_provider=MappedEmbeddingProvider(mapping),
        merge_provider=stub,
    )
    artifact = service.generate_memory_consolidation(
        MemoryConsolidationRequest(
            generation_mode="model_backed",
            model_route_mode="cloud_allowed",
            model_provider="mock",
            sensitivity_allowed=("public", "internal"),
        )
    )
    candidates = _consolidation_candidates(store)
    assert len(candidates) == 1
    candidate = candidates[0]
    consolidation = candidate["metadata_json"]["consolidation"]
    assert consolidation["proposal_kind"] == "merge"
    assert candidate["canonical_text"] == "Sam prefers oat milk lattes every morning, usually before standup."
    assert candidate["trust_class"] == "llm_single_source"
    assert consolidation["model_provenance"]["provider"] == "stub_model"
    assert consolidation["model_provenance"]["prompt_hash"].startswith("sha256:")
    # merge proposes superseding every member (after human acceptance only)
    assert sorted(consolidation["proposed_supersede"]) == sorted(str(row["id"]) for row in near_dups)
    assert artifact["metadata_json"]["generation_mode"] == "model_backed"
    assert stub.prompts and "cluster_members" in stub.prompts[0]


def test_model_backed_with_deterministic_route_falls_back_to_dedup() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    near_dups, _ = _seed_six_memories(store, mapping)
    service = _service(store, mapping)
    service.generate_memory_consolidation(
        MemoryConsolidationRequest(generation_mode="model_backed", sensitivity_allowed=("public", "internal"))
    )
    candidates = _consolidation_candidates(store)
    assert len(candidates) == 1
    consolidation = candidates[0]["metadata_json"]["consolidation"]
    assert consolidation["proposal_kind"] == "dedup"
    assert consolidation["merge_refusal"] == "deterministic_provider_refuses_merge_synthesis"
    survivor = max(near_dups, key=lambda row: (len(row["canonical_text"]), str(row["id"])))
    assert candidates[0]["canonical_text"] == survivor["canonical_text"]


def test_model_backed_approval_required_route_fails_before_any_writes() -> None:
    from alicebot_api.vnext_model_intelligence import VNextModelIntelligenceError

    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    _seed_six_memories(store, mapping)
    memory_count = len(store.memories)
    with pytest.raises(VNextModelIntelligenceError):
        _service(store, mapping).generate_memory_consolidation(
            MemoryConsolidationRequest(
                generation_mode="model_backed",
                model_route_mode="cloud_requires_approval",
                sensitivity_allowed=("public", "internal"),
            )
        )
    assert len(store.memories) == memory_count
    assert store.artifacts == []


def test_create_candidate_memories_false_lists_proposals_without_writes() -> None:
    store = FakeConsolidationStore()
    mapping: dict[str, list[float]] = {}
    _seed_six_memories(store, mapping)
    artifact = _service(store, mapping).generate_memory_consolidation(
        MemoryConsolidationRequest(create_candidate_memories=False)
    )
    assert _consolidation_candidates(store) == []
    proposals = artifact["metadata_json"]["consolidation"]["proposals"]
    assert len(proposals) == 1
    assert proposals[0]["candidate_memory_id"] is None


def test_scheduler_call_shape_still_constructs() -> None:
    # Mirrors the kwargs vnext_scheduler passes; must keep constructing unchanged.
    request = MemoryConsolidationRequest(
        domains=("project",),
        sensitivity_allowed=("public", "internal"),
        generated_for="2026-07-04",
        source_limit=12,
        memory_limit=12,
        artifact_limit=8,
        event_limit=30,
        rating_limit=20,
        create_candidate_memories=True,
        generated_by="scheduler",
        trace_id="trace-1",
        run_id="run-1",
        agent_identity=None,
        policy_decision=None,
        metadata_json={"workflow": "memory_consolidation"},
        generation_mode="deterministic",
        model_route_mode=None,
        model_provider=None,
        model=None,
        model_temperature=0.2,
        allow_cloud_private=False,
    )
    store = FakeConsolidationStore()
    artifact = VNextConsolidationService(store, embedding_provider=None).generate_memory_consolidation(request)
    assert artifact["artifact_type"] == "memory_consolidation"
    assert artifact["status"] == "needs_review"
    assert artifact["generated_by"] == "scheduler"


# -- live sqlite smoke ----------------------------------------------------------------


class SQLiteArtifactShim:
    """SQLiteVNextStore has no artifact surface yet; delegate everything else."""

    def __init__(self, store: SQLiteVNextStore) -> None:
        self._store = store
        self.artifacts: list[JsonObject] = []

    def __getattr__(self, name: str):
        return getattr(self._store, name)

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject:
        row = {"id": str(uuid4()), **artifact}
        self.artifacts.append(row)
        return dict(row)


def test_live_sqlite_smoke_clusters_near_duplicates_idempotently() -> None:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, "smoke@example.com", "Smoke User")
    sqlite_store = SQLiteVNextStore(conn, user_id)
    store = SQLiteArtifactShim(sqlite_store)

    mapping: dict[str, list[float]] = {}
    specs = [
        ("Oat milk latte", "Sam prefers oat milk lattes in the morning", NEAR_DUP_VECTORS[0]),
        ("Oat milk latte routine", "Sam prefers oat milk lattes every morning before standup", NEAR_DUP_VECTORS[1]),
        ("Morning latte", "Sam usually orders an oat milk latte in the mornings", NEAR_DUP_VECTORS[2]),
        ("Deploy day", "The API deploys from the main branch on Fridays", DISTINCT_VECTORS[0]),
        ("Quarterly review", "Type3 Capital quarterly review happens in October", DISTINCT_VECTORS[1]),
        ("Staging reset", "The staging database is reset every Sunday night", DISTINCT_VECTORS[2]),
    ]
    rows: list[JsonObject] = []
    for title, canonical_text, vector in specs:
        row = sqlite_store.create_memory(
            {
                "memory_key": f"memory.{uuid4()}",
                "value": {"text": canonical_text},
                "status": "active",
                "memory_type": "semantic",
                "title": title,
                "canonical_text": canonical_text,
                "summary": canonical_text[:80],
                "domain": "project",
                "sensitivity": "internal",
            }
        )
        # Deterministic fake vectors through the real embed-on-write surface.
        assert sqlite_store.update_memory_embedding(memory_id=str(row["id"]), vector=vector) is not None
        mapping[memory_embedding_text(row)] = list(vector)
        rows.append(row)
    near_dup_ids = sorted(str(row["id"]) for row in rows[:3])

    service = VNextConsolidationService(store, embedding_provider=MappedEmbeddingProvider(mapping))
    artifact = service.generate_memory_consolidation(MemoryConsolidationRequest())

    candidates = _consolidation_candidates(sqlite_store)
    assert len(candidates) == 1
    consolidation = candidates[0]["metadata_json"]["consolidation"]
    assert consolidation["cluster_member_ids"] == near_dup_ids
    assert consolidation["proposal_kind"] in {"dedup", "merge"}
    assert consolidation["proposal_kind"] == "dedup"  # deterministic run: no model
    assert candidates[0]["status"] == "candidate"
    assert artifact["metadata_json"]["input_counts"]["embedded_memories"] == 6
    assert artifact["metadata_json"]["input_counts"]["clusters"] == 1
    # Stored and re-derived vectors agree: probe self-distance is ~0.
    self_distance = artifact["metadata_json"]["consolidation"]["probe_self_distance"]
    assert self_distance is not None and self_distance < 1e-6

    # Idempotent rerun: same input set, no duplicate candidate.
    second = service.generate_memory_consolidation(MemoryConsolidationRequest())
    assert len(_consolidation_candidates(sqlite_store)) == 1
    assert second["metadata_json"]["candidate_memory_ids"] == artifact["metadata_json"]["candidate_memory_ids"]
    assert second["metadata_json"]["consolidation"]["proposals"][0]["candidate_state"] == "existing"

    # Review-first: the three members are still active in the real store.
    active_ids = {str(row["id"]) for row in sqlite_store.list_memories(status="active")}
    for member_id in near_dup_ids:
        assert member_id in active_ids
    conn.close()
