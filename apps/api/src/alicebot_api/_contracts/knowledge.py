from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sys as _sys
from typing import TypedDict
from uuid import UUID

from alicebot_api._contracts.common import (
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
    EntityType,
    MemoryPromotionEligibility,
    isoformat_or_none,
)
from alicebot_api._contracts.runtime import ContextPackEntityEdge
from alicebot_api.store import JsonObject, JsonValue


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


@dataclass(frozen=True, slots=True)
class EntityCreateInput:
    entity_type: EntityType
    name: str
    source_memory_ids: tuple[UUID, ...]

    def as_payload(self) -> JsonObject:
        return {
            "entity_type": self.entity_type,
            "name": self.name,
            "source_memory_ids": [str(source_memory_id) for source_memory_id in self.source_memory_ids],
        }


@dataclass(frozen=True, slots=True)
class EntityEdgeCreateInput:
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    valid_from: datetime | None
    valid_to: datetime | None
    source_memory_ids: tuple[UUID, ...]

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "from_entity_id": str(self.from_entity_id),
            "to_entity_id": str(self.to_entity_id),
            "relationship_type": self.relationship_type,
            "source_memory_ids": [str(source_memory_id) for source_memory_id in self.source_memory_ids],
        }
        payload["valid_from"] = isoformat_or_none(self.valid_from)
        payload["valid_to"] = isoformat_or_none(self.valid_to)
        return payload


@dataclass(frozen=True, slots=True)
class TemporalStateAtQueryInput:
    entity_id: UUID
    at: datetime | None = None

    def as_payload(self) -> JsonObject:
        return {
            "entity_id": str(self.entity_id),
            "at": isoformat_or_none(self.at),
        }


@dataclass(frozen=True, slots=True)
class TemporalTimelineQueryInput:
    entity_id: UUID
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_TEMPORAL_TIMELINE_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "entity_id": str(self.entity_id),
            "since": isoformat_or_none(self.since),
            "until": isoformat_or_none(self.until),
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class TemporalExplainQueryInput:
    entity_id: UUID
    at: datetime | None = None

    def as_payload(self) -> JsonObject:
        return {
            "entity_id": str(self.entity_id),
            "at": isoformat_or_none(self.at),
        }


@dataclass(frozen=True, slots=True)
class TrustedFactPatternListQueryInput:
    limit: int = DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class TrustedFactPlaybookListQueryInput:
    limit: int = DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
        }


class EntityRecord(TypedDict):
    id: str
    entity_type: EntityType
    name: str
    source_memory_ids: list[str]
    created_at: str


class EntityCreateResponse(TypedDict):
    entity: EntityRecord


class EntityListSummary(TypedDict):
    total_count: int
    order: list[str]


class EntityListResponse(TypedDict):
    items: list[EntityRecord]
    summary: EntityListSummary


class EntityDetailResponse(TypedDict):
    entity: EntityRecord


class EntityEdgeRecord(ContextPackEntityEdge):
    pass


class EntityEdgeCreateResponse(TypedDict):
    edge: EntityEdgeRecord


class EntityEdgeListSummary(TypedDict):
    entity_id: str
    total_count: int
    order: list[str]


class EntityEdgeListResponse(TypedDict):
    items: list[EntityEdgeRecord]
    summary: EntityEdgeListSummary


class TemporalValidityRecord(TypedDict):
    valid_from: str | None
    valid_to: str | None
    effective_at: bool


class TemporalStateFactRecord(TypedDict):
    memory_id: str
    memory_key: str
    value: JsonValue | None
    status: str
    validity: TemporalValidityRecord
    created_at: str


class TemporalStateEdgeRecord(TypedDict):
    id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    validity: TemporalValidityRecord
    source_memory_ids: list[str]
    created_at: str


class TemporalStateSummary(TypedDict):
    entity_id: str
    entity_name: str
    entity_type: EntityType
    as_of: str
    fact_count: int
    edge_count: int


class TemporalStateAtRecord(TypedDict):
    entity: EntityRecord
    facts: list[TemporalStateFactRecord]
    edges: list[TemporalStateEdgeRecord]
    summary: TemporalStateSummary


class TemporalStateAtResponse(TypedDict):
    state_at: TemporalStateAtRecord


class TemporalTimelineEventRecord(TypedDict):
    id: str
    event_type: str
    object_kind: str
    object_id: str
    occurred_at: str
    summary: str
    payload: JsonObject


class TemporalTimelineSummary(TypedDict):
    entity_id: str
    entity_name: str
    entity_type: EntityType
    since: str | None
    until: str | None
    returned_count: int
    total_count: int
    limit: int
    order: list[str]


class TemporalTimelineRecord(TypedDict):
    entity: EntityRecord
    events: list[TemporalTimelineEventRecord]
    summary: TemporalTimelineSummary


class TemporalTimelineResponse(TypedDict):
    timeline: TemporalTimelineRecord


class TemporalTrustRecord(TypedDict):
    trust_class: str | None
    trust_reason: str | None
    confirmation_status: str | None
    confidence: float | None


class TemporalProvenanceRecord(TypedDict):
    source_memory_ids: list[str]
    source_event_ids: list[str]
    revision_sequence_no: int | None
    revision_action: str | None
    revision_created_at: str | None


class TemporalFactSupersessionRecord(TypedDict):
    revision_id: str
    sequence_no: int
    action: str
    created_at: str
    value: JsonValue | None
    status: str
    validity: TemporalValidityRecord
    source_event_ids: list[str]
    effective_at_as_of: bool


class TemporalFactExplainRecord(TemporalStateFactRecord):
    trust: TemporalTrustRecord
    provenance: TemporalProvenanceRecord
    supersession_chain: list[TemporalFactSupersessionRecord]


class TemporalEdgeSupersessionRecord(TypedDict):
    id: str
    created_at: str
    validity: TemporalValidityRecord
    source_memory_ids: list[str]
    effective_at_as_of: bool


class TemporalEdgeExplainRecord(TemporalStateEdgeRecord):
    trust: TemporalTrustRecord
    provenance: TemporalProvenanceRecord
    supersession_chain: list[TemporalEdgeSupersessionRecord]


class TemporalExplainSummary(TypedDict):
    entity_id: str
    entity_name: str
    entity_type: EntityType
    as_of: str
    fact_count: int
    edge_count: int


class TemporalExplainRecord(TypedDict):
    entity: EntityRecord
    facts: list[TemporalFactExplainRecord]
    edges: list[TemporalEdgeExplainRecord]
    summary: TemporalExplainSummary


class TemporalExplainResponse(TypedDict):
    explain: TemporalExplainRecord


class TrustedFactEvidenceLinkRecord(TypedDict):
    fact_id: str
    memory_key: str
    memory_type: str
    value: JsonValue
    trust: TemporalTrustRecord
    promotion_eligibility: MemoryPromotionEligibility
    evidence_count: int | None
    independent_source_count: int | None
    extracted_by_model: str | None
    source_event_ids: list[str]
    revision_sequence_no: int | None
    revision_action: str | None
    revision_created_at: str | None


class TrustedFactPatternRecord(TypedDict):
    id: str
    pattern_key: str
    title: str
    memory_type: str
    namespace_key: str
    fact_count: int
    source_fact_ids: list[str]
    evidence_chain: list[TrustedFactEvidenceLinkRecord]
    explanation: str
    created_at: str
    updated_at: str


class TrustedFactPatternListSummary(TypedDict):
    returned_count: int
    total_count: int
    limit: int
    order: list[str]


class TrustedFactPatternListResponse(TypedDict):
    items: list[TrustedFactPatternRecord]
    summary: TrustedFactPatternListSummary


class TrustedFactPatternExplainResponse(TypedDict):
    pattern: TrustedFactPatternRecord


class TrustedFactPlaybookStepRecord(TypedDict):
    step_no: int
    fact_id: str
    memory_key: str
    action_type: str
    instruction: str
    value: JsonValue
    trust: TemporalTrustRecord


class TrustedFactPlaybookRecord(TypedDict):
    id: str
    playbook_key: str
    pattern_id: str
    pattern_key: str
    title: str
    memory_type: str
    source_fact_ids: list[str]
    source_pattern_ids: list[str]
    steps: list[TrustedFactPlaybookStepRecord]
    explanation: str
    created_at: str
    updated_at: str


class TrustedFactPlaybookListSummary(TypedDict):
    returned_count: int
    total_count: int
    limit: int
    order: list[str]


class TrustedFactPlaybookListResponse(TypedDict):
    items: list[TrustedFactPlaybookRecord]
    summary: TrustedFactPlaybookListSummary


class TrustedFactPlaybookExplainResponse(TypedDict):
    playbook: TrustedFactPlaybookRecord

__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
