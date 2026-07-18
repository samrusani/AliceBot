from __future__ import annotations

from dataclasses import dataclass, field
import sys as _sys
from typing import Literal, NotRequired, TypedDict
from uuid import UUID

from alicebot_api._contracts.common import (
    ApprovalStatus,
    DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    ProxyExecutionStatus,
    TaskArtifactChunkEmbeddingListScopeKind,
    TaskArtifactChunkRetrievalScopeKind,
    TaskArtifactIngestionStatus,
    TaskArtifactStatus,
    TaskLifecycleSource,
    TaskRunFailureClass,
    TaskRunRetryPosture,
    TaskRunStatus,
    TaskRunStopReason,
    TaskStatus,
    TaskStepKind,
    TaskStepStatus,
    TaskWorkspaceStatus,
    ToolRoutingDecision,
)
from alicebot_api._contracts.continuity import OpenLoopRecord
from alicebot_api._contracts.governance import ToolRecord, ToolRoutingRequestRecord
from alicebot_api._contracts.runtime import ContextPackMemory, ThreadEventRecord, ThreadRecord
from alicebot_api.store import JsonObject


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


@dataclass(frozen=True, slots=True)
class TaskArtifactChunkEmbeddingUpsertInput:
    task_artifact_chunk_id: UUID
    embedding_config_id: UUID
    vector: tuple[float, ...]

    def as_payload(self) -> JsonObject:
        return {
            "task_artifact_chunk_id": str(self.task_artifact_chunk_id),
            "embedding_config_id": str(self.embedding_config_id),
            "vector": [float(value) for value in self.vector],
        }


@dataclass(frozen=True, slots=True)
class TaskCreateInput:
    thread_id: UUID
    tool_id: UUID
    status: TaskStatus
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    latest_approval_id: UUID | None = None
    latest_execution_id: UUID | None = None


class TaskRecord(TypedDict):
    id: str
    thread_id: str
    tool_id: str
    status: TaskStatus
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    latest_approval_id: str | None
    latest_execution_id: str | None
    created_at: str
    updated_at: str


class TaskCreateResponse(TypedDict):
    task: TaskRecord


@dataclass(frozen=True, slots=True)
class TaskStepCreateInput:
    task_id: UUID
    sequence_no: int
    kind: TaskStepKind
    status: TaskStepStatus
    request: ToolRoutingRequestRecord
    outcome: "TaskStepOutcomeSnapshot"
    trace_id: UUID
    trace_kind: str


@dataclass(frozen=True, slots=True)
class TaskStepNextCreateInput:
    task_id: UUID
    kind: TaskStepKind
    status: TaskStepStatus
    request: ToolRoutingRequestRecord
    outcome: "TaskStepOutcomeSnapshot"
    lineage: "TaskStepLineageInput"


@dataclass(frozen=True, slots=True)
class TaskStepTransitionInput:
    task_step_id: UUID
    status: TaskStepStatus
    outcome: "TaskStepOutcomeSnapshot"


@dataclass(frozen=True, slots=True)
class TaskStepLineageInput:
    parent_step_id: UUID
    source_approval_id: UUID | None = None
    source_execution_id: UUID | None = None


class TaskListSummary(TypedDict):
    total_count: int
    order: list[str]


class TaskListResponse(TypedDict):
    items: list[TaskRecord]
    summary: TaskListSummary


class TaskDetailResponse(TypedDict):
    task: TaskRecord


@dataclass(frozen=True, slots=True)
class TaskRunCreateInput:
    task_id: UUID
    checkpoint: JsonObject = field(default_factory=dict)
    max_ticks: int = 1
    retry_cap: int | None = None


@dataclass(frozen=True, slots=True)
class TaskRunTickInput:
    task_run_id: UUID


@dataclass(frozen=True, slots=True)
class TaskRunPauseInput:
    task_run_id: UUID


@dataclass(frozen=True, slots=True)
class TaskRunResumeInput:
    task_run_id: UUID


@dataclass(frozen=True, slots=True)
class TaskRunCancelInput:
    task_run_id: UUID


class TaskRunRecord(TypedDict):
    id: str
    task_id: str
    status: TaskRunStatus
    checkpoint: JsonObject
    tick_count: int
    step_count: int
    max_ticks: int
    retry_count: int
    retry_cap: int
    retry_posture: TaskRunRetryPosture
    failure_class: TaskRunFailureClass | None
    stop_reason: TaskRunStopReason | None
    last_transitioned_at: str
    created_at: str
    updated_at: str


class TaskRunCreateResponse(TypedDict):
    task_run: TaskRunRecord


class TaskRunListSummary(TypedDict):
    task_id: str
    total_count: int
    order: list[str]


class TaskRunListResponse(TypedDict):
    items: list[TaskRunRecord]
    summary: TaskRunListSummary


class TaskRunDetailResponse(TypedDict):
    task_run: TaskRunRecord


class TaskRunMutationResponse(TypedDict):
    task_run: TaskRunRecord
    previous_status: TaskRunStatus


@dataclass(frozen=True, slots=True)
class TaskWorkspaceCreateInput:
    task_id: UUID
    status: TaskWorkspaceStatus


class TaskWorkspaceRecord(TypedDict):
    id: str
    task_id: str
    status: TaskWorkspaceStatus
    local_path: str
    created_at: str
    updated_at: str


class TaskWorkspaceCreateResponse(TypedDict):
    workspace: TaskWorkspaceRecord


class TaskWorkspaceListSummary(TypedDict):
    total_count: int
    order: list[str]


class TaskWorkspaceListResponse(TypedDict):
    items: list[TaskWorkspaceRecord]
    summary: TaskWorkspaceListSummary


class TaskWorkspaceDetailResponse(TypedDict):
    workspace: TaskWorkspaceRecord


@dataclass(frozen=True, slots=True)
class TaskArtifactRegisterInput:
    task_workspace_id: UUID
    local_path: str
    media_type_hint: str | None = None


@dataclass(frozen=True, slots=True)
class TaskArtifactIngestInput:
    task_artifact_id: UUID


@dataclass(frozen=True, slots=True)
class TaskScopedArtifactChunkRetrievalInput:
    task_id: UUID
    query: str


@dataclass(frozen=True, slots=True)
class ArtifactScopedArtifactChunkRetrievalInput:
    task_artifact_id: UUID
    query: str


@dataclass(frozen=True, slots=True)
class TaskScopedSemanticArtifactChunkRetrievalInput:
    task_id: UUID
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "task_id": str(self.task_id),
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ArtifactScopedSemanticArtifactChunkRetrievalInput:
    task_artifact_id: UUID
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "task_artifact_id": str(self.task_artifact_id),
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


class TaskArtifactRecord(TypedDict):
    id: str
    task_id: str
    task_workspace_id: str
    status: TaskArtifactStatus
    ingestion_status: TaskArtifactIngestionStatus
    relative_path: str
    media_type_hint: str | None
    created_at: str
    updated_at: str


class TaskArtifactCreateResponse(TypedDict):
    artifact: TaskArtifactRecord


class TaskArtifactListSummary(TypedDict):
    total_count: int
    order: list[str]


class TaskArtifactListResponse(TypedDict):
    items: list[TaskArtifactRecord]
    summary: TaskArtifactListSummary


class TaskArtifactDetailResponse(TypedDict):
    artifact: TaskArtifactRecord


class TaskArtifactChunkRecord(TypedDict):
    id: str
    task_artifact_id: str
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: str
    updated_at: str


class TaskArtifactChunkListSummary(TypedDict):
    total_count: int
    total_characters: int
    media_type: str
    chunking_rule: str
    order: list[str]


class TaskArtifactChunkListResponse(TypedDict):
    items: list[TaskArtifactChunkRecord]
    summary: TaskArtifactChunkListSummary


class TaskArtifactChunkEmbeddingRecord(TypedDict):
    id: str
    task_artifact_id: str
    task_artifact_chunk_id: str
    task_artifact_chunk_sequence_no: int
    embedding_config_id: str
    dimensions: int
    vector: list[float]
    created_at: str
    updated_at: str


class TaskArtifactChunkEmbeddingWriteResponse(TypedDict):
    embedding: TaskArtifactChunkEmbeddingRecord
    write_mode: Literal["created", "updated"]


class TaskArtifactChunkEmbeddingDetailResponse(TypedDict):
    embedding: TaskArtifactChunkEmbeddingRecord


class TaskArtifactChunkEmbeddingListScope(TypedDict):
    kind: TaskArtifactChunkEmbeddingListScopeKind
    task_artifact_id: str
    task_artifact_chunk_id: NotRequired[str]


class TaskArtifactChunkEmbeddingListSummary(TypedDict):
    total_count: int
    order: list[str]
    scope: TaskArtifactChunkEmbeddingListScope


class TaskArtifactChunkEmbeddingListResponse(TypedDict):
    items: list[TaskArtifactChunkEmbeddingRecord]
    summary: TaskArtifactChunkEmbeddingListSummary


class TaskArtifactIngestionResponse(TypedDict):
    artifact: TaskArtifactRecord
    summary: TaskArtifactChunkListSummary


class TaskArtifactChunkRetrievalMatch(TypedDict):
    matched_query_terms: list[str]
    matched_query_term_count: int
    first_match_char_start: int


class TaskArtifactChunkRetrievalItem(TypedDict):
    id: str
    task_id: str
    task_artifact_id: str
    relative_path: str
    media_type: str
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    match: TaskArtifactChunkRetrievalMatch


class TaskArtifactChunkRetrievalScope(TypedDict):
    kind: TaskArtifactChunkRetrievalScopeKind
    task_id: str
    task_artifact_id: NotRequired[str]


class TaskArtifactChunkRetrievalSummary(TypedDict):
    total_count: int
    searched_artifact_count: int
    query: str
    query_terms: list[str]
    matching_rule: str
    order: list[str]
    scope: TaskArtifactChunkRetrievalScope


class TaskArtifactChunkRetrievalResponse(TypedDict):
    items: list[TaskArtifactChunkRetrievalItem]
    summary: TaskArtifactChunkRetrievalSummary


class TaskArtifactChunkSemanticRetrievalItem(TypedDict):
    id: str
    task_id: str
    task_artifact_id: str
    relative_path: str
    media_type: str
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    score: float


class TaskArtifactChunkSemanticRetrievalSummary(TypedDict):
    embedding_config_id: str
    query_vector_dimensions: int
    limit: int
    returned_count: int
    searched_artifact_count: int
    similarity_metric: Literal["cosine_similarity"]
    order: list[str]
    scope: TaskArtifactChunkRetrievalScope


class TaskArtifactChunkSemanticRetrievalResponse(TypedDict):
    items: list[TaskArtifactChunkSemanticRetrievalItem]
    summary: TaskArtifactChunkSemanticRetrievalSummary


class TaskStepTraceLink(TypedDict):
    trace_id: str
    trace_kind: str


class TaskStepOutcomeSnapshot(TypedDict):
    routing_decision: ToolRoutingDecision
    approval_id: str | None
    approval_status: ApprovalStatus | None
    execution_id: str | None
    execution_status: ProxyExecutionStatus | None
    blocked_reason: str | None


class TaskStepLineageRecord(TypedDict):
    parent_step_id: str | None
    source_approval_id: str | None
    source_execution_id: str | None


class TaskStepRecord(TypedDict):
    id: str
    task_id: str
    sequence_no: int
    kind: TaskStepKind
    status: TaskStepStatus
    request: ToolRoutingRequestRecord
    outcome: TaskStepOutcomeSnapshot
    lineage: TaskStepLineageRecord
    trace: TaskStepTraceLink
    created_at: str
    updated_at: str


class TaskStepCreateResponse(TypedDict):
    task_step: TaskStepRecord


class TaskStepSequencingSummary(TypedDict):
    task_id: str
    total_count: int
    latest_sequence_no: int | None
    latest_status: TaskStepStatus | None
    next_sequence_no: int
    append_allowed: bool
    order: list[str]


class TaskStepListSummary(TaskStepSequencingSummary):
    pass


class TaskStepListResponse(TypedDict):
    items: list[TaskStepRecord]
    summary: TaskStepListSummary


class TaskStepDetailResponse(TypedDict):
    task_step: TaskStepRecord


class TaskStepMutationTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class TaskStepNextCreateResponse(TypedDict):
    task: TaskRecord
    task_step: TaskStepRecord
    sequencing: TaskStepSequencingSummary
    trace: TaskStepMutationTraceSummary


class TaskStepTransitionResponse(TypedDict):
    task: TaskRecord
    task_step: TaskStepRecord
    sequencing: TaskStepSequencingSummary
    trace: TaskStepMutationTraceSummary


class ResumptionBriefSectionSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ResumptionBriefConversationSummary(ResumptionBriefSectionSummary):
    kinds: list[str]


class ResumptionBriefConversationSection(TypedDict):
    items: list[ThreadEventRecord]
    summary: ResumptionBriefConversationSummary


class ResumptionBriefOpenLoopSection(TypedDict):
    items: list[OpenLoopRecord]
    summary: ResumptionBriefSectionSummary


class ResumptionBriefMemoryHighlightSection(TypedDict):
    items: list[ContextPackMemory]
    summary: ResumptionBriefSectionSummary


class ResumptionBriefWorkflowSummary(TypedDict):
    present: bool
    task_order: list[str]
    task_step_order: list[str]


class ResumptionBriefWorkflowPosture(TypedDict):
    task: TaskRecord
    latest_task_step: TaskStepRecord | None
    summary: ResumptionBriefWorkflowSummary


class ResumptionBriefRecord(TypedDict):
    assembly_version: str
    thread: ThreadRecord
    conversation: ResumptionBriefConversationSection
    open_loops: ResumptionBriefOpenLoopSection
    memory_highlights: ResumptionBriefMemoryHighlightSection
    workflow: ResumptionBriefWorkflowPosture | None
    sources: list[str]


class ResumptionBriefResponse(TypedDict):
    brief: ResumptionBriefRecord


class TaskLifecycleStateTracePayload(TypedDict):
    task_id: str
    source: TaskLifecycleSource
    previous_status: TaskStatus | None
    current_status: TaskStatus
    latest_approval_id: str | None
    latest_execution_id: str | None


class TaskLifecycleSummaryTracePayload(TypedDict):
    task_id: str
    source: TaskLifecycleSource
    final_status: TaskStatus
    latest_approval_id: str | None
    latest_execution_id: str | None


class TaskStepLifecycleStateTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    source: TaskLifecycleSource
    sequence_no: int
    kind: TaskStepKind
    previous_status: TaskStepStatus | None
    current_status: TaskStepStatus
    trace: TaskStepTraceLink


class TaskStepLifecycleSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    source: TaskLifecycleSource
    sequence_no: int
    kind: TaskStepKind
    final_status: TaskStepStatus
    trace: TaskStepTraceLink


class TaskStepSequenceRequestTracePayload(TypedDict):
    task_id: str
    previous_task_step_id: str
    previous_sequence_no: int
    previous_status: TaskStepStatus
    requested_kind: TaskStepKind
    requested_status: TaskStepStatus


class TaskStepSequenceStateTracePayload(TypedDict):
    task_id: str
    previous_task_step_id: str
    previous_sequence_no: int
    previous_status: TaskStepStatus
    task_step_id: str
    assigned_sequence_no: int
    kind: TaskStepKind
    current_status: TaskStepStatus


class TaskStepSequenceSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    latest_sequence_no: int
    next_sequence_no: int
    append_allowed: bool


class TaskStepContinuationRequestTracePayload(TypedDict):
    task_id: str
    parent_task_step_id: str
    parent_sequence_no: int
    parent_status: TaskStepStatus
    requested_kind: TaskStepKind
    requested_status: TaskStepStatus
    requested_source_approval_id: str | None
    requested_source_execution_id: str | None


class TaskStepContinuationLineageTracePayload(TypedDict):
    task_id: str
    parent_task_step_id: str
    parent_sequence_no: int
    parent_status: TaskStepStatus
    source_approval_id: str | None
    source_execution_id: str | None


class TaskStepContinuationSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    latest_sequence_no: int
    next_sequence_no: int
    append_allowed: bool
    lineage: TaskStepLineageRecord


class TaskStepTransitionRequestTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    sequence_no: int
    previous_status: TaskStepStatus
    requested_status: TaskStepStatus


class TaskStepTransitionStateTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    sequence_no: int
    previous_status: TaskStepStatus
    current_status: TaskStepStatus
    allowed_next_statuses: list[TaskStepStatus]
    trace: TaskStepTraceLink


class TaskStepTransitionSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    sequence_no: int
    final_status: TaskStepStatus
    parent_task_status: TaskStatus
    trace: TaskStepTraceLink

__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
