from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import sys as _sys
from typing import TYPE_CHECKING as _TYPE_CHECKING, Literal, NotRequired, TypedDict
from uuid import UUID

from alicebot_api._contracts.common import (
    AdmissionAction,
    ContinuityBriefType,
    ContinuityCaptureAdmissionPosture,
    ContinuityCaptureCandidateType,
    ContinuityCaptureCommitDecision,
    ContinuityCaptureCommitMode,
    ContinuityCaptureExplicitSignal,
    ContinuityCaptureProposedAction,
    ContinuityCorrectionAction,
    ContinuityObjectType,
    ContinuityOpenLoopPosture,
    ContinuityOpenLoopReviewAction,
    ContinuityPreservationStatus,
    ContinuityPromotionStatus,
    ContinuityRecallFreshnessPosture,
    ContinuityRecallProvenancePosture,
    ContinuityRecallScopeKind,
    ContinuityRecallSupersessionPosture,
    ContinuityReviewStatusFilter,
    ContinuitySearchabilityStatus,
    ContradictionKind,
    ContradictionResolutionAction,
    ContradictionStatus,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_CAPTURE_LIMIT,
    DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    ExplicitCommitmentOpenLoopDecision,
    ExplicitCommitmentPattern,
    ExplicitPreferencePattern,
    MemoryConfirmationStatus,
    MemoryOperationPolicyAction,
    MemoryOperationStatus,
    MemoryOperationType,
    MemoryPromotionEligibility,
    MemoryQualityGateStatus,
    MemoryQualityReviewAction,
    MemoryReviewLabelValue,
    MemoryReviewQueuePriorityMode,
    MemoryReviewStatusFilter,
    MemoryStatus,
    MemoryTrustClass,
    MemoryType,
    OpenLoopStatus,
    OpenLoopStatusFilter,
    RecommendationConfidencePosture,
    TaskBriefMode,
    TaskBriefingStrategy,
    TrustSignalDirection,
    TrustSignalState,
    TrustSignalType,
    isoformat_or_none,
)
from alicebot_api.store import JsonObject, JsonValue

if _TYPE_CHECKING:
    from alicebot_api.contracts import (
        ResumptionBriefSectionSummary,
        RetrievalEvaluationSummary,
    )


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


@dataclass(frozen=True, slots=True)
class OpenLoopCandidateInput:
    title: str
    due_at: datetime | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "title": self.title,
        }
        payload["due_at"] = isoformat_or_none(self.due_at)
        return payload


@dataclass(frozen=True, slots=True)
class MemoryCandidateInput:
    memory_key: str
    value: JsonValue | None
    source_event_ids: tuple[UUID, ...]
    agent_profile_id: str | None = None
    delete_requested: bool = False
    memory_type: str | None = None
    confidence: float | None = None
    salience: float | None = None
    confirmation_status: str | None = None
    trust_class: str | None = None
    promotion_eligibility: str | None = None
    evidence_count: int | None = None
    independent_source_count: int | None = None
    extracted_by_model: str | None = None
    trust_reason: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    last_confirmed_at: datetime | None = None
    open_loop: OpenLoopCandidateInput | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "memory_key": self.memory_key,
            "source_event_ids": [str(source_event_id) for source_event_id in self.source_event_ids],
            "delete_requested": self.delete_requested,
        }
        if self.agent_profile_id is not None:
            payload["agent_profile_id"] = self.agent_profile_id
        payload["value"] = self.value
        if self.memory_type is not None:
            payload["memory_type"] = self.memory_type
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.salience is not None:
            payload["salience"] = self.salience
        if self.confirmation_status is not None:
            payload["confirmation_status"] = self.confirmation_status
        if self.trust_class is not None:
            payload["trust_class"] = self.trust_class
        if self.promotion_eligibility is not None:
            payload["promotion_eligibility"] = self.promotion_eligibility
        if self.evidence_count is not None:
            payload["evidence_count"] = self.evidence_count
        if self.independent_source_count is not None:
            payload["independent_source_count"] = self.independent_source_count
        if self.extracted_by_model is not None:
            payload["extracted_by_model"] = self.extracted_by_model
        if self.trust_reason is not None:
            payload["trust_reason"] = self.trust_reason
        if self.valid_from is not None:
            payload["valid_from"] = isoformat_or_none(self.valid_from)
        if self.valid_to is not None:
            payload["valid_to"] = isoformat_or_none(self.valid_to)
        if self.last_confirmed_at is not None:
            payload["last_confirmed_at"] = isoformat_or_none(self.last_confirmed_at)
        if self.open_loop is not None:
            payload["open_loop"] = self.open_loop.as_payload()
        return payload


@dataclass(frozen=True, slots=True)
class ExplicitPreferenceExtractionRequestInput:
    source_event_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "source_event_id": str(self.source_event_id),
        }


@dataclass(frozen=True, slots=True)
class ExplicitCommitmentExtractionRequestInput:
    source_event_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "source_event_id": str(self.source_event_id),
        }


@dataclass(frozen=True, slots=True)
class ExplicitSignalCaptureRequestInput:
    source_event_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "source_event_id": str(self.source_event_id),
        }


@dataclass(frozen=True, slots=True)
class ContinuityCaptureCreateInput:
    raw_content: str
    explicit_signal: ContinuityCaptureExplicitSignal | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "raw_content": self.raw_content,
        }
        payload["explicit_signal"] = self.explicit_signal
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityCaptureCandidatesInput:
    user_content: str
    assistant_content: str
    session_id: str | None = None
    source_kind: str = "sync_turn"

    def as_payload(self) -> JsonObject:
        return {
            "user_content": self.user_content,
            "assistant_content": self.assistant_content,
            "session_id": self.session_id,
            "source_kind": self.source_kind,
        }


@dataclass(frozen=True, slots=True)
class ContinuityCaptureCommitInput:
    mode: ContinuityCaptureCommitMode = "assist"
    candidates: list[JsonObject] = field(default_factory=list)
    sync_fingerprint: str | None = None
    source_kind: str = "sync_turn"

    def as_payload(self) -> JsonObject:
        return {
            "mode": self.mode,
            "candidates": [dict(candidate) for candidate in self.candidates],
            "sync_fingerprint": self.sync_fingerprint,
            "source_kind": self.source_kind,
        }


@dataclass(frozen=True, slots=True)
class MemoryOperationGenerateInput:
    user_content: str
    assistant_content: str
    mode: ContinuityCaptureCommitMode = "assist"
    sync_fingerprint: str | None = None
    source_kind: str = "sync_turn"
    session_id: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    target_continuity_object_id: UUID | None = None

    def as_payload(self) -> JsonObject:
        return {
            "user_content": self.user_content,
            "assistant_content": self.assistant_content,
            "mode": self.mode,
            "sync_fingerprint": self.sync_fingerprint,
            "source_kind": self.source_kind,
            "session_id": self.session_id,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "target_continuity_object_id": (
                None if self.target_continuity_object_id is None else str(self.target_continuity_object_id)
            ),
        }


@dataclass(frozen=True, slots=True)
class MemoryOperationCommitInput:
    candidate_ids: list[UUID] = field(default_factory=list)
    sync_fingerprint: str | None = None
    include_review_required: bool = False

    def as_payload(self) -> JsonObject:
        return {
            "candidate_ids": [str(candidate_id) for candidate_id in self.candidate_ids],
            "sync_fingerprint": self.sync_fingerprint,
            "include_review_required": self.include_review_required,
        }


@dataclass(frozen=True, slots=True)
class MemoryOperationListInput:
    limit: int = DEFAULT_CONTINUITY_CAPTURE_LIMIT
    policy_action: MemoryOperationPolicyAction | None = None
    operation_type: MemoryOperationType | None = None
    sync_fingerprint: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
            "policy_action": self.policy_action,
            "operation_type": self.operation_type,
            "sync_fingerprint": self.sync_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ContinuityReviewQueueQueryInput:
    status: ContinuityReviewStatusFilter = "correction_ready"
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "status": self.status,
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ContinuityCorrectionInput:
    action: ContinuityCorrectionAction
    reason: str | None = None
    title: str | None = None
    body: JsonObject | None = None
    provenance: JsonObject | None = None
    confidence: float | None = None
    replacement_title: str | None = None
    replacement_body: JsonObject | None = None
    replacement_provenance: JsonObject | None = None
    replacement_confidence: float | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "action": self.action,
            "reason": self.reason,
            "title": self.title,
            "body": self.body,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "replacement_title": self.replacement_title,
            "replacement_body": self.replacement_body,
            "replacement_provenance": self.replacement_provenance,
            "replacement_confidence": self.replacement_confidence,
        }
        return payload


@dataclass(frozen=True, slots=True)
class ContradictionCaseListQueryInput:
    status: ContradictionStatus = "open"
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT
    continuity_object_id: UUID | None = None

    def as_payload(self) -> JsonObject:
        return {
            "status": self.status,
            "limit": self.limit,
            "continuity_object_id": (
                None if self.continuity_object_id is None else str(self.continuity_object_id)
            ),
        }


@dataclass(frozen=True, slots=True)
class ContradictionSyncInput:
    continuity_object_id: UUID | None = None
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "continuity_object_id": (
                None if self.continuity_object_id is None else str(self.continuity_object_id)
            ),
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ContradictionResolveInput:
    action: ContradictionResolutionAction
    note: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "action": self.action,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class TrustSignalListQueryInput:
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT
    continuity_object_id: UUID | None = None
    signal_state: TrustSignalState = "active"
    signal_type: TrustSignalType | None = None

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
            "continuity_object_id": (
                None if self.continuity_object_id is None else str(self.continuity_object_id)
            ),
            "signal_state": self.signal_state,
            "signal_type": self.signal_type,
        }


@dataclass(frozen=True, slots=True)
class ContinuityRecallQueryInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_RECALL_LIMIT
    debug: bool = False

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
            "debug": self.debug,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityResumptionBriefRequestInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    max_recent_changes: int = DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT
    max_open_loops: int = DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT
    include_non_promotable_facts: bool = False
    debug: bool = False

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "max_recent_changes": self.max_recent_changes,
            "max_open_loops": self.max_open_loops,
            "include_non_promotable_facts": self.include_non_promotable_facts,
            "debug": self.debug,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityBriefRequestInput:
    brief_type: ContinuityBriefType = "general"
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    max_relevant_facts: int = DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT
    max_recent_changes: int = DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT
    max_open_loops: int = DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT
    max_conflicts: int = DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT
    max_timeline_highlights: int = DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT
    include_non_promotable_facts: bool = False

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "brief_type": self.brief_type,
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "max_relevant_facts": self.max_relevant_facts,
            "max_recent_changes": self.max_recent_changes,
            "max_open_loops": self.max_open_loops,
            "max_conflicts": self.max_conflicts,
            "max_timeline_highlights": self.max_timeline_highlights,
            "include_non_promotable_facts": self.include_non_promotable_facts,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class TaskBriefCompileRequestInput:
    mode: TaskBriefMode
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    include_non_promotable_facts: bool = False
    provider_strategy: str | None = None
    briefing_strategy: TaskBriefingStrategy | None = None
    token_budget: int | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "mode": self.mode,
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "include_non_promotable_facts": self.include_non_promotable_facts,
            "provider_strategy": self.provider_strategy,
            "briefing_strategy": self.briefing_strategy,
            "token_budget": self.token_budget,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class TaskBriefComparisonRequestInput:
    primary: TaskBriefCompileRequestInput
    secondary: TaskBriefCompileRequestInput

    def as_payload(self) -> JsonObject:
        return {
            "primary": self.primary.as_payload(),
            "secondary": self.secondary.as_payload(),
        }


@dataclass(frozen=True, slots=True)
class ContinuityLifecycleQueryInput:
    limit: int = DEFAULT_CONTINUITY_LIFECYCLE_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ContinuityOpenLoopDashboardQueryInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityDailyBriefRequestInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityWeeklyReviewRequestInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload












@dataclass(frozen=True, slots=True)
class ContinuityOpenLoopReviewActionInput:
    action: ContinuityOpenLoopReviewAction
    note: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "action": self.action,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class OpenLoopCreateInput:
    title: str
    memory_id: UUID | None = None
    due_at: datetime | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "title": self.title,
            "memory_id": None if self.memory_id is None else str(self.memory_id),
        }
        payload["due_at"] = isoformat_or_none(self.due_at)
        return payload


@dataclass(frozen=True, slots=True)
class OpenLoopStatusUpdateInput:
    status: OpenLoopStatus
    resolution_note: str | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "status": self.status,
        }
        payload["resolution_note"] = self.resolution_note
        return payload


class ExtractedPreferenceCandidateRecord(TypedDict):
    memory_key: str
    value: JsonValue
    source_event_ids: list[str]
    delete_requested: bool
    pattern: ExplicitPreferencePattern
    subject_text: str


class ExtractedCommitmentCandidateRecord(TypedDict):
    memory_key: str
    value: JsonValue
    source_event_ids: list[str]
    delete_requested: bool
    pattern: ExplicitCommitmentPattern
    commitment_text: str
    open_loop_title: str


class PersistedMemoryRecord(TypedDict):
    id: str
    user_id: str
    memory_key: str
    value: JsonValue
    status: MemoryStatus
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
    deleted_at: str | None


class PersistedMemoryRevisionRecord(TypedDict):
    id: str
    user_id: str
    memory_id: str
    sequence_no: int
    action: AdmissionAction
    memory_key: str
    previous_value: JsonValue | None
    new_value: JsonValue | None
    source_event_ids: list[str]
    candidate: JsonObject
    created_at: str


@dataclass(frozen=True, slots=True)
class AdmissionDecisionOutput:
    action: AdmissionAction
    reason: str
    memory: PersistedMemoryRecord | None
    revision: PersistedMemoryRevisionRecord | None
    open_loop: OpenLoopRecord | None = None


class ExplicitPreferenceAdmissionRecord(TypedDict):
    decision: AdmissionAction
    reason: str
    memory: PersistedMemoryRecord | None
    revision: PersistedMemoryRevisionRecord | None


class ExplicitPreferenceExtractionSummary(TypedDict):
    source_event_id: str
    source_event_kind: str
    candidate_count: int
    admission_count: int
    persisted_change_count: int
    noop_count: int


class ExplicitPreferenceExtractionResponse(TypedDict):
    candidates: list[ExtractedPreferenceCandidateRecord]
    admissions: list[ExplicitPreferenceAdmissionRecord]
    summary: ExplicitPreferenceExtractionSummary


class ExplicitCommitmentOpenLoopOutcome(TypedDict):
    decision: ExplicitCommitmentOpenLoopDecision
    reason: str
    open_loop: OpenLoopRecord | None


class ExplicitCommitmentAdmissionRecord(TypedDict):
    decision: AdmissionAction
    reason: str
    memory: PersistedMemoryRecord | None
    revision: PersistedMemoryRevisionRecord | None
    open_loop: ExplicitCommitmentOpenLoopOutcome


class ExplicitCommitmentExtractionSummary(TypedDict):
    source_event_id: str
    source_event_kind: str
    candidate_count: int
    admission_count: int
    persisted_change_count: int
    noop_count: int
    open_loop_created_count: int
    open_loop_noop_count: int


class ExplicitCommitmentExtractionResponse(TypedDict):
    candidates: list[ExtractedCommitmentCandidateRecord]
    admissions: list[ExplicitCommitmentAdmissionRecord]
    summary: ExplicitCommitmentExtractionSummary


class ExplicitSignalCaptureSummary(TypedDict):
    source_event_id: str
    source_event_kind: str
    candidate_count: int
    admission_count: int
    persisted_change_count: int
    noop_count: int
    open_loop_created_count: int
    open_loop_noop_count: int
    preference_candidate_count: int
    preference_admission_count: int
    commitment_candidate_count: int
    commitment_admission_count: int


class ExplicitSignalCaptureResponse(TypedDict):
    preferences: ExplicitPreferenceExtractionResponse
    commitments: ExplicitCommitmentExtractionResponse
    summary: ExplicitSignalCaptureSummary


class ContinuityCaptureEventRecord(TypedDict):
    id: str
    raw_content: str
    explicit_signal: ContinuityCaptureExplicitSignal | None
    admission_posture: ContinuityCaptureAdmissionPosture
    admission_reason: str
    created_at: str


class ContinuityCaptureCandidateRecord(TypedDict):
    candidate_id: str
    candidate_type: ContinuityCaptureCandidateType
    object_type: ContinuityObjectType | None
    normalized_text: str
    confidence: float
    trust_class: MemoryTrustClass
    evidence_snippet: str
    explicit: bool
    source_role: str
    admission_reason: str
    proposed_action: ContinuityCaptureProposedAction


class ContinuityCaptureCandidatesSummary(TypedDict):
    candidate_count: int
    explicit_count: int
    high_confidence_count: int
    no_op_count: int


class ContinuityCaptureCandidatesResponse(TypedDict):
    candidates: list[ContinuityCaptureCandidateRecord]
    summary: ContinuityCaptureCandidatesSummary


class ContinuityCaptureCommitRecord(TypedDict):
    candidate_id: str
    candidate_type: ContinuityCaptureCandidateType
    decision: ContinuityCaptureCommitDecision
    reason: str
    persistence_target: str
    capture_event: ContinuityCaptureEventRecord | None
    continuity_object: ContinuityObjectRecord | None


class ContinuityCaptureCommitSummary(TypedDict):
    mode: ContinuityCaptureCommitMode
    candidate_count: int
    auto_saved_count: int
    review_queued_count: int
    noop_count: int
    duplicate_noop_count: int
    auto_saved_types: list[str]
    review_queued_types: list[str]


class ContinuityCaptureCommitResponse(TypedDict):
    commits: list[ContinuityCaptureCommitRecord]
    summary: ContinuityCaptureCommitSummary


class MemoryOperationCandidateRecord(TypedDict):
    id: str
    sync_fingerprint: str
    source_kind: str
    source_candidate_id: str
    source_candidate_type: str
    candidate_payload: JsonObject
    source_scope: JsonObject
    operation_type: MemoryOperationType
    operation_reason: str
    policy_action: MemoryOperationPolicyAction
    policy_reason: str
    target_continuity_object_id: str | None
    target_snapshot: JsonObject
    applied_operation_id: str | None
    created_at: str
    applied_at: str | None


class MemoryOperationRecord(TypedDict):
    id: str
    candidate_id: str
    operation_type: MemoryOperationType
    status: MemoryOperationStatus
    sync_fingerprint: str
    target_continuity_object_id: str | None
    resulting_continuity_object_id: str | None
    correction_event_id: str | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    details: JsonObject
    created_at: str


class MemoryOperationCandidateGenerateSummary(TypedDict):
    candidate_count: int
    auto_apply_count: int
    review_required_count: int
    noop_count: int
    operation_types: list[str]


class MemoryOperationCandidateGenerateResponse(TypedDict):
    items: list[MemoryOperationCandidateRecord]
    summary: MemoryOperationCandidateGenerateSummary


class MemoryOperationCommitSummary(TypedDict):
    requested_count: int
    applied_count: int
    no_op_count: int
    skipped_count: int
    duplicate_count: int
    operation_types: list[str]


class MemoryOperationCommitResponse(TypedDict):
    candidates: list[MemoryOperationCandidateRecord]
    operations: list[MemoryOperationRecord]
    summary: MemoryOperationCommitSummary


class MemoryOperationListSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    policy_action: MemoryOperationPolicyAction | None
    operation_type: MemoryOperationType | None
    sync_fingerprint: str | None


class MemoryOperationCandidateListResponse(TypedDict):
    items: list[MemoryOperationCandidateRecord]
    summary: MemoryOperationListSummary


class MemoryOperationListResponse(TypedDict):
    items: list[MemoryOperationRecord]
    summary: MemoryOperationListSummary


class ContinuityLifecycleStateRecord(TypedDict):
    is_preserved: bool
    preservation_status: ContinuityPreservationStatus
    is_searchable: bool
    searchability_status: ContinuitySearchabilityStatus
    is_promotable: bool
    promotion_status: ContinuityPromotionStatus


class ContinuityObjectRecord(TypedDict):
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    lifecycle: ContinuityLifecycleStateRecord
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    created_at: str
    updated_at: str


class ContinuityReviewObjectRecord(TypedDict):
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    lifecycle: ContinuityLifecycleStateRecord
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    last_confirmed_at: str | None
    supersedes_object_id: str | None
    superseded_by_object_id: str | None
    created_at: str
    updated_at: str
    explanation: NotRequired["ContinuityExplanationRecord"]


class ContinuityCorrectionEventRecord(TypedDict):
    id: str
    continuity_object_id: str
    action: ContinuityCorrectionAction
    reason: str | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    payload: JsonObject
    created_at: str


class ContinuityCaptureInboxItem(TypedDict):
    capture_event: ContinuityCaptureEventRecord
    derived_object: ContinuityObjectRecord | None


class ContinuityCaptureInboxSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    derived_count: int
    triage_count: int
    order: list[str]


class ContinuityCaptureCreateResponse(TypedDict):
    capture: ContinuityCaptureInboxItem


class ContinuityCaptureInboxResponse(TypedDict):
    items: list[ContinuityCaptureInboxItem]
    summary: ContinuityCaptureInboxSummary


class ContinuityCaptureDetailResponse(TypedDict):
    capture: ContinuityCaptureInboxItem


class ContinuityReviewQueueSummary(TypedDict):
    status: ContinuityReviewStatusFilter
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityReviewQueueResponse(TypedDict):
    items: list[ContinuityReviewObjectRecord]
    summary: ContinuityReviewQueueSummary


class ContinuitySupersessionChain(TypedDict):
    supersedes: ContinuityReviewObjectRecord | None
    superseded_by: ContinuityReviewObjectRecord | None


class ContinuityReviewDetail(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    correction_events: list[ContinuityCorrectionEventRecord]
    supersession_chain: ContinuitySupersessionChain


class ContinuityReviewDetailResponse(TypedDict):
    review: ContinuityReviewDetail


class ContradictionCaseRecord(TypedDict):
    id: str
    canonical_key: str
    status: ContradictionStatus
    kind: ContradictionKind
    rationale: str
    detection_payload: JsonObject
    resolution_action: ContradictionResolutionAction | None
    resolution_note: str | None
    resolved_at: str | None
    continuity_object_updated_at: str
    counterpart_object_updated_at: str
    created_at: str
    updated_at: str
    continuity_object: ContinuityReviewObjectRecord
    counterpart_object: ContinuityReviewObjectRecord


class ContradictionCaseListSummary(TypedDict):
    status: ContradictionStatus
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContradictionCaseListResponse(TypedDict):
    items: list[ContradictionCaseRecord]
    summary: ContradictionCaseListSummary


class ContradictionCaseDetailResponse(TypedDict):
    contradiction_case: ContradictionCaseRecord


class ContradictionSyncSummary(TypedDict):
    continuity_object_id: str | None
    scanned_object_count: int
    open_case_count: int
    resolved_case_count: int
    updated_case_count: int


class ContradictionSyncResponse(TypedDict):
    items: list[ContradictionCaseRecord]
    summary: ContradictionSyncSummary


class ContradictionResolveResponse(TypedDict):
    contradiction_case: ContradictionCaseRecord


class TrustSignalRecord(TypedDict):
    id: str
    continuity_object_id: str
    signal_key: str
    signal_type: TrustSignalType
    signal_state: TrustSignalState
    direction: TrustSignalDirection
    magnitude: float
    reason: str
    contradiction_case_id: str | None
    related_continuity_object_id: str | None
    payload: JsonObject
    created_at: str
    updated_at: str


class TrustSignalListSummary(TypedDict):
    continuity_object_id: str | None
    signal_state: TrustSignalState
    signal_type: TrustSignalType | None
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class TrustSignalListResponse(TypedDict):
    items: list[TrustSignalRecord]
    summary: TrustSignalListSummary


class ContinuityEvidenceArtifactRecord(TypedDict):
    id: str
    source_kind: str
    import_source_path: str
    relative_path: str
    display_name: str
    media_type: str
    created_at: str


class ContinuityEvidenceArtifactCopyRecord(TypedDict):
    id: str
    checksum_sha256: str
    content_length_bytes: int
    content_encoding: str
    content_text: str
    created_at: str


class ContinuityEvidenceArtifactSegmentRecord(TypedDict):
    id: str
    source_item_id: str
    sequence_no: int
    segment_kind: str
    locator: JsonObject
    raw_content: str
    checksum_sha256: str
    created_at: str


class ContinuityEvidenceLinkRecord(TypedDict):
    id: str
    relationship: str
    created_at: str
    artifact: ContinuityEvidenceArtifactRecord
    artifact_copy: ContinuityEvidenceArtifactCopyRecord
    artifact_segment: ContinuityEvidenceArtifactSegmentRecord | None


class ContinuityExplanationSourceFactRecord(TypedDict):
    kind: str
    label: str
    value: str


class ContinuityExplanationEvidenceSegmentRecord(TypedDict):
    relationship: str
    source_kind: str
    source_id: str
    display_name: str
    relative_path: str | None
    segment_kind: str | None
    locator: JsonObject | None
    snippet: str
    created_at: str | None


class ContinuityExplanationSupersessionNoteRecord(TypedDict):
    kind: str
    note: str
    action: str | None
    related_object_id: str | None
    created_at: str | None


class ContinuityExplanationContradictionRecord(TypedDict):
    open_case_count: int
    resolved_case_count: int
    open_case_ids: list[str]
    kinds: list[ContradictionKind]
    counterpart_object_ids: list[str]
    penalty_score: float


class ContinuityExplanationTrustRecord(TypedDict):
    trust_class: MemoryTrustClass
    trust_reason: str
    confirmation_status: MemoryConfirmationStatus
    confidence: float
    provenance_posture: ContinuityRecallProvenancePosture
    evidence_segment_count: int
    correction_count: int
    active_signal_count: int


class ContinuityExplanationTimestampsRecord(TypedDict):
    capture_created_at: str | None
    created_at: str
    updated_at: str
    last_confirmed_at: str | None


class ContinuityExplanationRecord(TypedDict):
    source_facts: list[ContinuityExplanationSourceFactRecord]
    trust: ContinuityExplanationTrustRecord
    contradictions: ContinuityExplanationContradictionRecord
    evidence_segments: list[ContinuityExplanationEvidenceSegmentRecord]
    supersession_notes: list[ContinuityExplanationSupersessionNoteRecord]
    timestamps: ContinuityExplanationTimestampsRecord
    proposal_rationale: NotRequired[str]


class ContinuityExplainRecord(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    explanation: ContinuityExplanationRecord
    evidence_chain: list[ContinuityEvidenceLinkRecord]


class ContinuityExplainResponse(TypedDict):
    explain: ContinuityExplainRecord


class ContinuityArtifactDetailRecord(TypedDict):
    artifact: ContinuityEvidenceArtifactRecord
    copies: list[ContinuityEvidenceArtifactCopyRecord]
    segments: list[ContinuityEvidenceArtifactSegmentRecord]


class ContinuityArtifactDetailResponse(TypedDict):
    artifact_detail: ContinuityArtifactDetailRecord


class ContinuityRecallScopeFilters(TypedDict):
    thread_id: NotRequired[str]
    task_id: NotRequired[str]
    project: NotRequired[str]
    person: NotRequired[str]
    since: str | None
    until: str | None


class ContinuityRecallScopeMatch(TypedDict):
    kind: ContinuityRecallScopeKind
    value: str


class ContinuityRecallProvenanceReference(TypedDict):
    source_kind: str
    source_id: str


class ContinuityRecallOrderingMetadata(TypedDict):
    scope_match_count: int
    query_term_match_count: int
    semantic_similarity_score: float
    exact_match_score: float
    recency_score: float
    temporal_overlap_score: float
    entity_match_count: int
    confirmation_rank: int
    trust_class: MemoryTrustClass
    trust_rank: int
    freshness_posture: ContinuityRecallFreshnessPosture
    freshness_rank: int
    provenance_posture: ContinuityRecallProvenancePosture
    provenance_rank: int
    supersession_posture: ContinuityRecallSupersessionPosture
    supersession_rank: int
    supersession_freshness_score: float
    posture_rank: int
    lifecycle_rank: int
    open_contradiction_count: int
    contradiction_penalty_score: float
    confidence: float


class ContinuityRetrievalStageScoreRecord(TypedDict):
    raw_score: float
    normalized_score: float
    matched: bool
    reason: str


class ContinuityRetrievalDebugCandidateRecord(TypedDict):
    object_id: str
    title: str
    object_type: ContinuityObjectType
    status: str
    selected: bool
    rank: int | None
    exclusion_reason: str | None
    scope_matches: list[ContinuityRecallScopeMatch]
    ordering: ContinuityRecallOrderingMetadata
    stage_scores: dict[str, ContinuityRetrievalStageScoreRecord]
    relevance: float


class ContinuityRetrievalDebugRecord(TypedDict):
    retrieval_run_id: str | None
    source_surface: str
    ranking_strategy: str
    query_terms: list[str]
    entity_anchor_names: list[str]
    entity_expansion_names: list[str]
    candidate_count: int
    selected_count: int
    candidates: list[ContinuityRetrievalDebugCandidateRecord]


class ContinuityRecallResultRecord(TypedDict):
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    lifecycle: ContinuityLifecycleStateRecord
    title: str
    body: JsonObject
    provenance: JsonObject
    confirmation_status: MemoryConfirmationStatus
    admission_posture: ContinuityCaptureAdmissionPosture
    confidence: float
    relevance: float
    last_confirmed_at: str | None
    supersedes_object_id: str | None
    superseded_by_object_id: str | None
    scope_matches: list[ContinuityRecallScopeMatch]
    provenance_references: list[ContinuityRecallProvenanceReference]
    ordering: ContinuityRecallOrderingMetadata
    explanation: ContinuityExplanationRecord
    created_at: str
    updated_at: str


class ContinuityRecallSummary(TypedDict):
    query: str | None
    filters: ContinuityRecallScopeFilters
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityRecallResponse(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ContinuityRecallSummary
    debug: NotRequired[ContinuityRetrievalDebugRecord]


class ContinuityLifecycleCounts(TypedDict):
    preserved_count: int
    searchable_count: int
    promotable_count: int
    not_searchable_count: int
    not_promotable_count: int


class ContinuityLifecycleListSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    counts: ContinuityLifecycleCounts
    order: list[str]


class ContinuityLifecycleListResponse(TypedDict):
    items: list[ContinuityReviewObjectRecord]
    summary: ContinuityLifecycleListSummary


class ContinuityLifecycleDetailResponse(TypedDict):
    continuity_object: ContinuityReviewObjectRecord


class ContinuityResumptionEmptyState(TypedDict):
    is_empty: bool
    message: str


class ContinuityResumptionSingleSection(TypedDict):
    item: ContinuityRecallResultRecord | None
    empty_state: ContinuityResumptionEmptyState


class ContinuityResumptionListSection(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ResumptionBriefSectionSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityResumptionBriefRecord(TypedDict):
    assembly_version: str
    scope: ContinuityRecallScopeFilters
    last_decision: ContinuityResumptionSingleSection
    open_loops: ContinuityResumptionListSection
    recent_changes: ContinuityResumptionListSection
    next_action: ContinuityResumptionSingleSection
    sources: list[str]


class ContinuityResumptionDebugRecord(TypedDict):
    retrieval: ContinuityRetrievalDebugRecord


class ContinuityResumptionBriefResponse(TypedDict):
    brief: ContinuityResumptionBriefRecord
    debug: NotRequired[ContinuityResumptionDebugRecord]


class ContinuityBriefRelevantFactsSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]
    task_brief_mode: TaskBriefMode


class ContinuityBriefRelevantFactsSection(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ContinuityBriefRelevantFactsSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityBriefConflictSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityBriefConflictSection(TypedDict):
    items: list[ContradictionCaseRecord]
    summary: ContinuityBriefConflictSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityBriefTimelineHighlightRecord(TypedDict):
    continuity_object_id: str
    title: str
    object_type: ContinuityObjectType
    status: str
    created_at: str
    source_section: str


class ContinuityBriefTimelineSection(TypedDict):
    items: list[ContinuityBriefTimelineHighlightRecord]
    summary: ResumptionBriefSectionSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityBriefSuggestedActionRecord(TypedDict):
    continuity_object_id: str | None
    title: str
    object_type: ContinuityObjectType | None
    reason: str
    confidence_posture: RecommendationConfidencePosture
    provenance_references: list[ContinuityRecallProvenanceReference]


class ContinuityBriefSelectionStrategyRecord(TypedDict):
    task_brief_mode: TaskBriefMode
    provider_strategy: str
    briefing_strategy: TaskBriefingStrategy
    token_budget: int
    budget_source: str


class ContinuityBriefProvenanceSummary(TypedDict):
    source_object_count: int
    reference_count: int
    reference_kind_count: int


class ContinuityBriefProvenanceBundle(TypedDict):
    source_object_ids: list[str]
    references: list[ContinuityRecallProvenanceReference]
    summary: ContinuityBriefProvenanceSummary


class ContinuityBriefTrustPostureRecord(TypedDict):
    confidence_posture: RecommendationConfidencePosture
    average_confidence: float
    strongest_trust_class: MemoryTrustClass | None
    weakest_provenance_posture: ContinuityRecallProvenancePosture | None
    active_signal_count: int
    positive_signal_count: int
    negative_signal_count: int
    neutral_signal_count: int
    open_conflict_count: int
    rationale: str


class ContinuityBriefRecord(TypedDict):
    assembly_version: str
    brief_type: ContinuityBriefType
    scope: ContinuityRecallScopeFilters
    summary: str
    selection_strategy: ContinuityBriefSelectionStrategyRecord
    relevant_facts: ContinuityBriefRelevantFactsSection
    recent_changes: ContinuityResumptionListSection
    open_loops: ContinuityResumptionListSection
    conflicts: ContinuityBriefConflictSection
    timeline_highlights: ContinuityBriefTimelineSection
    next_suggested_action: ContinuityBriefSuggestedActionRecord
    provenance_bundle: ContinuityBriefProvenanceBundle
    trust_posture: ContinuityBriefTrustPostureRecord
    sources: list[str]


class ContinuityBriefResponse(TypedDict):
    brief: ContinuityBriefRecord


class TaskBriefEmptyState(TypedDict):
    is_empty: bool
    message: str


class TaskBriefSectionSummary(TypedDict):
    candidate_count: int
    selected_count: int
    truncated_count: int
    token_budget: int
    estimated_tokens: int
    order: list[str]


class TaskBriefSectionRecord(TypedDict):
    section_key: str
    title: str
    intent: str
    selection_rule: str
    items: list[ContinuityRecallResultRecord]
    summary: TaskBriefSectionSummary
    empty_state: TaskBriefEmptyState


class TaskBriefStrategyRecord(TypedDict):
    provider_strategy: str
    briefing_strategy: TaskBriefingStrategy
    token_budget: int
    budget_source: str


class TaskBriefSummary(TypedDict):
    candidate_count: int
    selected_item_count: int
    estimated_tokens: int
    token_budget: int
    truncated: bool
    deterministic_key: str
    section_order: list[str]
    mode_order: list[str]


class TaskBriefRecord(TypedDict):
    assembly_version: str
    mode: TaskBriefMode
    scope: ContinuityRecallScopeFilters
    strategy: TaskBriefStrategyRecord
    summary: TaskBriefSummary
    sections: list[TaskBriefSectionRecord]
    sources: list[str]


class TaskBriefPersistenceRecord(TypedDict):
    task_brief_id: str
    created_at: str


class TaskBriefResponse(TypedDict):
    task_brief: TaskBriefRecord
    persistence: TaskBriefPersistenceRecord


class TaskBriefComparisonStats(TypedDict):
    primary_mode: TaskBriefMode
    secondary_mode: TaskBriefMode
    smaller_mode: TaskBriefMode | None
    estimated_token_delta: int
    selected_item_delta: int
    shared_item_ids: list[str]
    primary_is_smaller: bool


class TaskBriefComparisonResponse(TypedDict):
    comparison_version: str
    primary: TaskBriefRecord
    secondary: TaskBriefRecord
    comparison: TaskBriefComparisonStats


class ContinuityOpenLoopSectionSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityOpenLoopSection(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ContinuityOpenLoopSectionSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityOpenLoopDashboardSummary(TypedDict):
    limit: int
    total_count: int
    posture_order: list[ContinuityOpenLoopPosture]
    item_order: list[str]


class ContinuityOpenLoopDashboardRecord(TypedDict):
    scope: ContinuityRecallScopeFilters
    waiting_for: ContinuityOpenLoopSection
    blocker: ContinuityOpenLoopSection
    stale: ContinuityOpenLoopSection
    next_action: ContinuityOpenLoopSection
    summary: ContinuityOpenLoopDashboardSummary
    sources: list[str]


class ContinuityOpenLoopDashboardResponse(TypedDict):
    dashboard: ContinuityOpenLoopDashboardRecord


class ContinuityDailyBriefRecord(TypedDict):
    assembly_version: str
    scope: ContinuityRecallScopeFilters
    waiting_for_highlights: ContinuityOpenLoopSection
    blocker_highlights: ContinuityOpenLoopSection
    stale_items: ContinuityOpenLoopSection
    next_suggested_action: ContinuityResumptionSingleSection
    sources: list[str]


class ContinuityDailyBriefResponse(TypedDict):
    brief: ContinuityDailyBriefRecord


class ContinuityWeeklyReviewRollup(TypedDict):
    total_count: int
    waiting_for_count: int
    blocker_count: int
    stale_count: int
    correction_recurrence_count: int
    freshness_drift_count: int
    next_action_count: int
    posture_order: list[ContinuityOpenLoopPosture]


class ContinuityWeeklyReviewRecord(TypedDict):
    assembly_version: str
    scope: ContinuityRecallScopeFilters
    rollup: ContinuityWeeklyReviewRollup
    waiting_for: ContinuityOpenLoopSection
    blocker: ContinuityOpenLoopSection
    stale: ContinuityOpenLoopSection
    next_action: ContinuityOpenLoopSection
    sources: list[str]


class ContinuityWeeklyReviewResponse(TypedDict):
    review: ContinuityWeeklyReviewRecord




















































































































class ContinuityOpenLoopReviewActionResponse(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    correction_event: ContinuityCorrectionEventRecord
    review_action: ContinuityOpenLoopReviewAction
    lifecycle_outcome: str


class ContinuityCorrectionApplyResponse(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    correction_event: ContinuityCorrectionEventRecord
    replacement_object: ContinuityReviewObjectRecord | None


class MemoryReviewRecord(TypedDict):
    id: str
    memory_key: str
    value: JsonValue
    status: MemoryStatus
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
    deleted_at: str | None


class MemoryReviewListSummary(TypedDict):
    status: MemoryReviewStatusFilter
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class MemoryReviewListResponse(TypedDict):
    items: list[MemoryReviewRecord]
    summary: MemoryReviewListSummary


class MemoryReviewDetailResponse(TypedDict):
    memory: MemoryReviewRecord


class OpenLoopRecord(TypedDict):
    id: str
    memory_id: str | None
    title: str
    status: OpenLoopStatus
    opened_at: str
    due_at: str | None
    resolved_at: str | None
    resolution_note: str | None
    created_at: str
    updated_at: str


class OpenLoopListSummary(TypedDict):
    status: OpenLoopStatusFilter
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class OpenLoopListResponse(TypedDict):
    items: list[OpenLoopRecord]
    summary: OpenLoopListSummary


class OpenLoopDetailResponse(TypedDict):
    open_loop: OpenLoopRecord


class OpenLoopCreateResponse(TypedDict):
    open_loop: OpenLoopRecord


class OpenLoopStatusUpdateResponse(TypedDict):
    open_loop: OpenLoopRecord


class MemoryRevisionReviewRecord(TypedDict):
    id: str
    memory_id: str
    sequence_no: int
    action: AdmissionAction
    memory_key: str
    previous_value: JsonValue | None
    new_value: JsonValue | None
    source_event_ids: list[str]
    created_at: str


class MemoryRevisionReviewListSummary(TypedDict):
    memory_id: str
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class MemoryRevisionReviewListResponse(TypedDict):
    items: list[MemoryRevisionReviewRecord]
    summary: MemoryRevisionReviewListSummary


class MemoryReviewLabelCounts(TypedDict):
    correct: int
    incorrect: int
    outdated: int
    insufficient_evidence: int


class MemoryReviewLabelRecord(TypedDict):
    id: str
    memory_id: str
    reviewer_user_id: str
    label: MemoryReviewLabelValue
    note: str | None
    created_at: str


class MemoryReviewLabelSummary(TypedDict):
    memory_id: str
    total_count: int
    counts_by_label: MemoryReviewLabelCounts
    order: list[str]


class MemoryReviewLabelCreateResponse(TypedDict):
    label: MemoryReviewLabelRecord
    summary: MemoryReviewLabelSummary


class MemoryReviewLabelListResponse(TypedDict):
    items: list[MemoryReviewLabelRecord]
    summary: MemoryReviewLabelSummary


class MemoryReviewQueueItem(TypedDict):
    id: str
    memory_key: str
    value: JsonValue
    status: Literal["active"]
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
    is_high_risk: bool
    is_stale_truth: bool
    is_promotable: bool
    queue_priority_mode: MemoryReviewQueuePriorityMode
    priority_reason: str
    created_at: str
    updated_at: str


class MemoryReviewQueueSummary(TypedDict):
    memory_status: Literal["active"]
    review_state: Literal["unlabeled"]
    priority_mode: MemoryReviewQueuePriorityMode
    available_priority_modes: list[MemoryReviewQueuePriorityMode]
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class MemoryReviewQueueResponse(TypedDict):
    items: list[MemoryReviewQueueItem]
    summary: MemoryReviewQueueSummary


class MemoryQualityGateComputationCounts(TypedDict):
    active_memory_count: int
    labeled_active_memory_count: int
    adjudicated_correct_count: int
    adjudicated_incorrect_count: int
    outdated_label_count: int
    insufficient_evidence_label_count: int


class MemoryQualityGateSummary(TypedDict):
    status: MemoryQualityGateStatus
    precision: float | None
    precision_target: float
    adjudicated_sample_count: int
    minimum_adjudicated_sample: int
    remaining_to_minimum_sample: int
    unlabeled_memory_count: int
    high_risk_memory_count: int
    stale_truth_count: int
    superseded_active_conflict_count: int
    counts: MemoryQualityGateComputationCounts


class MemoryQualityGateResponse(TypedDict):
    summary: MemoryQualityGateSummary


class MemoryTrustQueueAgingSummary(TypedDict):
    anchor_updated_at: str | None
    newest_updated_at: str | None
    oldest_updated_at: str | None
    backlog_span_hours: float
    fresh_within_24h_count: int
    aging_24h_to_72h_count: int
    stale_over_72h_count: int


class MemoryTrustQueuePostureSummary(TypedDict):
    priority_mode: MemoryReviewQueuePriorityMode
    total_count: int
    high_risk_count: int
    stale_truth_count: int
    priority_reason_counts: dict[str, int]
    order: list[str]
    aging: MemoryTrustQueueAgingSummary


class MemoryTrustCorrectionFreshnessSummary(TypedDict):
    total_open_loop_count: int
    stale_open_loop_count: int
    correction_recurrence_count: int
    freshness_drift_count: int


class MemoryTrustRecommendedReview(TypedDict):
    priority_mode: MemoryReviewQueuePriorityMode
    action: MemoryQualityReviewAction
    reason: str


MemoryHygienePosture = Literal["healthy", "watch", "critical"]
MemoryHygieneFocusKind = Literal[
    "duplicates",
    "stale_facts",
    "unresolved_contradictions",
    "weak_trust",
    "review_queue_pressure",
]


class MemoryDuplicateGroupRecord(TypedDict):
    group_key: str
    memory_type: str
    normalized_value: str
    count: int
    memory_ids: list[str]
    memory_keys: list[str]
    latest_updated_at: str


class MemoryReviewQueuePressureSummary(TypedDict):
    posture: MemoryHygienePosture
    total_count: int
    stale_over_72h_count: int
    aging_24h_to_72h_count: int
    reason: str


class MemoryHygieneFocusRecord(TypedDict):
    kind: MemoryHygieneFocusKind
    posture: MemoryHygienePosture
    count: int
    reason: str
    action: str
    sample_ids: list[str]


class MemoryHygieneDashboardSummary(TypedDict):
    posture: MemoryHygienePosture
    reason: str
    duplicate_group_count: int
    duplicate_memory_count: int
    stale_fact_count: int
    unresolved_contradiction_count: int
    weak_trust_count: int
    review_queue_pressure: MemoryReviewQueuePressureSummary
    duplicate_groups: list[MemoryDuplicateGroupRecord]
    focus: list[MemoryHygieneFocusRecord]
    sources: list[str]


class MemoryHygieneDashboardResponse(TypedDict):
    dashboard: MemoryHygieneDashboardSummary


class MemoryTrustDashboardSummary(TypedDict):
    quality_gate: MemoryQualityGateSummary
    queue_posture: MemoryTrustQueuePostureSummary
    retrieval_quality: RetrievalEvaluationSummary
    correction_freshness: MemoryTrustCorrectionFreshnessSummary
    recommended_review: MemoryTrustRecommendedReview
    sources: list[str]


class MemoryTrustDashboardResponse(TypedDict):
    dashboard: MemoryTrustDashboardSummary


class MemoryEvaluationSummary(TypedDict):
    total_memory_count: int
    active_memory_count: int
    deleted_memory_count: int
    labeled_memory_count: int
    unlabeled_memory_count: int
    total_label_row_count: int
    label_row_counts_by_value: MemoryReviewLabelCounts
    label_value_order: list[MemoryReviewLabelValue]


class MemoryEvaluationSummaryResponse(TypedDict):
    summary: MemoryEvaluationSummary


__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
