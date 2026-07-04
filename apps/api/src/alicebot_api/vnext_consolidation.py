"""Memory consolidation: near-duplicate clustering behind the review gate.

Pipeline (all review-only, nothing is promoted or superseded automatically):

1. Fetch the user's active/accepted memories (bounded, logged) and cluster
   near-duplicates by pairwise cosine over their embeddings.
2. Per cluster, build a merge (model-backed) or dedup (deterministic)
   proposal as a *candidate* memory carrying cluster membership, similarity
   stats, provenance, and per-member ``proposed_supersede`` markers.
3. Detect reinforced preferences: preference/routine clusters whose members
   span >= 3 distinct sources or days.
4. Emit a ``memory_consolidation`` report artifact with real sections.

Embedding access path
---------------------
Store rows never expose the raw embedding column (``MEMORY_COLUMNS`` excludes
it in both stores) and there is no bulk embeddings read. This service
therefore re-derives each memory's vector from the exact text the
embed-on-write path used (``memory_embedding_text``) via the configured
``EmbeddingProvider`` — reproducing the stored vector for unmodified rows —
and uses one ``search_memories_vector`` probe call as the read surface for
"which memories actually have stored embeddings" plus a self-distance drift
check. Without an embedding provider, clustering is skipped with an explicit
reason in the artifact.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
import json
import logging
from typing import Protocol

import numpy as np

from alicebot_api.vnext_embeddings import (
    MAX_EMBEDDINGS_BATCH_SIZE,
    EmbeddingProvider,
    VNextEmbeddingConfigurationError,
    VNextEmbeddingProviderError,
    get_embedding_provider,
    memory_embedding_text,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_model_intelligence import (
    BrainModelProvider,
    ConsolidationMergeRequest,
    ModelBackedRequest,
    ModelRoutingRequest,
    VNextModelIntelligenceError,
    build_model_backed_artifact,
    generate_consolidation_merge,
    resolve_model_route,
)
from alicebot_api.vnext_repositories import JsonObject


logger = logging.getLogger(__name__)

DEFAULT_CONSOLIDATION_LIMIT = 12
DEFAULT_SIMILARITY_THRESHOLD = 0.88
DEFAULT_MIN_CLUSTER_SIZE = 2
DEFAULT_MAX_CLUSTERS = 20
MAX_EMBEDDED_MEMORIES_HARD_CAP = 5000
PREFERENCE_MEMORY_TYPES = frozenset({"preference", "routine"})
REINFORCED_PREFERENCE_MIN_DISTINCT = 3
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
SENSITIVITY_RANK = {
    "public": 1,
    "internal": 2,
    "unknown": 2,
    "private": 3,
    "confidential": 4,
    "highly_sensitive": 5,
    "sacred": 6,
    "regulated": 6,
}


class VNextConsolidationValidationError(ValueError):
    """Raised when a memory-consolidation request is invalid."""


class VNextConsolidationStore(Protocol):
    """Required store surface. ``search_memories_vector``, ``search_sources``,
    ``list_artifacts`` and ``list_artifact_quality_ratings`` are used when
    present (checked via ``getattr``) so slimmer stores still work."""

    def append_event(self, event: JsonObject) -> JsonObject: ...

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def list_memories(self, *, status: str | None = None) -> list[JsonObject]: ...

    def list_events(self, **kwargs) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class MemoryConsolidationRequest:
    domains: tuple[str, ...] = ()
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    generated_for: str | None = None
    # source_limit/memory_limit/artifact_limit/event_limit/rating_limit are
    # kept for scheduler call-shape compatibility; they bound the report's
    # context scan, not the clustering pass (which uses max_embedded_memories).
    source_limit: int = DEFAULT_CONSOLIDATION_LIMIT
    memory_limit: int = DEFAULT_CONSOLIDATION_LIMIT
    artifact_limit: int = 8
    event_limit: int = 30
    rating_limit: int = 20
    create_candidate_memories: bool = True
    generated_by: str = "system"
    trace_id: str | None = None
    run_id: str | None = None
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    metadata_json: JsonObject = field(default_factory=dict)
    generation_mode: str = "deterministic"
    model_route_mode: str | None = None
    model_provider: str | None = None
    model: str | None = None
    model_temperature: float = 0.2
    allow_cloud_private: bool = False
    # Clustering knobs; also overridable via
    # metadata_json["consolidation_options"] = {"similarity_threshold": ...,
    # "max_embedded_memories": ..., "min_cluster_size": ..., "max_clusters": ...}.
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    max_embedded_memories: int = MAX_EMBEDDED_MEMORIES_HARD_CAP
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE
    max_clusters: int = DEFAULT_MAX_CLUSTERS


@dataclass(frozen=True, slots=True)
class _ClusteringOptions:
    similarity_threshold: float
    max_embedded_memories: int
    min_cluster_size: int
    max_clusters: int


@dataclass(slots=True)
class _ClusteringOutcome:
    clusters: list[list[JsonObject]] = field(default_factory=list)
    similarity_stats: dict[str, JsonObject] = field(default_factory=dict)
    active_count: int = 0
    embedded_count: int = 0
    bounded: bool = False
    probe_self_distance: float | None = None
    skipped: list[str] = field(default_factory=list)


def _validate_request(request: MemoryConsolidationRequest) -> None:
    if not request.sensitivity_allowed:
        raise VNextConsolidationValidationError("sensitivity_allowed must not be empty")
    if request.generation_mode not in {"deterministic", "model_backed"}:
        raise VNextConsolidationValidationError("generation_mode must be deterministic or model_backed")
    for field_name in ("source_limit", "memory_limit", "artifact_limit", "event_limit", "rating_limit"):
        value = getattr(request, field_name)
        if value < 1 or value > 100:
            raise VNextConsolidationValidationError(f"{field_name} must be between 1 and 100")
    if request.model_temperature < 0.0 or request.model_temperature > 2.0:
        raise VNextConsolidationValidationError("model_temperature must be between 0.0 and 2.0")


def _clustering_options(request: MemoryConsolidationRequest) -> _ClusteringOptions:
    overrides = request.metadata_json.get("consolidation_options") if isinstance(request.metadata_json, dict) else None
    overrides = overrides if isinstance(overrides, dict) else {}

    def _number(key: str, default: float) -> float:
        value = overrides.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VNextConsolidationValidationError(f"consolidation_options.{key} must be a number")
        return float(value)

    threshold = _number("similarity_threshold", request.similarity_threshold)
    cap = int(_number("max_embedded_memories", request.max_embedded_memories))
    min_cluster = int(_number("min_cluster_size", request.min_cluster_size))
    max_clusters = int(_number("max_clusters", request.max_clusters))
    if not (0.0 < threshold <= 1.0):
        raise VNextConsolidationValidationError("similarity_threshold must be in (0.0, 1.0]")
    if not (2 <= cap <= MAX_EMBEDDED_MEMORIES_HARD_CAP):
        raise VNextConsolidationValidationError(
            f"max_embedded_memories must be between 2 and {MAX_EMBEDDED_MEMORIES_HARD_CAP}"
        )
    if not (2 <= min_cluster <= 50):
        raise VNextConsolidationValidationError("min_cluster_size must be between 2 and 50")
    if not (1 <= max_clusters <= 100):
        raise VNextConsolidationValidationError("max_clusters must be between 1 and 100")
    return _ClusteringOptions(
        similarity_threshold=threshold,
        max_embedded_memories=cap,
        min_cluster_size=min_cluster,
        max_clusters=max_clusters,
    )


def _allowed_domains(request: MemoryConsolidationRequest) -> list[str] | None:
    return list(request.domains) if request.domains else None


def _allowed_sensitivity(request: MemoryConsolidationRequest) -> list[str]:
    return list(request.sensitivity_allowed)


def _highest_sensitivity(rows: list[JsonObject]) -> str:
    sensitivities = [str(row.get("sensitivity", "unknown")) for row in rows]
    if not sensitivities:
        return "unknown"
    return max(sensitivities, key=lambda value: SENSITIVITY_RANK.get(value, SENSITIVITY_RANK["unknown"]))


def _domain(request: MemoryConsolidationRequest, rows: list[JsonObject]) -> str:
    if len(request.domains) == 1:
        return request.domains[0]
    domains = {row.get("domain") for row in rows if isinstance(row.get("domain"), str)}
    if len(domains) == 1:
        return str(next(iter(domains)))
    return "unknown"


def _text(row: JsonObject) -> str:
    for key in ("canonical_text", "summary", "title", "content_markdown", "memory_key"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        raw_text = metadata.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            return " ".join(raw_text.split())
    return str(row.get("id", "item"))


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def _scoped_rows(
    rows: list[JsonObject],
    *,
    domains: list[str] | None,
    sensitivity_allowed: list[str],
) -> list[JsonObject]:
    allowed_sensitivity = set(sensitivity_allowed)
    scoped: list[JsonObject] = []
    for row in rows:
        sensitivity = str(row.get("sensitivity") or "unknown")
        if sensitivity not in allowed_sensitivity:
            continue
        if domains:
            domain = str(row.get("domain") or "unknown")
            if domain not in domains and domain != "unknown":
                continue
        scoped.append(row)
    return scoped


def _member_source_ids(row: JsonObject) -> set[str]:
    sources: set[str] = set()
    event_ids = row.get("source_event_ids")
    if isinstance(event_ids, list):
        sources.update(str(item) for item in event_ids if item is not None)
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        source_id = metadata.get("source_id")
        if source_id is not None:
            sources.add(f"source:{source_id}")
        refs = metadata.get("source_refs")
        if isinstance(refs, list):
            sources.update(str(ref) for ref in refs if isinstance(ref, str) and ref.startswith("source:"))
    return sources


def _member_day(row: JsonObject) -> str | None:
    for key in ("first_seen_at", "created_at", "last_seen_at"):
        value = row.get(key)
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]
    return None


def _member_source_refs(members: list[JsonObject]) -> list[str]:
    refs: list[str] = []
    for member in members:
        if member.get("id") is not None:
            refs.append(f"memory:{member['id']}")
        metadata = member.get("metadata_json")
        if isinstance(metadata, dict) and isinstance(metadata.get("source_refs"), list):
            refs.extend(str(ref) for ref in metadata["source_refs"] if isinstance(ref, str))
    return list(dict.fromkeys(refs))


def _union_source_event_ids(members: list[JsonObject]) -> list[str]:
    merged: list[str] = []
    for member in members:
        event_ids = member.get("source_event_ids")
        if isinstance(event_ids, list):
            merged.extend(str(item) for item in event_ids if item is not None)
    return list(dict.fromkeys(merged))


def _existing_cluster_candidates(store: VNextConsolidationStore) -> dict[str, str]:
    """Map cluster consolidation_digest -> existing candidate memory id."""
    existing: dict[str, str] = {}
    for memory in store.list_memories(status="candidate"):
        metadata = memory.get("metadata_json")
        if not isinstance(metadata, dict) or memory.get("id") is None:
            continue
        digest = metadata.get("consolidation_digest")
        if isinstance(digest, str) and digest:
            existing.setdefault(digest, str(memory["id"]))
    return existing


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, left: int, right: int) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[max(root_left, root_right)] = min(root_left, root_right)


class VNextConsolidationService:
    def __init__(
        self,
        store: VNextConsolidationStore,
        *,
        embedding_provider: EmbeddingProvider | None | str = "ambient",
        merge_provider: BrainModelProvider | None = None,
    ) -> None:
        self.store = store
        if embedding_provider == "ambient":
            self.embedding_provider: EmbeddingProvider | None = get_embedding_provider()
        else:
            self.embedding_provider = embedding_provider  # type: ignore[assignment]
        self.merge_provider = merge_provider

    # -- clustering ------------------------------------------------------------

    def _cluster_memories(
        self,
        *,
        domains: list[str] | None,
        sensitivity: list[str],
        options: _ClusteringOptions,
    ) -> _ClusteringOutcome:
        outcome = _ClusteringOutcome()
        active_rows = [
            *self.store.list_memories(status="active"),
            *self.store.list_memories(status="accepted"),
        ]
        active_rows = _scoped_rows(active_rows, domains=domains, sensitivity_allowed=sensitivity)
        active_rows.sort(
            key=lambda row: (str(row.get("updated_at") or row.get("created_at") or ""), str(row.get("id"))),
            reverse=True,
        )
        outcome.active_count = len(active_rows)
        if len(active_rows) > options.max_embedded_memories:
            outcome.bounded = True
            logger.info(
                "memory consolidation bounded to %d most recently updated of %d active memories",
                options.max_embedded_memories,
                len(active_rows),
            )
            active_rows = active_rows[: options.max_embedded_memories]
        if not active_rows:
            outcome.skipped.append("no_active_memories_in_scope")
            return outcome
        if self.embedding_provider is None:
            outcome.skipped.append("no_embedding_provider_configured")
            return outcome
        search_memories_vector = getattr(self.store, "search_memories_vector", None)
        if not callable(search_memories_vector):
            outcome.skipped.append("store_lacks_vector_search")
            return outcome

        embeddable = [(row, memory_embedding_text(row)) for row in active_rows]
        embeddable = [(row, text) for row, text in embeddable if text]
        if not embeddable:
            outcome.skipped.append("no_embeddable_memory_text")
            return outcome
        texts = [text for _, text in embeddable]
        vectors: list[list[float]] = []
        try:
            for start in range(0, len(texts), MAX_EMBEDDINGS_BATCH_SIZE):
                vectors.extend(self.embedding_provider.embed_batch(texts[start : start + MAX_EMBEDDINGS_BATCH_SIZE]))
        except (VNextEmbeddingConfigurationError, VNextEmbeddingProviderError) as exc:
            outcome.skipped.append(f"embedding_provider_failed: {exc}")
            return outcome

        # The stores never expose raw embedding values; a single vector-search
        # probe is the read surface that tells us which rows have stored
        # embeddings (and how far the probe row's stored vector drifted from
        # its re-derived one).
        try:
            probe_rows = search_memories_vector(
                query_vector=vectors[0],
                domains=domains,
                sensitivity_allowed=sensitivity,
                limit=options.max_embedded_memories,
            )
        except Exception as exc:  # noqa: BLE001 - store backends raise driver-specific errors
            outcome.skipped.append(f"vector_search_failed: {exc}")
            return outcome
        embedded_ids = {str(row.get("id")) for row in probe_rows if row.get("id") is not None}
        probe_row_id = str(embeddable[0][0].get("id"))
        for row in probe_rows:
            if str(row.get("id")) == probe_row_id and isinstance(row.get("vector_distance"), (int, float)):
                outcome.probe_self_distance = float(row["vector_distance"])
                break
        members = [
            (row, vector)
            for (row, _), vector in zip(embeddable, vectors, strict=True)
            if str(row.get("id")) in embedded_ids
        ]
        outcome.embedded_count = len(members)
        if len(members) < options.min_cluster_size:
            outcome.skipped.append("fewer_embedded_memories_than_min_cluster_size")
            return outcome

        width = max(len(vector) for _, vector in members)
        matrix = np.zeros((len(members), width), dtype=np.float32)
        for index, (_, vector) in enumerate(members):
            matrix[index, : len(vector)] = np.asarray(vector, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0.0] = 1.0
        normalized = matrix / norms[:, None]
        similarities = normalized @ normalized.T

        union_find = _UnionFind(len(members))
        pair_rows, pair_cols = np.where(np.triu(similarities, k=1) >= options.similarity_threshold)
        for left, right in zip(pair_rows.tolist(), pair_cols.tolist(), strict=True):
            union_find.union(left, right)
        groups: dict[int, list[int]] = {}
        for index in range(len(members)):
            groups.setdefault(union_find.find(index), []).append(index)
        clusters = [indices for indices in groups.values() if len(indices) >= options.min_cluster_size]
        clusters.sort(key=lambda indices: (-len(indices), str(members[min(indices)][0].get("id"))))

        for indices in clusters:
            rows = sorted((members[index][0] for index in indices), key=lambda row: str(row.get("id")))
            pairwise = [
                float(similarities[i, j])
                for position, i in enumerate(indices)
                for j in indices[position + 1 :]
            ]
            digest = _digest_payload({"cluster_member_ids": [str(row.get("id")) for row in rows]})
            outcome.clusters.append(rows)
            outcome.similarity_stats[digest] = {
                "pair_count": len(pairwise),
                "min": round(min(pairwise), 4),
                "max": round(max(pairwise), 4),
                "mean": round(sum(pairwise) / len(pairwise), 4),
            }
        return outcome

    # -- proposals ---------------------------------------------------------------

    def _build_proposal(
        self,
        *,
        request: MemoryConsolidationRequest,
        members: list[JsonObject],
        cluster_digest: str,
        similarity_stats: JsonObject,
        route,
    ) -> JsonObject:
        member_ids = [str(row.get("id")) for row in members]
        survivor = max(members, key=lambda row: (len(str(row.get("canonical_text") or "")), str(row.get("id"))))
        proposal_kind = "dedup"
        title = f"Duplicate cluster: {_text(survivor)[:120]}"
        canonical_text = _text(survivor)
        model_provenance: JsonObject | None = None
        merge_refusal: str | None = None
        if request.generation_mode == "model_backed" and route is not None:
            merge = generate_consolidation_merge(
                ConsolidationMergeRequest(
                    cluster_members=tuple(members),
                    route=route,
                    temperature=request.model_temperature,
                    trace_id=request.trace_id,
                ),
                provider=self.merge_provider,
            )
            model_provenance = merge.model_provenance
            if merge.merged:
                proposal_kind = "merge"
                title = str(merge.title)
                canonical_text = str(merge.canonical_text)
            else:
                merge_refusal = merge.refusal_reason
        proposed_supersede = member_ids if proposal_kind == "merge" else [
            member_id for member_id in member_ids if member_id != str(survivor.get("id"))
        ]
        return {
            "proposal_kind": proposal_kind,
            "cluster_member_ids": member_ids,
            "consolidation_digest": cluster_digest,
            "similarity_stats": similarity_stats,
            "survivor_memory_id": str(survivor.get("id")) if proposal_kind == "dedup" else None,
            "proposed_supersede": proposed_supersede,
            "title": title,
            "canonical_text": canonical_text,
            "model_provenance": model_provenance,
            "merge_refusal": merge_refusal,
            "source_refs": _member_source_refs(members),
            "source_event_ids": _union_source_event_ids(members),
            "members": members,
        }

    def _create_proposal_candidate(
        self,
        *,
        request: MemoryConsolidationRequest,
        proposal: JsonObject,
    ) -> JsonObject:
        members: list[JsonObject] = proposal["members"]
        member_ids: list[str] = proposal["cluster_member_ids"]
        cluster_digest: str = proposal["consolidation_digest"]
        proposal_kind: str = proposal["proposal_kind"]
        memory_types = Counter(
            str(row.get("memory_type")) for row in members if isinstance(row.get("memory_type"), str)
        )
        memory_type = memory_types.most_common(1)[0][0] if memory_types else "semantic"
        reviewer_instructions = [
            f"Review candidate memory for cluster {cluster_digest}; accepting it is the promotion decision.",
            "After accepting, supersede the listed members through the existing memory review/undo flows "
            f"(members proposed for supersession: {', '.join(proposal['proposed_supersede']) or 'none'}).",
            "Consolidation never supersedes active memories automatically.",
        ]
        return self.store.create_memory(
            {
                "memory_key": f"vnext.consolidation.{cluster_digest}",
                "value": {
                    "kind": "memory_consolidation_proposal",
                    "proposal_kind": proposal_kind,
                    "consolidation_digest": cluster_digest,
                    "cluster_member_ids": member_ids,
                    "text": proposal["canonical_text"],
                },
                "status": "candidate",
                "memory_type": memory_type,
                "confidence": 0.6 if proposal_kind == "merge" else 0.75,
                "trust_class": "llm_single_source" if proposal_kind == "merge" else "deterministic",
                "promotion_eligibility": "promotable",
                "title": proposal["title"],
                "canonical_text": proposal["canonical_text"],
                "summary": (
                    f"{proposal_kind} proposal covering {len(member_ids)} near-duplicate memories "
                    f"(mean cosine {proposal['similarity_stats'].get('mean')})."
                ),
                "domain": _domain(request, members),
                "sensitivity": _highest_sensitivity(members),
                "source_event_ids": proposal["source_event_ids"],
                "metadata_json": {
                    "candidate_kind": "memory_consolidation",
                    "consolidation_digest": cluster_digest,
                    "source_refs": proposal["source_refs"],
                    "review_required": True,
                    "consolidation": {
                        "cluster_member_ids": member_ids,
                        "similarity_stats": proposal["similarity_stats"],
                        "proposal_kind": proposal_kind,
                        "model_provenance": proposal["model_provenance"],
                        "survivor_memory_id": proposal["survivor_memory_id"],
                        "proposed_supersede": proposal["proposed_supersede"],
                        "merge_refusal": proposal["merge_refusal"],
                        "reviewer_instructions": reviewer_instructions,
                    },
                },
            },
            actor_type=request.generated_by,
        )

    # -- reinforced preferences ----------------------------------------------------

    def _reinforced_preferences(self, clusters: list[list[JsonObject]]) -> list[JsonObject]:
        notes: list[JsonObject] = []
        for members in clusters:
            types = {str(row.get("memory_type") or "") for row in members}
            if not types or not types.issubset(PREFERENCE_MEMORY_TYPES):
                continue
            source_ids: set[str] = set()
            days: set[str] = set()
            for row in members:
                source_ids |= _member_source_ids(row)
                day = _member_day(row)
                if day is not None:
                    days.add(day)
            if (
                len(source_ids) < REINFORCED_PREFERENCE_MIN_DISTINCT
                and len(days) < REINFORCED_PREFERENCE_MIN_DISTINCT
            ):
                continue
            member_ids = [str(row.get("id")) for row in members]
            notes.append(
                {
                    "cluster_member_ids": member_ids,
                    "consolidation_digest": _digest_payload({"cluster_member_ids": sorted(member_ids)}),
                    "distinct_source_count": len(source_ids),
                    "distinct_day_count": len(days),
                    "memory_types": sorted(types),
                    "suggestion": (
                        "Repeated preference observed across independent sources/days; "
                        "consider promotion or a confidence bump after human review."
                    ),
                }
            )
        return notes

    # -- report ---------------------------------------------------------------

    def generate_memory_consolidation(self, request: MemoryConsolidationRequest | None = None) -> JsonObject:
        request = request or MemoryConsolidationRequest()
        _validate_request(request)
        options = _clustering_options(request)
        domains = _allowed_domains(request)
        sensitivity = _allowed_sensitivity(request)

        events = self.store.list_events(limit=request.event_limit)
        ratings: list[JsonObject] = []
        list_ratings = getattr(self.store, "list_artifact_quality_ratings", None)
        if callable(list_ratings):
            ratings = list_ratings(limit=request.rating_limit)
        artifacts: list[JsonObject] = []
        list_artifacts = getattr(self.store, "list_artifacts", None)
        if callable(list_artifacts):
            artifacts = [
                row
                for row in list_artifacts(
                    domains=domains, sensitivity_allowed=sensitivity, limit=request.artifact_limit
                )
                if row.get("artifact_type") != "memory_consolidation"
            ]

        route = None
        if request.generation_mode == "model_backed":
            route = resolve_model_route(
                ModelRoutingRequest(
                    workflow_type="memory_consolidation",
                    generation_mode="model_backed",
                    domains=request.domains,
                    sensitivity_allowed=request.sensitivity_allowed,
                    agent_identity=request.agent_identity,
                    brain_charter=self._brain_charter(),
                    requested_route_mode=request.model_route_mode,
                    requested_provider=request.model_provider,
                    requested_model=request.model,
                    allow_cloud_private=request.allow_cloud_private,
                )
            )
            if route.approval_required or route.route_mode == "model_disabled":
                # Fail before any candidate writes, preserving the previous
                # behavior where build_model_backed_artifact raised first.
                raise VNextModelIntelligenceError("model-backed generation is not allowed by routing policy")

        clustering = self._cluster_memories(domains=domains, sensitivity=sensitivity, options=options)
        existing_candidates = _existing_cluster_candidates(self.store)

        proposals: list[JsonObject] = []
        skipped: list[str] = list(clustering.skipped)
        candidate_ids: list[str] = []
        clusters_for_proposals = clustering.clusters[: options.max_clusters]
        if len(clustering.clusters) > options.max_clusters:
            skipped.append(
                f"cluster_bound: {len(clustering.clusters) - options.max_clusters} clusters beyond "
                f"max_clusters={options.max_clusters} were not proposed this run"
            )
        for members in clusters_for_proposals:
            member_ids = [str(row.get("id")) for row in members]
            cluster_digest = _digest_payload({"cluster_member_ids": member_ids})
            similarity_stats = clustering.similarity_stats.get(cluster_digest, {})
            proposal = self._build_proposal(
                request=request,
                members=members,
                cluster_digest=cluster_digest,
                similarity_stats=similarity_stats,
                route=route,
            )
            existing_id = existing_candidates.get(cluster_digest)
            if existing_id is not None:
                proposal["candidate_memory_id"] = existing_id
                proposal["candidate_state"] = "existing"
                candidate_ids.append(existing_id)
            elif request.create_candidate_memories:
                candidate = self._create_proposal_candidate(request=request, proposal=proposal)
                proposal["candidate_memory_id"] = str(candidate["id"])
                proposal["candidate_state"] = "created"
                candidate_ids.append(str(candidate["id"]))
            else:
                proposal["candidate_memory_id"] = None
                proposal["candidate_state"] = "not_created (create_candidate_memories=false)"
            proposals.append(proposal)

        reinforced = self._reinforced_preferences(clustering.clusters)

        cluster_membership = [
            sorted(str(row.get("id")) for row in members) for members in clustering.clusters
        ]
        run_digest = _digest_payload(
            {
                "cluster_membership": cluster_membership,
                "similarity_threshold": options.similarity_threshold,
                "min_cluster_size": options.min_cluster_size,
                "embedded_count": clustering.embedded_count,
            }
        )

        content = self._render_markdown(
            request=request,
            options=options,
            clustering=clustering,
            proposals=proposals,
            reinforced=reinforced,
            skipped=skipped,
            events_count=len(events),
            artifacts_count=len(artifacts),
            ratings_count=len(ratings),
        )

        proposal_records = [
            {
                key: proposal[key]
                for key in (
                    "proposal_kind",
                    "cluster_member_ids",
                    "consolidation_digest",
                    "similarity_stats",
                    "survivor_memory_id",
                    "proposed_supersede",
                    "model_provenance",
                    "merge_refusal",
                    "candidate_memory_id",
                    "candidate_state",
                    "source_refs",
                )
            }
            for proposal in proposals
        ]
        report_source_refs = list(
            dict.fromkeys(ref for proposal in proposal_records for ref in proposal["source_refs"])
        )
        metadata = {
            **request.metadata_json,
            "workflow": "memory_consolidation",
            "workflow_type": "memory_consolidation",
            "trace_id": request.trace_id,
            "scheduler_run_id": request.run_id,
            "review_status": "needs_review",
            "generation_mode": request.generation_mode,
            "source_refs": report_source_refs,
            "consolidation_digest": run_digest,
            "candidate_memory_ids": candidate_ids,
            "consolidation": {
                "embedding_access": "provider_reembed_plus_vector_search_probe",
                "similarity_threshold": options.similarity_threshold,
                "min_cluster_size": options.min_cluster_size,
                "max_embedded_memories": options.max_embedded_memories,
                "bounded": clustering.bounded,
                "probe_self_distance": clustering.probe_self_distance,
                "cluster_membership": cluster_membership,
                "proposals": proposal_records,
                "reinforced_preferences": reinforced,
                "skipped": skipped,
            },
            "input_counts": {
                "active_memories": clustering.active_count,
                "embedded_memories": clustering.embedded_count,
                "clusters": len(clustering.clusters),
                "proposals": len(proposals),
                "reinforced_preferences": len(reinforced),
                "artifacts": len(artifacts),
                "events": len(events),
                "ratings": len(ratings),
            },
            "policy_decision": request.policy_decision,
            "agent_identity": request.agent_identity,
        }

        prompt_hash: str | None = None
        model_info_json: JsonObject | None = None
        if request.generation_mode == "model_backed" and route is not None:
            context_rows = tuple(row for members in clusters_for_proposals for row in members)[:10]
            model_artifact = build_model_backed_artifact(
                ModelBackedRequest(
                    workflow_type="memory_consolidation",
                    title=self._title(request),
                    deterministic_markdown=content,
                    context_rows=context_rows,
                    source_refs=tuple(report_source_refs),
                    open_questions=("Which consolidation proposal should be promoted, edited, or rejected?",),
                    trace_id=request.trace_id,
                    route=route,
                    temperature=request.model_temperature,
                    config={"generated_by": request.generated_by},
                )
            )
            content = model_artifact.content_markdown
            prompt_hash = model_artifact.prompt_hash
            model_info_json = model_artifact.model_info
            metadata = {**metadata, **model_artifact.metadata}

        all_cluster_rows = [row for members in clustering.clusters for row in members]
        artifact = self.store.create_artifact(
            {
                "artifact_type": "memory_consolidation",
                "title": self._title(request),
                "content_markdown": content,
                "status": "needs_review",
                "domain": _domain(request, all_cluster_rows),
                "sensitivity": _highest_sensitivity(all_cluster_rows),
                "generated_by": request.generated_by,
                "prompt_hash": prompt_hash,
                "model_info_json": model_info_json,
                "metadata_json": metadata,
            },
            actor_type=request.generated_by,
        )
        append_event(
            self.store,
            event_type="memory.consolidation.generated",
            actor_type=request.generated_by,
            target_type="artifact",
            target_id=str(artifact["id"]),
            trace_id=request.trace_id,
            run_id=request.run_id,
            payload={
                "consolidation_digest": run_digest,
                "candidate_memory_ids": candidate_ids,
                "input_counts": metadata["input_counts"],
                "skipped": skipped,
            },
        )
        return artifact

    def _title(self, request: MemoryConsolidationRequest) -> str:
        return f"Memory Consolidation - {request.generated_for or datetime.now(UTC).date().isoformat()}"

    def _render_markdown(
        self,
        *,
        request: MemoryConsolidationRequest,
        options: _ClusteringOptions,
        clustering: _ClusteringOutcome,
        proposals: list[JsonObject],
        reinforced: list[JsonObject],
        skipped: list[str],
        events_count: int,
        artifacts_count: int,
        ratings_count: int,
    ) -> str:
        cluster_lines: list[str] = []
        for members in clustering.clusters:
            member_ids = [str(row.get("id")) for row in members]
            digest = _digest_payload({"cluster_member_ids": member_ids})
            stats = clustering.similarity_stats.get(digest, {})
            cluster_lines.append(
                f"- Cluster `{digest}` ({len(members)} members, mean cosine {stats.get('mean')}): "
                + "; ".join(f"{_text(row)[:80]} [memory:{row.get('id')}]" for row in members)
            )
        if not cluster_lines:
            cluster_lines = ["- No near-duplicate clusters were found in scope."]

        proposal_lines: list[str] = []
        for proposal in proposals:
            proposal_lines.append(
                f"- `{proposal['consolidation_digest']}` {proposal['proposal_kind']} proposal "
                f"({proposal['candidate_state']}, candidate: {proposal['candidate_memory_id']}) - "
                f"members: {', '.join(proposal['cluster_member_ids'])}; "
                f"proposed supersede after acceptance: {', '.join(proposal['proposed_supersede']) or 'none'}"
                + (f"; merge refused: {proposal['merge_refusal']}" if proposal.get("merge_refusal") else "")
            )
        if not proposal_lines:
            proposal_lines = ["- No merge or dedup proposals were created this run."]

        reinforced_lines = [
            f"- Cluster `{note['consolidation_digest']}` is a reinforced preference: "
            f"{note['distinct_source_count']} distinct sources, {note['distinct_day_count']} distinct days. "
            f"{note['suggestion']}"
            for note in reinforced
        ] or ["- No reinforced preferences were detected."]

        skipped_lines = [f"- {reason}" for reason in skipped]
        if clustering.bounded:
            skipped_lines.append(
                f"- Clustering was bounded to the {options.max_embedded_memories} most recently updated "
                f"memories of {clustering.active_count} in scope."
            )
        if clustering.probe_self_distance is not None and clustering.probe_self_distance > (
            1.0 - options.similarity_threshold
        ):
            skipped_lines.append(
                f"- Warning: stored embeddings may be stale (probe self-distance "
                f"{clustering.probe_self_distance:.4f}); rerun the embeddings backfill."
            )
        if not skipped_lines:
            skipped_lines = ["- Nothing was skipped; no bounds were hit."]

        return "\n".join(
            [
                f"# {self._title(request)}",
                "",
                "## Consolidation Summary",
                f"- Active memories in scope: {clustering.active_count}",
                f"- Memories with stored embeddings considered: {clustering.embedded_count}",
                f"- Similarity threshold: {options.similarity_threshold} (min cluster size {options.min_cluster_size})",
                f"- Clusters found: {len(clustering.clusters)}",
                f"- Proposals: {len(proposals)}",
                f"- Reinforced preferences: {len(reinforced)}",
                f"- Context scanned: {artifacts_count} artifacts, {events_count} events, {ratings_count} ratings",
                "",
                "## Near-Duplicate Clusters",
                *cluster_lines,
                "",
                "## Merge / Dedup Proposals",
                *proposal_lines,
                "",
                "## Reinforced Preferences",
                *reinforced_lines,
                "",
                "## Skipped / Bounds",
                *skipped_lines,
                "",
                "## Review Policy",
                "- This artifact is review-only.",
                "- Proposals are candidate memories; accepting a candidate is the promotion decision.",
                "- Members marked `proposed_supersede` are only superseded when a reviewer does so through",
                "  the existing memory review/undo flows; consolidation never supersedes automatically.",
            ]
        )

    def _brain_charter(self) -> JsonObject | None:
        getter = getattr(self.store, "get_brain_charter", None)
        if not callable(getter):
            return None
        charter = getter()
        return charter if isinstance(charter, dict) else None


__all__ = [
    "DEFAULT_SIMILARITY_THRESHOLD",
    "MAX_EMBEDDED_MEMORIES_HARD_CAP",
    "MemoryConsolidationRequest",
    "VNextConsolidationService",
    "VNextConsolidationStore",
    "VNextConsolidationValidationError",
]
