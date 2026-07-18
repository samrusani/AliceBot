from __future__ import annotations

from dataclasses import dataclass
import sys as _sys
from typing import TYPE_CHECKING as _TYPE_CHECKING, Literal, NotRequired, TypedDict
from uuid import UUID

from alicebot_api._contracts.common import (
    DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    EmbeddingConfigStatus,
    MemoryConfirmationStatus,
    MemoryPromotionEligibility,
    MemoryTrustClass,
    MemoryType,
    RetrievalEvaluationStatus,
)
from alicebot_api.store import JsonObject, JsonValue

if _TYPE_CHECKING:
    from alicebot_api.contracts import (
        ContinuityRecallOrderingMetadata,
        ContinuityRetrievalDebugCandidateRecord,
    )


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


@dataclass(frozen=True, slots=True)
class EmbeddingConfigCreateInput:
    provider: str
    model: str
    version: str
    dimensions: int
    status: EmbeddingConfigStatus
    metadata: JsonObject

    def as_payload(self) -> JsonObject:
        return {
            "provider": self.provider,
            "model": self.model,
            "version": self.version,
            "dimensions": self.dimensions,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class MemoryEmbeddingUpsertInput:
    memory_id: UUID
    embedding_config_id: UUID
    vector: tuple[float, ...]

    def as_payload(self) -> JsonObject:
        return {
            "memory_id": str(self.memory_id),
            "embedding_config_id": str(self.embedding_config_id),
            "vector": [float(value) for value in self.vector],
        }


@dataclass(frozen=True, slots=True)
class SemanticMemoryRetrievalRequestInput:
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


class RetrievalRunRecord(TypedDict):
    id: str
    source_surface: str
    ranking_strategy: str
    query_text: str | None
    request_scope: JsonObject
    result_ids: list[str]
    exclusion_summary: JsonObject
    candidate_count: int
    selected_count: int
    debug_enabled: bool
    retention_until: str
    created_at: str


class RetrievalRunListSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class RetrievalRunListResponse(TypedDict):
    items: list[RetrievalRunRecord]
    summary: RetrievalRunListSummary


class RetrievalTraceSummary(TypedDict):
    candidate_count: int
    selected_count: int
    order: list[str]


class RetrievalTraceResponse(TypedDict):
    retrieval_run: RetrievalRunRecord
    candidates: list[ContinuityRetrievalDebugCandidateRecord]
    summary: RetrievalTraceSummary


class EmbeddingConfigRecord(TypedDict):
    id: str
    provider: str
    model: str
    version: str
    dimensions: int
    status: EmbeddingConfigStatus
    metadata: JsonObject
    created_at: str


class EmbeddingConfigCreateResponse(TypedDict):
    embedding_config: EmbeddingConfigRecord


class EmbeddingConfigListSummary(TypedDict):
    total_count: int
    order: list[str]


class EmbeddingConfigListResponse(TypedDict):
    items: list[EmbeddingConfigRecord]
    summary: EmbeddingConfigListSummary


class MemoryEmbeddingRecord(TypedDict):
    id: str
    memory_id: str
    embedding_config_id: str
    dimensions: int
    vector: list[float]
    created_at: str
    updated_at: str


class MemoryEmbeddingUpsertResponse(TypedDict):
    embedding: MemoryEmbeddingRecord
    write_mode: Literal["created", "updated"]


class MemoryEmbeddingDetailResponse(TypedDict):
    embedding: MemoryEmbeddingRecord


class MemoryEmbeddingListSummary(TypedDict):
    memory_id: str
    total_count: int
    order: list[str]


class MemoryEmbeddingListResponse(TypedDict):
    items: list[MemoryEmbeddingRecord]
    summary: MemoryEmbeddingListSummary


class SemanticMemoryRetrievalResultItem(TypedDict):
    memory_id: str
    memory_key: str
    value: JsonValue
    source_event_ids: list[str]
    memory_type: NotRequired[MemoryType]
    confidence: NotRequired[float | None]
    salience: NotRequired[float | None]
    confirmation_status: NotRequired[MemoryConfirmationStatus]
    trust_class: NotRequired[MemoryTrustClass]
    promotion_eligibility: NotRequired[MemoryPromotionEligibility]
    evidence_count: NotRequired[int | None]
    independent_source_count: NotRequired[int | None]
    extracted_by_model: NotRequired[str | None]
    trust_reason: NotRequired[str | None]
    valid_from: NotRequired[str | None]
    valid_to: NotRequired[str | None]
    last_confirmed_at: NotRequired[str | None]
    created_at: str
    updated_at: str
    score: float


class SemanticMemoryRetrievalSummary(TypedDict):
    embedding_config_id: str
    limit: int
    returned_count: int
    similarity_metric: Literal["cosine_similarity"]
    order: list[str]


class SemanticMemoryRetrievalResponse(TypedDict):
    items: list[SemanticMemoryRetrievalResultItem]
    summary: SemanticMemoryRetrievalSummary


class RetrievalEvaluationFixtureResult(TypedDict):
    fixture_id: str
    title: str
    query: str
    top_k: int
    expected_relevant_ids: list[str]
    baseline_returned_ids: list[str]
    returned_ids: list[str]
    hit_count: int
    baseline_hit_count: int
    baseline_precision_at_k: float
    precision_at_k: float
    precision_lift_at_k: float
    baseline_top_result_id: str | None
    top_result_id: str | None
    baseline_top_result_ordering: ContinuityRecallOrderingMetadata | None
    top_result_ordering: ContinuityRecallOrderingMetadata | None


class RetrievalEvaluationSummary(TypedDict):
    fixture_count: int
    evaluated_fixture_count: int
    passing_fixture_count: int
    baseline_passing_fixture_count: int
    baseline_precision_at_k_mean: float
    precision_at_k_mean: float
    precision_at_k_lift: float
    baseline_precision_at_1_mean: float
    precision_at_1_mean: float
    precision_target: float
    status: RetrievalEvaluationStatus
    fixture_order: list[str]
    result_order: list[str]


class RetrievalEvaluationResponse(TypedDict):
    fixtures: list[RetrievalEvaluationFixtureResult]
    summary: RetrievalEvaluationSummary


class PublicEvalSuiteDefinitionRecord(TypedDict):
    suite_key: str
    title: str
    description: str
    evaluator_kind: str
    case_count: int
    fixture_schema_version: str
    fixture_source_path: str
    case_keys: list[str]


class PublicEvalSuiteDefinitionListResponse(TypedDict):
    items: list[PublicEvalSuiteDefinitionRecord]
    summary: JsonObject


class PublicEvalRunRecord(TypedDict):
    id: str
    status: str
    report_digest: str
    summary: JsonObject
    created_at: str


class PublicEvalResultRecord(TypedDict):
    id: str
    suite_key: str
    case_key: str
    status: str
    score: float
    summary: JsonObject
    details: JsonObject
    created_at: str


class PublicEvalRunListResponse(TypedDict):
    items: list[PublicEvalRunRecord]
    summary: JsonObject


class PublicEvalRunDetailResponse(TypedDict):
    run: PublicEvalRunRecord
    report: JsonObject
    results: list[PublicEvalResultRecord]

__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
