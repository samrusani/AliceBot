from __future__ import annotations

import json
from collections.abc import Callable as _Callable, Sequence
from datetime import datetime
from types import FunctionType as _FunctionType
from typing import Any, TypedDict, TypeVar as _TypeVar, cast
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from alicebot_api.db import UserConnection


_LegacyStoreMethodT = _TypeVar("_LegacyStoreMethodT", bound=_Callable[..., object])


def _clone_function_with_facade_globals(
    source: _FunctionType,
    *,
    qualname: str,
) -> _FunctionType:
    rebound = _FunctionType(
        source.__code__.replace(co_qualname=qualname),
        globals(),
        source.__name__,
        source.__defaults__,
        source.__closure__,
    )
    rebound.__kwdefaults__ = source.__kwdefaults__
    rebound.__dict__.update(source.__dict__)
    rebound.__doc__ = source.__doc__
    rebound.__module__ = __name__
    rebound.__qualname__ = qualname

    type_params = getattr(source, "__type_params__", None)
    if type_params is not None:
        setattr(rebound, "__type_params__", type_params)

    source_annotate = getattr(source, "__annotate__", None)
    if isinstance(source_annotate, _FunctionType):
        annotate_qualname = f"{qualname.rpartition('.')[0]}.__annotate__"
        rebound_annotate = _FunctionType(
            source_annotate.__code__.replace(co_qualname=annotate_qualname),
            globals(),
            source_annotate.__name__,
            source_annotate.__defaults__,
            source_annotate.__closure__,
        )
        rebound_annotate.__kwdefaults__ = source_annotate.__kwdefaults__
        rebound_annotate.__dict__.update(source_annotate.__dict__)
        rebound_annotate.__doc__ = source_annotate.__doc__
        rebound_annotate.__module__ = __name__
        rebound_annotate.__qualname__ = annotate_qualname
        setattr(rebound, "__annotate__", rebound_annotate)
    else:
        rebound.__annotations__ = source.__annotations__
    return rebound


def _bind_legacy_store_method(source: _LegacyStoreMethodT) -> _LegacyStoreMethodT:
    source_function = cast(_FunctionType, source)
    rebound = _clone_function_with_facade_globals(
        source_function,
        qualname=f"ContinuityStore.{source_function.__name__}",
    )
    return cast(_LegacyStoreMethodT, rebound)

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class UserRow(TypedDict):
    id: UUID
    email: str
    display_name: str | None
    created_at: datetime


class ThreadRow(TypedDict):
    id: UUID
    user_id: UUID
    title: str
    agent_profile_id: str
    created_at: datetime
    updated_at: datetime


class AgentProfileRow(TypedDict):
    id: str
    name: str
    description: str
    model_provider: str | None
    model_name: str | None


class SessionRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class EventRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    session_id: UUID | None
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: datetime


class TraceRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    kind: str
    compiler_version: str
    status: str
    limits: JsonObject
    created_at: datetime


class TraceEventRow(TypedDict):
    id: UUID
    user_id: UUID
    trace_id: UUID
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: datetime


class TraceReviewRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    kind: str
    compiler_version: str
    status: str
    limits: JsonObject
    created_at: datetime
    trace_event_count: int


class MemoryRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str
    memory_key: str
    value: JsonValue
    status: str
    source_event_ids: list[str]
    memory_type: str
    confidence: float | None
    salience: float | None
    confirmation_status: str
    trust_class: str
    promotion_eligibility: str
    evidence_count: int | None
    independent_source_count: int | None
    extracted_by_model: str | None
    trust_reason: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    last_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MemoryRevisionRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    sequence_no: int
    action: str
    memory_key: str
    previous_value: JsonValue | None
    new_value: JsonValue | None
    source_event_ids: list[str]
    candidate: JsonObject
    created_at: datetime


class FactPatternRow(TypedDict):
    id: UUID
    user_id: UUID
    pattern_key: str
    title: str
    memory_type: str
    namespace_key: str
    fact_count: int
    source_fact_ids: list[str]
    evidence_chain: JsonValue
    explanation: str
    created_at: datetime
    updated_at: datetime


class FactPlaybookRow(TypedDict):
    id: UUID
    user_id: UUID
    playbook_key: str
    pattern_id: UUID
    pattern_key: str
    title: str
    memory_type: str
    source_fact_ids: list[str]
    source_pattern_ids: list[str]
    steps: JsonValue
    explanation: str
    created_at: datetime
    updated_at: datetime


class MemoryReviewLabelRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    label: str
    note: str | None
    created_at: datetime


class OpenLoopRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID | None
    title: str
    status: str
    opened_at: datetime
    due_at: datetime | None
    resolved_at: datetime | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class ContinuityCaptureEventRow(TypedDict):
    id: UUID
    user_id: UUID
    raw_content: str
    explicit_signal: str | None
    admission_posture: str
    admission_reason: str
    created_at: datetime


class ContinuityObjectRow(TypedDict):
    id: UUID
    user_id: UUID
    capture_event_id: UUID
    object_type: str
    status: str
    is_preserved: bool
    is_searchable: bool
    is_promotable: bool
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    last_confirmed_at: datetime | None
    supersedes_object_id: UUID | None
    superseded_by_object_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ContinuityCorrectionEventRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    action: str
    reason: str | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    payload: JsonObject
    created_at: datetime


class ContradictionCaseRow(TypedDict):
    id: UUID
    user_id: UUID
    canonical_key: str
    continuity_object_id: UUID
    counterpart_object_id: UUID
    kind: str
    status: str
    rationale: str
    detection_payload: JsonObject
    resolution_action: str | None
    resolution_note: str | None
    continuity_object_updated_at: datetime
    counterpart_object_updated_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TrustSignalRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    signal_key: str
    signal_type: str
    signal_state: str
    direction: str
    magnitude: float
    reason: str
    contradiction_case_id: UUID | None
    related_continuity_object_id: UUID | None
    payload: JsonObject
    created_at: datetime
    updated_at: datetime


class MemoryOperationCandidateRow(TypedDict):
    id: UUID
    user_id: UUID
    sync_fingerprint: str
    source_kind: str
    source_candidate_id: str
    source_candidate_type: str
    candidate_payload: JsonObject
    source_scope: JsonObject
    operation_type: str
    operation_reason: str
    policy_action: str
    policy_reason: str
    target_continuity_object_id: UUID | None
    target_snapshot: JsonObject
    applied_operation_id: UUID | None
    created_at: datetime
    applied_at: datetime | None


class MemoryOperationRow(TypedDict):
    id: UUID
    user_id: UUID
    candidate_id: UUID
    operation_type: str
    status: str
    sync_fingerprint: str
    target_continuity_object_id: UUID | None
    resulting_continuity_object_id: UUID | None
    correction_event_id: UUID | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    details: JsonObject
    created_at: datetime


class ContinuityRecallCandidateRow(TypedDict):
    id: UUID
    user_id: UUID
    capture_event_id: UUID
    object_type: str
    status: str
    is_preserved: bool
    is_searchable: bool
    is_promotable: bool
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    last_confirmed_at: datetime | None
    supersedes_object_id: UUID | None
    superseded_by_object_id: UUID | None
    object_created_at: datetime
    object_updated_at: datetime
    admission_posture: str
    admission_reason: str
    explicit_signal: str | None
    capture_created_at: datetime


class ContinuityArtifactRow(TypedDict):
    id: UUID
    user_id: UUID
    source_kind: str
    import_source_path: str
    relative_path: str
    display_name: str
    media_type: str
    created_at: datetime


class ContinuityArtifactCopyRow(TypedDict):
    id: UUID
    user_id: UUID
    artifact_id: UUID
    checksum_sha256: str
    content_text: str
    content_length_bytes: int
    content_encoding: str
    created_at: datetime


class ContinuityArtifactSegmentRow(TypedDict):
    id: UUID
    user_id: UUID
    artifact_id: UUID
    artifact_copy_id: UUID
    source_item_id: str
    sequence_no: int
    segment_kind: str
    locator: JsonObject
    raw_content: str
    checksum_sha256: str
    created_at: datetime


class ContinuityObjectEvidenceLinkRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    artifact_id: UUID
    artifact_copy_id: UUID
    artifact_segment_id: UUID | None
    relationship: str
    created_at: datetime


class ContinuityObjectEvidenceRow(TypedDict):
    id: UUID
    user_id: UUID
    continuity_object_id: UUID
    artifact_id: UUID
    artifact_copy_id: UUID
    artifact_segment_id: UUID | None
    relationship: str
    created_at: datetime
    source_kind: str
    import_source_path: str
    relative_path: str
    display_name: str
    media_type: str
    artifact_created_at: datetime
    artifact_copy_checksum_sha256: str
    artifact_copy_content_text: str
    artifact_copy_content_length_bytes: int
    artifact_copy_content_encoding: str
    artifact_copy_created_at: datetime
    segment_source_item_id: str | None
    segment_sequence_no: int | None
    segment_kind: str | None
    segment_locator: JsonObject | None
    segment_raw_content: str | None
    segment_checksum_sha256: str | None
    segment_created_at: datetime | None


class EmbeddingConfigRow(TypedDict):
    id: UUID
    user_id: UUID
    provider: str
    model: str
    version: str
    dimensions: int
    status: str
    metadata: JsonObject
    created_at: datetime


class ModelProviderRow(TypedDict):
    id: UUID
    workspace_id: UUID
    created_by_user_account_id: UUID
    provider_key: str
    model_provider: str
    display_name: str
    base_url: str
    api_key: str
    auth_mode: str
    default_model: str
    status: str
    model_list_path: str
    healthcheck_path: str
    invoke_path: str
    azure_api_version: str
    azure_auth_secret_ref: str
    metadata: JsonObject
    config_revision: int
    config_fingerprint_sha256: str
    created_at: datetime
    updated_at: datetime


class ProviderCapabilityRow(TypedDict):
    id: UUID
    workspace_id: UUID
    provider_id: UUID
    discovered_by_user_account_id: UUID
    adapter_key: str
    discovery_status: str
    capability_snapshot: JsonObject
    discovery_error: str | None
    provider_config_revision: int
    provider_config_fingerprint_sha256: str
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime


class ProviderInvocationTelemetryRow(TypedDict):
    id: UUID
    workspace_id: UUID
    provider_id: UUID
    thread_id: UUID | None
    invoked_by_user_account_id: UUID
    invocation_kind: str
    adapter_key: str
    runtime_provider: str
    requested_model: str
    response_model: str | None
    response_id: str | None
    status: str
    latency_ms: int
    usage: JsonObject
    error_detail: str | None
    created_at: datetime


class MemoryEmbeddingRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    embedding_config_id: UUID
    dimensions: int
    vector: list[float]
    created_at: datetime
    updated_at: datetime


class SemanticMemoryRetrievalRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str
    memory_key: str
    value: JsonValue
    status: str
    source_event_ids: list[str]
    memory_type: str
    confidence: float | None
    salience: float | None
    confirmation_status: str
    trust_class: str
    promotion_eligibility: str
    evidence_count: int | None
    independent_source_count: int | None
    extracted_by_model: str | None
    trust_reason: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    last_confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    score: float


class EntityRow(TypedDict):
    id: UUID
    user_id: UUID
    entity_type: str
    name: str
    source_memory_ids: list[str]
    created_at: datetime


class EntityEdgeRow(TypedDict):
    id: UUID
    user_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    valid_from: datetime | None
    valid_to: datetime | None
    source_memory_ids: list[str]
    created_at: datetime


class RetrievalRunRow(TypedDict):
    id: UUID
    user_id: UUID
    source_surface: str
    ranking_strategy: str
    query_text: str | None
    request_scope: JsonObject
    result_ids: list[str]
    exclusion_summary: JsonObject
    candidate_count: int
    selected_count: int
    debug_enabled: bool
    retention_until: datetime
    created_at: datetime


class TaskBriefRow(TypedDict):
    id: UUID
    user_id: UUID
    mode: str
    query_text: str | None
    scope: JsonObject
    provider_strategy: str
    model_pack_strategy: str
    token_budget: int
    estimated_tokens: int
    item_count: int
    deterministic_key: str
    payload: JsonObject
    created_at: datetime


class EvalSuiteRow(TypedDict):
    id: UUID
    user_id: UUID
    suite_key: str
    title: str
    description: str
    evaluator_kind: str
    fixture_schema_version: str
    fixture_source_path: str
    case_count: int
    suite_order: int
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


class EvalCaseRow(TypedDict):
    id: UUID
    user_id: UUID
    suite_id: UUID
    case_key: str
    title: str
    evaluator_kind: str
    case_order: int
    fixture: JsonObject
    expectations: JsonObject
    created_at: datetime
    updated_at: datetime


class EvalRunRow(TypedDict):
    id: UUID
    user_id: UUID
    fixture_schema_version: str
    fixture_source_path: str
    requested_suite_keys: list[str]
    status: str
    summary: JsonObject
    report: JsonObject
    report_digest: str
    created_at: datetime


class EvalResultRow(TypedDict):
    id: UUID
    user_id: UUID
    eval_run_id: UUID
    suite_key: str
    case_key: str
    status: str
    score: float
    summary: JsonObject
    details: JsonObject
    created_at: datetime


class RetrievalCandidateRow(TypedDict):
    id: UUID
    user_id: UUID
    retrieval_run_id: UUID
    continuity_object_id: UUID
    rank: int | None
    selected: bool
    exclusion_reason: str | None
    lexical_score: float
    semantic_score: float
    entity_edge_score: float
    temporal_score: float
    trust_score: float
    relevance: float
    scope_matches: list[JsonObject]
    stage_details: JsonObject
    ordering: JsonObject
    title: str
    object_type: str
    status: str
    created_at: datetime


class ConsentRow(TypedDict):
    id: UUID
    user_id: UUID
    consent_key: str
    status: str
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


class PolicyRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str | None
    name: str
    action: str
    scope: str
    effect: str
    priority: int
    active: bool
    conditions: JsonObject
    required_consents: list[str]
    created_at: datetime
    updated_at: datetime


class ToolRow(TypedDict):
    id: UUID
    user_id: UUID
    tool_key: str
    name: str
    description: str
    version: str
    metadata_version: str
    active: bool
    tags: list[str]
    action_hints: list[str]
    scope_hints: list[str]
    domain_hints: list[str]
    risk_hints: list[str]
    metadata: JsonObject
    created_at: datetime


class ApprovalRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    task_run_id: UUID | None
    task_step_id: UUID | None
    status: str
    request: JsonObject
    tool: JsonObject
    routing: JsonObject
    routing_trace_id: UUID
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None


class TaskRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    status: str
    request: JsonObject
    tool: JsonObject
    latest_approval_id: UUID | None
    latest_execution_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TaskWorkspaceRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    status: str
    local_path: str
    created_at: datetime
    updated_at: datetime


class GmailAccountRow(TypedDict):
    id: UUID
    user_id: UUID
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: datetime
    updated_at: datetime


class CalendarAccountRow(TypedDict):
    id: UUID
    user_id: UUID
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: datetime
    updated_at: datetime


class ProtectedGmailCredentialRow(TypedDict):
    gmail_account_id: UUID
    user_id: UUID
    auth_kind: str
    credential_kind: str
    secret_manager_kind: str
    secret_ref: str | None
    credential_blob: JsonObject | None
    created_at: datetime
    updated_at: datetime


class ProtectedCalendarCredentialRow(TypedDict):
    calendar_account_id: UUID
    user_id: UUID
    auth_kind: str
    credential_kind: str
    secret_manager_kind: str
    secret_ref: str | None
    credential_blob: JsonObject | None
    created_at: datetime
    updated_at: datetime


class TaskArtifactRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    task_workspace_id: UUID
    status: str
    ingestion_status: str
    relative_path: str
    media_type_hint: str | None
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkRow(TypedDict):
    id: UUID
    user_id: UUID
    task_artifact_id: UUID
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkEmbeddingRow(TypedDict):
    id: UUID
    user_id: UUID
    task_artifact_id: UUID
    task_artifact_chunk_id: UUID
    task_artifact_chunk_sequence_no: int
    embedding_config_id: UUID
    dimensions: int
    vector: list[float]
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkSemanticRetrievalRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    task_artifact_id: UUID
    relative_path: str
    media_type_hint: str | None
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: datetime
    updated_at: datetime
    embedding_config_id: UUID
    score: float


class TaskStepRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    sequence_no: int
    parent_step_id: UUID | None
    source_approval_id: UUID | None
    source_execution_id: UUID | None
    kind: str
    status: str
    request: JsonObject
    outcome: JsonObject
    trace_id: UUID
    trace_kind: str
    created_at: datetime
    updated_at: datetime


class TaskRunRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    status: str
    checkpoint: JsonObject
    tick_count: int
    step_count: int
    max_ticks: int
    retry_count: int
    retry_cap: int
    retry_posture: str
    failure_class: str | None
    stop_reason: str | None
    last_transitioned_at: datetime
    created_at: datetime
    updated_at: datetime


class ToolExecutionRow(TypedDict):
    id: UUID
    user_id: UUID
    approval_id: UUID
    task_run_id: UUID | None
    task_step_id: UUID
    thread_id: UUID
    tool_id: UUID
    trace_id: UUID
    request_event_id: UUID | None
    result_event_id: UUID | None
    status: str
    handler_key: str | None
    idempotency_key: str | None
    request: JsonObject
    tool: JsonObject
    result: JsonObject
    executed_at: datetime


class ExecutionBudgetRow(TypedDict):
    id: UUID
    user_id: UUID
    agent_profile_id: str | None
    tool_key: str | None
    domain_hint: str | None
    max_completed_executions: int
    rolling_window_seconds: int | None
    status: str
    deactivated_at: datetime | None
    superseded_by_budget_id: UUID | None
    supersedes_budget_id: UUID | None
    created_at: datetime


class CountRow(TypedDict):
    count: int


class LabelCountRow(TypedDict):
    label: str
    count: int


from alicebot_api.legacy_store import conversation_memory as _conversation_memory
from alicebot_api.legacy_store.conversation_memory import (
    INSERT_USER_SQL as INSERT_USER_SQL,
    GET_USER_SQL as GET_USER_SQL,
    INSERT_THREAD_SQL as INSERT_THREAD_SQL,
    GET_THREAD_SQL as GET_THREAD_SQL,
    LIST_THREADS_SQL as LIST_THREADS_SQL,
    LIST_AGENT_PROFILES_SQL as LIST_AGENT_PROFILES_SQL,
    GET_AGENT_PROFILE_SQL as GET_AGENT_PROFILE_SQL,
    INSERT_SESSION_SQL as INSERT_SESSION_SQL,
    LIST_THREAD_SESSIONS_SQL as LIST_THREAD_SESSIONS_SQL,
    LOCK_THREAD_EVENTS_SQL as LOCK_THREAD_EVENTS_SQL,
)
from alicebot_api.legacy_store import task_execution as _task_execution
from alicebot_api.legacy_store.task_execution import (
    LOCK_TASK_STEPS_SQL as LOCK_TASK_STEPS_SQL,
    LOCK_TASK_WORKSPACES_SQL as LOCK_TASK_WORKSPACES_SQL,
    LOCK_TASK_ARTIFACTS_SQL as LOCK_TASK_ARTIFACTS_SQL,
    LOCK_TASK_RUNS_SQL as LOCK_TASK_RUNS_SQL,
)

from alicebot_api.legacy_store.conversation_memory import (
    INSERT_EVENT_SQL as INSERT_EVENT_SQL,
    LIST_THREAD_EVENTS_SQL as LIST_THREAD_EVENTS_SQL,
    GET_THREAD_EVENT_TAIL_SQL as GET_THREAD_EVENT_TAIL_SQL,
    LIST_EVENTS_BY_IDS_SQL as LIST_EVENTS_BY_IDS_SQL,
    INSERT_TRACE_SQL as INSERT_TRACE_SQL,
    GET_TRACE_SQL as GET_TRACE_SQL,
    LIST_TRACE_REVIEWS_SQL as LIST_TRACE_REVIEWS_SQL,
    GET_TRACE_REVIEW_SQL as GET_TRACE_REVIEW_SQL,
    INSERT_TRACE_EVENT_SQL as INSERT_TRACE_EVENT_SQL,
    LIST_TRACE_EVENTS_SQL as LIST_TRACE_EVENTS_SQL,
    INSERT_MEMORY_SQL as INSERT_MEMORY_SQL,
    GET_MEMORY_SQL as GET_MEMORY_SQL,
    LIST_MEMORIES_BY_IDS_SQL as LIST_MEMORIES_BY_IDS_SQL,
    GET_MEMORY_BY_KEY_SQL as GET_MEMORY_BY_KEY_SQL,
    GET_MEMORY_BY_KEY_AND_PROFILE_SQL as GET_MEMORY_BY_KEY_AND_PROFILE_SQL,
    LIST_MEMORIES_SQL as LIST_MEMORIES_SQL,
    COUNT_MEMORIES_SQL as COUNT_MEMORIES_SQL,
    COUNT_MEMORIES_BY_STATUS_SQL as COUNT_MEMORIES_BY_STATUS_SQL,
    COUNT_UNLABELED_REVIEW_MEMORIES_SQL as COUNT_UNLABELED_REVIEW_MEMORIES_SQL,
    LIST_REVIEW_MEMORIES_SQL as LIST_REVIEW_MEMORIES_SQL,
    LIST_REVIEW_MEMORIES_BY_STATUS_SQL as LIST_REVIEW_MEMORIES_BY_STATUS_SQL,
    LIST_UNLABELED_REVIEW_MEMORIES_SQL as LIST_UNLABELED_REVIEW_MEMORIES_SQL,
    LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL as LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL,
    LIST_CONTEXT_MEMORIES_SQL as LIST_CONTEXT_MEMORIES_SQL,
    LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL as LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL,
    UPDATE_MEMORY_SQL as UPDATE_MEMORY_SQL,
    LOCK_MEMORY_REVISIONS_SQL as LOCK_MEMORY_REVISIONS_SQL,
    INSERT_MEMORY_REVISION_SQL as INSERT_MEMORY_REVISION_SQL,
    LIST_MEMORY_REVISIONS_SQL as LIST_MEMORY_REVISIONS_SQL,
    COUNT_MEMORY_REVISIONS_SQL as COUNT_MEMORY_REVISIONS_SQL,
    LIST_LIMITED_MEMORY_REVISIONS_SQL as LIST_LIMITED_MEMORY_REVISIONS_SQL,
    UPSERT_FACT_PATTERN_SQL as UPSERT_FACT_PATTERN_SQL,
    LIST_FACT_PATTERNS_SQL as LIST_FACT_PATTERNS_SQL,
    COUNT_FACT_PATTERNS_SQL as COUNT_FACT_PATTERNS_SQL,
    GET_FACT_PATTERN_SQL as GET_FACT_PATTERN_SQL,
    DELETE_FACT_PATTERNS_NOT_IN_SQL as DELETE_FACT_PATTERNS_NOT_IN_SQL,
    DELETE_ALL_FACT_PATTERNS_SQL as DELETE_ALL_FACT_PATTERNS_SQL,
    UPSERT_FACT_PLAYBOOK_SQL as UPSERT_FACT_PLAYBOOK_SQL,
    LIST_FACT_PLAYBOOKS_SQL as LIST_FACT_PLAYBOOKS_SQL,
    COUNT_FACT_PLAYBOOKS_SQL as COUNT_FACT_PLAYBOOKS_SQL,
    GET_FACT_PLAYBOOK_SQL as GET_FACT_PLAYBOOK_SQL,
    DELETE_FACT_PLAYBOOKS_NOT_IN_SQL as DELETE_FACT_PLAYBOOKS_NOT_IN_SQL,
    DELETE_ALL_FACT_PLAYBOOKS_SQL as DELETE_ALL_FACT_PLAYBOOKS_SQL,
    INSERT_MEMORY_REVIEW_LABEL_SQL as INSERT_MEMORY_REVIEW_LABEL_SQL,
    LIST_MEMORY_REVIEW_LABELS_SQL as LIST_MEMORY_REVIEW_LABELS_SQL,
    LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL as LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL,
    COUNT_LABELED_MEMORIES_SQL as COUNT_LABELED_MEMORIES_SQL,
    COUNT_UNLABELED_MEMORIES_SQL as COUNT_UNLABELED_MEMORIES_SQL,
    LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL as LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL,
    LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL as LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL,
    INSERT_OPEN_LOOP_SQL as INSERT_OPEN_LOOP_SQL,
    GET_OPEN_LOOP_SQL as GET_OPEN_LOOP_SQL,
    LIST_OPEN_LOOPS_SQL as LIST_OPEN_LOOPS_SQL,
    LIST_OPEN_LOOPS_BY_STATUS_SQL as LIST_OPEN_LOOPS_BY_STATUS_SQL,
    LIST_LIMITED_OPEN_LOOPS_SQL as LIST_LIMITED_OPEN_LOOPS_SQL,
    LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL as LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL,
    COUNT_OPEN_LOOPS_SQL as COUNT_OPEN_LOOPS_SQL,
    COUNT_OPEN_LOOPS_BY_STATUS_SQL as COUNT_OPEN_LOOPS_BY_STATUS_SQL,
    UPDATE_OPEN_LOOP_STATUS_SQL as UPDATE_OPEN_LOOP_STATUS_SQL,
)

from alicebot_api.legacy_store import providers_knowledge as _providers_knowledge
from alicebot_api.legacy_store.providers_knowledge import (
    INSERT_MODEL_PROVIDER_SQL as INSERT_MODEL_PROVIDER_SQL,
    GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL as GET_MODEL_PROVIDER_FOR_WORKSPACE_SQL,
    LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL as LIST_MODEL_PROVIDERS_FOR_WORKSPACE_SQL,
    UPDATE_MODEL_PROVIDER_SQL as UPDATE_MODEL_PROVIDER_SQL,
    UPSERT_PROVIDER_CAPABILITY_IF_CURRENT_SQL as UPSERT_PROVIDER_CAPABILITY_IF_CURRENT_SQL,
    GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL as GET_PROVIDER_CAPABILITY_FOR_PROVIDER_SQL,
    IS_PROVIDER_SECRET_REFERENCE_IN_USE_SQL as IS_PROVIDER_SECRET_REFERENCE_IN_USE_SQL,
    INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL as INSERT_PROVIDER_INVOCATION_TELEMETRY_SQL,
    WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL as WORKSPACE_VISIBLE_TO_USER_ACCOUNT_SQL,
    INSERT_TASK_BRIEF_SQL as INSERT_TASK_BRIEF_SQL,
    GET_TASK_BRIEF_BY_ID_SQL as GET_TASK_BRIEF_BY_ID_SQL,
    INSERT_EMBEDDING_CONFIG_SQL as INSERT_EMBEDDING_CONFIG_SQL,
    GET_EMBEDDING_CONFIG_SQL as GET_EMBEDDING_CONFIG_SQL,
    GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL as GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL,
    LIST_EMBEDDING_CONFIGS_SQL as LIST_EMBEDDING_CONFIGS_SQL,
    INSERT_MEMORY_EMBEDDING_SQL as INSERT_MEMORY_EMBEDDING_SQL,
    GET_MEMORY_EMBEDDING_SQL as GET_MEMORY_EMBEDDING_SQL,
    GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL as GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL,
    LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL as LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL,
    LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL as LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL,
    UPDATE_MEMORY_EMBEDDING_SQL as UPDATE_MEMORY_EMBEDDING_SQL,
    RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL as RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL,
    RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL as RETRIEVE_SEMANTIC_MEMORY_MATCHES_FOR_PROFILE_SQL,
    RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL as RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
    RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL as RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
    INSERT_ENTITY_SQL as INSERT_ENTITY_SQL,
    GET_ENTITY_SQL as GET_ENTITY_SQL,
    LIST_ENTITIES_SQL as LIST_ENTITIES_SQL,
    INSERT_ENTITY_EDGE_SQL as INSERT_ENTITY_EDGE_SQL,
    LIST_ENTITY_EDGES_FOR_ENTITY_SQL as LIST_ENTITY_EDGES_FOR_ENTITY_SQL,
    LIST_ENTITY_EDGES_FOR_ENTITIES_SQL as LIST_ENTITY_EDGES_FOR_ENTITIES_SQL,
)

from alicebot_api.legacy_store import governance_integrations as _governance_integrations
from alicebot_api.legacy_store.governance_integrations import (
    INSERT_CONSENT_SQL as INSERT_CONSENT_SQL,
    GET_CONSENT_BY_KEY_SQL as GET_CONSENT_BY_KEY_SQL,
    LIST_CONSENTS_SQL as LIST_CONSENTS_SQL,
    UPDATE_CONSENT_SQL as UPDATE_CONSENT_SQL,
    INSERT_POLICY_SQL as INSERT_POLICY_SQL, GET_POLICY_SQL as GET_POLICY_SQL,
    LIST_POLICIES_SQL as LIST_POLICIES_SQL,
    LIST_ACTIVE_POLICIES_SQL as LIST_ACTIVE_POLICIES_SQL,
    LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL as LIST_ACTIVE_POLICIES_FOR_PROFILE_SQL,
    INSERT_TOOL_SQL as INSERT_TOOL_SQL, GET_TOOL_SQL as GET_TOOL_SQL,
    LIST_TOOLS_SQL as LIST_TOOLS_SQL,
    LIST_ACTIVE_TOOLS_SQL as LIST_ACTIVE_TOOLS_SQL,
    INSERT_APPROVAL_SQL as INSERT_APPROVAL_SQL, GET_APPROVAL_SQL as GET_APPROVAL_SQL,
    LIST_APPROVALS_SQL as LIST_APPROVALS_SQL,
    UPDATE_APPROVAL_RESOLUTION_SQL as UPDATE_APPROVAL_RESOLUTION_SQL,
    UPDATE_APPROVAL_TASK_STEP_SQL as UPDATE_APPROVAL_TASK_STEP_SQL,
    UPDATE_APPROVAL_TASK_RUN_SQL as UPDATE_APPROVAL_TASK_RUN_SQL,
    INSERT_TASK_SQL as INSERT_TASK_SQL, GET_TASK_SQL as GET_TASK_SQL,
    GET_TASK_BY_APPROVAL_SQL as GET_TASK_BY_APPROVAL_SQL, LIST_TASKS_SQL as LIST_TASKS_SQL,
    UPDATE_TASK_STATUS_BY_APPROVAL_SQL as UPDATE_TASK_STATUS_BY_APPROVAL_SQL,
    UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL as UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL,
    UPDATE_TASK_STATUS_SQL as UPDATE_TASK_STATUS_SQL,
    INSERT_GMAIL_ACCOUNT_SQL as INSERT_GMAIL_ACCOUNT_SQL,
    INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL as INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL,
    GET_GMAIL_ACCOUNT_SQL as GET_GMAIL_ACCOUNT_SQL,
    GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL as GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
    GET_GMAIL_ACCOUNT_CREDENTIAL_SQL as GET_GMAIL_ACCOUNT_CREDENTIAL_SQL,
    UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL as UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL,
    LIST_GMAIL_ACCOUNTS_SQL as LIST_GMAIL_ACCOUNTS_SQL,
    INSERT_CALENDAR_ACCOUNT_SQL as INSERT_CALENDAR_ACCOUNT_SQL,
    INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL as INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
    GET_CALENDAR_ACCOUNT_SQL as GET_CALENDAR_ACCOUNT_SQL,
    GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL as GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
    GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL as GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
    LIST_CALENDAR_ACCOUNTS_SQL as LIST_CALENDAR_ACCOUNTS_SQL,
)

from alicebot_api.legacy_store.task_execution import (
    INSERT_TASK_WORKSPACE_SQL as INSERT_TASK_WORKSPACE_SQL,
    GET_TASK_WORKSPACE_SQL as GET_TASK_WORKSPACE_SQL,
    GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL as GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL,
    LIST_TASK_WORKSPACES_SQL as LIST_TASK_WORKSPACES_SQL,
    INSERT_TASK_ARTIFACT_SQL as INSERT_TASK_ARTIFACT_SQL,
    GET_TASK_ARTIFACT_SQL as GET_TASK_ARTIFACT_SQL,
    GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL as GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL,
    LIST_TASK_ARTIFACTS_SQL as LIST_TASK_ARTIFACTS_SQL,
    LIST_TASK_ARTIFACTS_FOR_TASK_SQL as LIST_TASK_ARTIFACTS_FOR_TASK_SQL,
    LOCK_TASK_ARTIFACT_INGESTION_SQL as LOCK_TASK_ARTIFACT_INGESTION_SQL,
    INSERT_TASK_ARTIFACT_CHUNK_SQL as INSERT_TASK_ARTIFACT_CHUNK_SQL,
    LIST_TASK_ARTIFACT_CHUNKS_SQL as LIST_TASK_ARTIFACT_CHUNKS_SQL,
    GET_TASK_ARTIFACT_CHUNK_SQL as GET_TASK_ARTIFACT_CHUNK_SQL,
    INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL as INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
    GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL as GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
    GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL as GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL,
    LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL as LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL,
    LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL as LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL,
    UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL as UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
    UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL as UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL,
    INSERT_TASK_STEP_SQL as INSERT_TASK_STEP_SQL,
    GET_TASK_STEP_SQL as GET_TASK_STEP_SQL,
    GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL as GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL,
    LIST_TASK_STEPS_FOR_TASK_SQL as LIST_TASK_STEPS_FOR_TASK_SQL,
    UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL as UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL,
    UPDATE_TASK_STEP_SQL as UPDATE_TASK_STEP_SQL,
    INSERT_TASK_RUN_SQL as INSERT_TASK_RUN_SQL,
    GET_TASK_RUN_SQL as GET_TASK_RUN_SQL,
    LIST_TASK_RUNS_FOR_TASK_SQL as LIST_TASK_RUNS_FOR_TASK_SQL,
    UPDATE_TASK_RUN_SQL as UPDATE_TASK_RUN_SQL,
    ACQUIRE_NEXT_TASK_RUN_SQL as ACQUIRE_NEXT_TASK_RUN_SQL,
    INSERT_TOOL_EXECUTION_SQL as INSERT_TOOL_EXECUTION_SQL,
    GET_TOOL_EXECUTION_SQL as GET_TOOL_EXECUTION_SQL,
    LIST_TOOL_EXECUTIONS_SQL as LIST_TOOL_EXECUTIONS_SQL,
    GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL as GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL,
    INSERT_EXECUTION_BUDGET_SQL as INSERT_EXECUTION_BUDGET_SQL,
    GET_EXECUTION_BUDGET_SQL as GET_EXECUTION_BUDGET_SQL,
    LIST_EXECUTION_BUDGETS_SQL as LIST_EXECUTION_BUDGETS_SQL,
    DEACTIVATE_EXECUTION_BUDGET_SQL as DEACTIVATE_EXECUTION_BUDGET_SQL,
    SUPERSEDE_EXECUTION_BUDGET_SQL as SUPERSEDE_EXECUTION_BUDGET_SQL,
)

from alicebot_api.legacy_store import continuity as _continuity
from alicebot_api.legacy_store.continuity import (
    INSERT_CONTINUITY_CAPTURE_EVENT_SQL as INSERT_CONTINUITY_CAPTURE_EVENT_SQL,
    GET_CONTINUITY_CAPTURE_EVENT_SQL as GET_CONTINUITY_CAPTURE_EVENT_SQL,
    LIST_CONTINUITY_CAPTURE_EVENTS_SQL as LIST_CONTINUITY_CAPTURE_EVENTS_SQL,
    COUNT_CONTINUITY_CAPTURE_EVENTS_SQL as COUNT_CONTINUITY_CAPTURE_EVENTS_SQL,
    INSERT_CONTINUITY_OBJECT_SQL as INSERT_CONTINUITY_OBJECT_SQL,
    GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL as GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL,
    GET_CONTINUITY_OBJECT_SQL as GET_CONTINUITY_OBJECT_SQL,
    GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL as GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL,
    LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL as LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL,
    LIST_CONTINUITY_REVIEW_QUEUE_SQL as LIST_CONTINUITY_REVIEW_QUEUE_SQL,
    COUNT_CONTINUITY_REVIEW_QUEUE_SQL as COUNT_CONTINUITY_REVIEW_QUEUE_SQL,
    LIST_CONTINUITY_RECALL_CANDIDATES_SQL as LIST_CONTINUITY_RECALL_CANDIDATES_SQL,
    INSERT_RETRIEVAL_RUN_SQL as INSERT_RETRIEVAL_RUN_SQL,
    LIST_RETRIEVAL_RUNS_SQL as LIST_RETRIEVAL_RUNS_SQL,
    GET_RETRIEVAL_RUN_SQL as GET_RETRIEVAL_RUN_SQL,
    UPSERT_EVAL_SUITE_SQL as UPSERT_EVAL_SUITE_SQL,
    LIST_EVAL_SUITES_SQL as LIST_EVAL_SUITES_SQL,
    DELETE_EVAL_SUITES_NOT_IN_SQL as DELETE_EVAL_SUITES_NOT_IN_SQL,
    UPSERT_EVAL_CASE_SQL as UPSERT_EVAL_CASE_SQL,
    LIST_EVAL_CASES_FOR_SUITE_SQL as LIST_EVAL_CASES_FOR_SUITE_SQL,
    DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL as DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL,
    INSERT_EVAL_RUN_SQL as INSERT_EVAL_RUN_SQL,
    LIST_EVAL_RUNS_SQL as LIST_EVAL_RUNS_SQL,
    GET_EVAL_RUN_SQL as GET_EVAL_RUN_SQL,
    INSERT_EVAL_RESULT_SQL as INSERT_EVAL_RESULT_SQL,
    LIST_EVAL_RESULTS_FOR_RUN_SQL as LIST_EVAL_RESULTS_FOR_RUN_SQL,
    INSERT_RETRIEVAL_CANDIDATE_SQL as INSERT_RETRIEVAL_CANDIDATE_SQL,
    LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL as LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL,
    UPSERT_CONTINUITY_ARTIFACT_SQL as UPSERT_CONTINUITY_ARTIFACT_SQL,
    GET_CONTINUITY_ARTIFACT_SQL as GET_CONTINUITY_ARTIFACT_SQL,
    GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL as GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL,
    UPSERT_CONTINUITY_ARTIFACT_COPY_SQL as UPSERT_CONTINUITY_ARTIFACT_COPY_SQL,
    GET_CONTINUITY_ARTIFACT_COPY_SQL as GET_CONTINUITY_ARTIFACT_COPY_SQL,
    GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL as GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL,
    LIST_CONTINUITY_ARTIFACT_COPIES_SQL as LIST_CONTINUITY_ARTIFACT_COPIES_SQL,
    UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL as UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL,
    GET_CONTINUITY_ARTIFACT_SEGMENT_SQL as GET_CONTINUITY_ARTIFACT_SEGMENT_SQL,
    GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL as GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL,
    LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL as LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL,
    INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL as INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL,
    LIST_CONTINUITY_OBJECT_EVIDENCE_SQL as LIST_CONTINUITY_OBJECT_EVIDENCE_SQL,
    UPDATE_CONTINUITY_OBJECT_SQL as UPDATE_CONTINUITY_OBJECT_SQL,
    INSERT_CONTINUITY_CORRECTION_EVENT_SQL as INSERT_CONTINUITY_CORRECTION_EVENT_SQL,
    LIST_CONTINUITY_CORRECTION_EVENTS_SQL as LIST_CONTINUITY_CORRECTION_EVENTS_SQL,
    INSERT_CONTRADICTION_CASE_SQL as INSERT_CONTRADICTION_CASE_SQL,
    UPDATE_CONTRADICTION_CASE_SQL as UPDATE_CONTRADICTION_CASE_SQL,
    GET_CONTRADICTION_CASE_SQL as GET_CONTRADICTION_CASE_SQL,
    GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL as GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL,
    LIST_CONTRADICTION_CASES_SQL as LIST_CONTRADICTION_CASES_SQL,
    COUNT_CONTRADICTION_CASES_SQL as COUNT_CONTRADICTION_CASES_SQL,
    LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL as LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL,
    UPSERT_TRUST_SIGNAL_SQL as UPSERT_TRUST_SIGNAL_SQL,
    LIST_TRUST_SIGNALS_SQL as LIST_TRUST_SIGNALS_SQL,
    COUNT_TRUST_SIGNALS_SQL as COUNT_TRUST_SIGNALS_SQL,
    INSERT_MEMORY_OPERATION_CANDIDATE_SQL as INSERT_MEMORY_OPERATION_CANDIDATE_SQL,
    GET_MEMORY_OPERATION_CANDIDATE_SQL as GET_MEMORY_OPERATION_CANDIDATE_SQL,
    GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL as GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL,
    LIST_MEMORY_OPERATION_CANDIDATES_SQL as LIST_MEMORY_OPERATION_CANDIDATES_SQL,
    COUNT_MEMORY_OPERATION_CANDIDATES_SQL as COUNT_MEMORY_OPERATION_CANDIDATES_SQL,
    UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL as UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL,
    INSERT_MEMORY_OPERATION_SQL as INSERT_MEMORY_OPERATION_SQL,
    GET_MEMORY_OPERATION_SQL as GET_MEMORY_OPERATION_SQL,
    LIST_MEMORY_OPERATIONS_SQL as LIST_MEMORY_OPERATIONS_SQL,
    COUNT_MEMORY_OPERATIONS_SQL as COUNT_MEMORY_OPERATIONS_SQL,
)

from alicebot_api.legacy_store.conversation_memory import (
    UPDATE_EVENT_ERROR as UPDATE_EVENT_ERROR,
    DELETE_EVENT_ERROR as DELETE_EVENT_ERROR,
    UPDATE_TRACE_EVENT_ERROR as UPDATE_TRACE_EVENT_ERROR,
    DELETE_TRACE_EVENT_ERROR as DELETE_TRACE_EVENT_ERROR,
)


class AppendOnlyViolation(RuntimeError):
    """Raised when a caller attempts to mutate an immutable event."""

setattr(_conversation_memory, "AppendOnlyViolation", AppendOnlyViolation)


class ContinuityStoreInvariantError(RuntimeError):
    """Raised when a write query does not return the row its contract promises."""


setattr(_continuity, "ContinuityStoreInvariantError", ContinuityStoreInvariantError)


class ContinuityStore:
    def __init__(self, conn: UserConnection):
        self.conn = conn

    @staticmethod
    def _default_continuity_searchable(object_type: str) -> bool:
        return object_type != "Note"

    @staticmethod
    def _default_continuity_promotable(object_type: str) -> bool:
        return object_type in {"Decision", "Commitment", "WaitingFor", "Blocker", "NextAction"}

    def _acquire_advisory_lock(self, lock_query: str, lock_key: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(lock_query, (str(lock_key),))

    def _fetch_one(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> Any:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )

        return row

    def _fetch_one_with_lock(
        self,
        *,
        operation_name: str,
        lock_query: str,
        lock_key: UUID,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> Any:
        with self.conn.cursor() as cur:
            cur.execute(lock_query, (str(lock_key),))
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )

        return row

    def _fetch_all(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> list[Any]:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> Any | None:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        return row

    def _fetch_count(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                "count query did not return a row from the database",
            )

        return cast(CountRow, row)["count"]

    def _execute(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> None:
        del operation_name
        with self.conn.cursor() as cur:
            cur.execute(query, params)

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(repr(value) for value in vector) + "]"

    create_user = _bind_legacy_store_method(_conversation_memory.create_user)
    get_user = _bind_legacy_store_method(_conversation_memory.get_user)
    create_thread = _bind_legacy_store_method(_conversation_memory.create_thread)
    get_thread = _bind_legacy_store_method(_conversation_memory.get_thread)
    get_thread_optional = _bind_legacy_store_method(_conversation_memory.get_thread_optional)
    list_threads = _bind_legacy_store_method(_conversation_memory.list_threads)
    list_agent_profiles = _bind_legacy_store_method(_conversation_memory.list_agent_profiles)
    get_agent_profile_optional = _bind_legacy_store_method(_conversation_memory.get_agent_profile_optional)
    create_session = _bind_legacy_store_method(_conversation_memory.create_session)
    list_thread_sessions = _bind_legacy_store_method(_conversation_memory.list_thread_sessions)
    append_event = _bind_legacy_store_method(_conversation_memory.append_event)
    append_event_if_tail = _bind_legacy_store_method(_conversation_memory.append_event_if_tail)
    list_thread_events = _bind_legacy_store_method(_conversation_memory.list_thread_events)
    list_events_by_ids = _bind_legacy_store_method(_conversation_memory.list_events_by_ids)
    create_trace = _bind_legacy_store_method(_conversation_memory.create_trace)
    get_trace = _bind_legacy_store_method(_conversation_memory.get_trace)
    get_trace_review_optional = _bind_legacy_store_method(_conversation_memory.get_trace_review_optional)
    list_trace_reviews = _bind_legacy_store_method(_conversation_memory.list_trace_reviews)
    append_trace_event = _bind_legacy_store_method(_conversation_memory.append_trace_event)
    list_trace_events = _bind_legacy_store_method(_conversation_memory.list_trace_events)
    create_memory = _bind_legacy_store_method(_conversation_memory.create_memory)
    get_memory = _bind_legacy_store_method(_conversation_memory.get_memory)
    get_memory_optional = _bind_legacy_store_method(_conversation_memory.get_memory_optional)
    list_memories_by_ids = _bind_legacy_store_method(_conversation_memory.list_memories_by_ids)
    get_memory_by_key = _bind_legacy_store_method(_conversation_memory.get_memory_by_key)
    get_memory_by_key_and_profile = _bind_legacy_store_method(_conversation_memory.get_memory_by_key_and_profile)
    list_memories = _bind_legacy_store_method(_conversation_memory.list_memories)
    count_memories = _bind_legacy_store_method(_conversation_memory.count_memories)
    count_unlabeled_review_memories = _bind_legacy_store_method(_conversation_memory.count_unlabeled_review_memories)
    list_review_memories = _bind_legacy_store_method(_conversation_memory.list_review_memories)
    list_unlabeled_review_memories = _bind_legacy_store_method(_conversation_memory.list_unlabeled_review_memories)
    list_context_memories = _bind_legacy_store_method(_conversation_memory.list_context_memories)
    list_context_memories_for_profile = _bind_legacy_store_method(_conversation_memory.list_context_memories_for_profile)
    update_memory = _bind_legacy_store_method(_conversation_memory.update_memory)
    append_memory_revision = _bind_legacy_store_method(_conversation_memory.append_memory_revision)
    count_memory_revisions = _bind_legacy_store_method(_conversation_memory.count_memory_revisions)
    list_memory_revisions = _bind_legacy_store_method(_conversation_memory.list_memory_revisions)
    upsert_fact_pattern = _bind_legacy_store_method(_conversation_memory.upsert_fact_pattern)
    list_fact_patterns = _bind_legacy_store_method(_conversation_memory.list_fact_patterns)
    count_fact_patterns = _bind_legacy_store_method(_conversation_memory.count_fact_patterns)
    get_fact_pattern_optional = _bind_legacy_store_method(_conversation_memory.get_fact_pattern_optional)
    delete_fact_patterns_not_in = _bind_legacy_store_method(_conversation_memory.delete_fact_patterns_not_in)
    upsert_fact_playbook = _bind_legacy_store_method(_conversation_memory.upsert_fact_playbook)
    list_fact_playbooks = _bind_legacy_store_method(_conversation_memory.list_fact_playbooks)
    count_fact_playbooks = _bind_legacy_store_method(_conversation_memory.count_fact_playbooks)
    get_fact_playbook_optional = _bind_legacy_store_method(_conversation_memory.get_fact_playbook_optional)
    delete_fact_playbooks_not_in = _bind_legacy_store_method(_conversation_memory.delete_fact_playbooks_not_in)
    create_memory_review_label = _bind_legacy_store_method(_conversation_memory.create_memory_review_label)
    list_memory_review_labels = _bind_legacy_store_method(_conversation_memory.list_memory_review_labels)
    list_memory_review_label_counts = _bind_legacy_store_method(_conversation_memory.list_memory_review_label_counts)
    count_labeled_memories = _bind_legacy_store_method(_conversation_memory.count_labeled_memories)
    count_unlabeled_memories = _bind_legacy_store_method(_conversation_memory.count_unlabeled_memories)
    list_all_memory_review_label_counts = _bind_legacy_store_method(_conversation_memory.list_all_memory_review_label_counts)
    list_active_memory_review_label_counts = _bind_legacy_store_method(_conversation_memory.list_active_memory_review_label_counts)
    create_open_loop = _bind_legacy_store_method(_conversation_memory.create_open_loop)
    get_open_loop = _bind_legacy_store_method(_conversation_memory.get_open_loop)
    get_open_loop_optional = _bind_legacy_store_method(_conversation_memory.get_open_loop_optional)
    list_open_loops = _bind_legacy_store_method(_conversation_memory.list_open_loops)
    count_open_loops = _bind_legacy_store_method(_conversation_memory.count_open_loops)
    update_open_loop_status_optional = _bind_legacy_store_method(_conversation_memory.update_open_loop_status_optional)

    create_continuity_capture_event = _bind_legacy_store_method(_continuity.create_continuity_capture_event)

    get_continuity_capture_event_optional = _bind_legacy_store_method(_continuity.get_continuity_capture_event_optional)

    list_continuity_capture_events = _bind_legacy_store_method(_continuity.list_continuity_capture_events)

    count_continuity_capture_events = _bind_legacy_store_method(_continuity.count_continuity_capture_events)

    create_continuity_object = _bind_legacy_store_method(_continuity.create_continuity_object)

    get_continuity_object_by_capture_event_optional = _bind_legacy_store_method(_continuity.get_continuity_object_by_capture_event_optional)

    list_continuity_objects_for_capture_events = _bind_legacy_store_method(_continuity.list_continuity_objects_for_capture_events)

    get_continuity_object_optional = _bind_legacy_store_method(_continuity.get_continuity_object_optional)

    get_continuity_object_by_commit_fingerprint_optional = _bind_legacy_store_method(_continuity.get_continuity_object_by_commit_fingerprint_optional)

    list_continuity_review_queue = _bind_legacy_store_method(_continuity.list_continuity_review_queue)

    count_continuity_review_queue = _bind_legacy_store_method(_continuity.count_continuity_review_queue)

    list_continuity_recall_candidates = _bind_legacy_store_method(_continuity.list_continuity_recall_candidates)

    upsert_eval_suite = _bind_legacy_store_method(_continuity.upsert_eval_suite)

    list_eval_suites = _bind_legacy_store_method(_continuity.list_eval_suites)

    delete_eval_suites_not_in = _bind_legacy_store_method(_continuity.delete_eval_suites_not_in)

    upsert_eval_case = _bind_legacy_store_method(_continuity.upsert_eval_case)

    list_eval_cases_for_suite = _bind_legacy_store_method(_continuity.list_eval_cases_for_suite)

    delete_eval_cases_for_suite_not_in = _bind_legacy_store_method(_continuity.delete_eval_cases_for_suite_not_in)

    create_eval_run = _bind_legacy_store_method(_continuity.create_eval_run)

    list_eval_runs = _bind_legacy_store_method(_continuity.list_eval_runs)

    get_eval_run_optional = _bind_legacy_store_method(_continuity.get_eval_run_optional)

    create_eval_result = _bind_legacy_store_method(_continuity.create_eval_result)

    list_eval_results_for_run = _bind_legacy_store_method(_continuity.list_eval_results_for_run)

    create_retrieval_run = _bind_legacy_store_method(_continuity.create_retrieval_run)

    list_retrieval_runs = _bind_legacy_store_method(_continuity.list_retrieval_runs)

    get_retrieval_run_optional = _bind_legacy_store_method(_continuity.get_retrieval_run_optional)

    create_retrieval_candidate = _bind_legacy_store_method(_continuity.create_retrieval_candidate)

    list_retrieval_candidates_for_run = _bind_legacy_store_method(_continuity.list_retrieval_candidates_for_run)

    upsert_continuity_artifact = _bind_legacy_store_method(_continuity.upsert_continuity_artifact)

    get_continuity_artifact_optional = _bind_legacy_store_method(_continuity.get_continuity_artifact_optional)

    upsert_continuity_artifact_copy = _bind_legacy_store_method(_continuity.upsert_continuity_artifact_copy)

    get_continuity_artifact_copy_optional = _bind_legacy_store_method(_continuity.get_continuity_artifact_copy_optional)

    list_continuity_artifact_copies = _bind_legacy_store_method(_continuity.list_continuity_artifact_copies)

    upsert_continuity_artifact_segment = _bind_legacy_store_method(_continuity.upsert_continuity_artifact_segment)

    get_continuity_artifact_segment_optional = _bind_legacy_store_method(_continuity.get_continuity_artifact_segment_optional)

    list_continuity_artifact_segments = _bind_legacy_store_method(_continuity.list_continuity_artifact_segments)

    create_continuity_object_evidence_link = _bind_legacy_store_method(_continuity.create_continuity_object_evidence_link)

    list_continuity_object_evidence = _bind_legacy_store_method(_continuity.list_continuity_object_evidence)

    update_continuity_object_optional = _bind_legacy_store_method(_continuity.update_continuity_object_optional)

    create_continuity_correction_event = _bind_legacy_store_method(_continuity.create_continuity_correction_event)

    list_continuity_correction_events = _bind_legacy_store_method(_continuity.list_continuity_correction_events)

    create_contradiction_case = _bind_legacy_store_method(_continuity.create_contradiction_case)

    update_contradiction_case_optional = _bind_legacy_store_method(_continuity.update_contradiction_case_optional)

    get_contradiction_case_optional = _bind_legacy_store_method(_continuity.get_contradiction_case_optional)

    get_contradiction_case_by_canonical_key_optional = _bind_legacy_store_method(_continuity.get_contradiction_case_by_canonical_key_optional)

    list_contradiction_cases = _bind_legacy_store_method(_continuity.list_contradiction_cases)

    count_contradiction_cases = _bind_legacy_store_method(_continuity.count_contradiction_cases)

    list_contradiction_cases_for_objects = _bind_legacy_store_method(_continuity.list_contradiction_cases_for_objects)

    upsert_trust_signal = _bind_legacy_store_method(_continuity.upsert_trust_signal)

    list_trust_signals = _bind_legacy_store_method(_continuity.list_trust_signals)

    count_trust_signals = _bind_legacy_store_method(_continuity.count_trust_signals)

    create_memory_operation_candidate = _bind_legacy_store_method(_continuity.create_memory_operation_candidate)

    get_memory_operation_candidate_optional = _bind_legacy_store_method(_continuity.get_memory_operation_candidate_optional)

    get_memory_operation_candidate_by_sync_source_optional = _bind_legacy_store_method(_continuity.get_memory_operation_candidate_by_sync_source_optional)

    list_memory_operation_candidates = _bind_legacy_store_method(_continuity.list_memory_operation_candidates)

    count_memory_operation_candidates = _bind_legacy_store_method(_continuity.count_memory_operation_candidates)

    update_memory_operation_candidate_application = _bind_legacy_store_method(_continuity.update_memory_operation_candidate_application)

    create_memory_operation = _bind_legacy_store_method(_continuity.create_memory_operation)

    get_memory_operation_optional = _bind_legacy_store_method(_continuity.get_memory_operation_optional)

    list_memory_operations = _bind_legacy_store_method(_continuity.list_memory_operations)

    count_memory_operations = _bind_legacy_store_method(_continuity.count_memory_operations)

    create_model_provider = _bind_legacy_store_method(_providers_knowledge.create_model_provider)

    get_model_provider_for_workspace_optional = _bind_legacy_store_method(_providers_knowledge.get_model_provider_for_workspace_optional)

    list_model_providers_for_workspace = _bind_legacy_store_method(_providers_knowledge.list_model_providers_for_workspace)

    update_model_provider = _bind_legacy_store_method(_providers_knowledge.update_model_provider)

    upsert_provider_capability_if_current = _bind_legacy_store_method(_providers_knowledge.upsert_provider_capability_if_current)

    get_provider_capability_for_provider_optional = _bind_legacy_store_method(_providers_knowledge.get_provider_capability_for_provider_optional)

    is_provider_secret_reference_in_use = _bind_legacy_store_method(_providers_knowledge.is_provider_secret_reference_in_use)

    record_provider_invocation_telemetry = _bind_legacy_store_method(_providers_knowledge.record_provider_invocation_telemetry)

    workspace_visible_to_user_account = _bind_legacy_store_method(_providers_knowledge.workspace_visible_to_user_account)

    create_task_brief = _bind_legacy_store_method(_providers_knowledge.create_task_brief)

    get_task_brief_optional = _bind_legacy_store_method(_providers_knowledge.get_task_brief_optional)

    create_embedding_config = _bind_legacy_store_method(_providers_knowledge.create_embedding_config)

    get_embedding_config_optional = _bind_legacy_store_method(_providers_knowledge.get_embedding_config_optional)

    get_embedding_config_by_identity_optional = _bind_legacy_store_method(_providers_knowledge.get_embedding_config_by_identity_optional)

    list_embedding_configs = _bind_legacy_store_method(_providers_knowledge.list_embedding_configs)

    create_memory_embedding = _bind_legacy_store_method(_providers_knowledge.create_memory_embedding)

    get_memory_embedding_optional = _bind_legacy_store_method(_providers_knowledge.get_memory_embedding_optional)

    get_memory_embedding_by_memory_and_config_optional = _bind_legacy_store_method(_providers_knowledge.get_memory_embedding_by_memory_and_config_optional)

    list_memory_embeddings_for_memory = _bind_legacy_store_method(_providers_knowledge.list_memory_embeddings_for_memory)

    list_memory_embeddings_for_config = _bind_legacy_store_method(_providers_knowledge.list_memory_embeddings_for_config)

    update_memory_embedding = _bind_legacy_store_method(_providers_knowledge.update_memory_embedding)

    retrieve_semantic_memory_matches = _bind_legacy_store_method(_providers_knowledge.retrieve_semantic_memory_matches)

    retrieve_semantic_memory_matches_for_profile = _bind_legacy_store_method(_providers_knowledge.retrieve_semantic_memory_matches_for_profile)

    retrieve_task_scoped_semantic_artifact_chunk_matches = _bind_legacy_store_method(_providers_knowledge.retrieve_task_scoped_semantic_artifact_chunk_matches)

    retrieve_artifact_scoped_semantic_artifact_chunk_matches = _bind_legacy_store_method(_providers_knowledge.retrieve_artifact_scoped_semantic_artifact_chunk_matches)

    create_entity = _bind_legacy_store_method(_providers_knowledge.create_entity)

    get_entity_optional = _bind_legacy_store_method(_providers_knowledge.get_entity_optional)

    list_entities = _bind_legacy_store_method(_providers_knowledge.list_entities)

    create_entity_edge = _bind_legacy_store_method(_providers_knowledge.create_entity_edge)

    list_entity_edges_for_entity = _bind_legacy_store_method(_providers_knowledge.list_entity_edges_for_entity)

    list_entity_edges_for_entities = _bind_legacy_store_method(_providers_knowledge.list_entity_edges_for_entities)

    create_consent = _bind_legacy_store_method(_governance_integrations.create_consent)
    get_consent_by_key_optional = _bind_legacy_store_method(_governance_integrations.get_consent_by_key_optional)
    list_consents = _bind_legacy_store_method(_governance_integrations.list_consents)
    update_consent = _bind_legacy_store_method(_governance_integrations.update_consent)
    create_policy = _bind_legacy_store_method(_governance_integrations.create_policy)
    get_policy_optional = _bind_legacy_store_method(_governance_integrations.get_policy_optional)
    list_policies = _bind_legacy_store_method(_governance_integrations.list_policies)
    list_active_policies = _bind_legacy_store_method(_governance_integrations.list_active_policies)
    create_tool = _bind_legacy_store_method(_governance_integrations.create_tool)
    get_tool_optional = _bind_legacy_store_method(_governance_integrations.get_tool_optional)
    list_tools = _bind_legacy_store_method(_governance_integrations.list_tools)
    list_active_tools = _bind_legacy_store_method(_governance_integrations.list_active_tools)
    create_approval = _bind_legacy_store_method(_governance_integrations.create_approval)
    get_approval_optional = _bind_legacy_store_method(_governance_integrations.get_approval_optional)
    list_approvals = _bind_legacy_store_method(_governance_integrations.list_approvals)
    resolve_approval_optional = _bind_legacy_store_method(_governance_integrations.resolve_approval_optional)
    update_approval_task_step_optional = _bind_legacy_store_method(_governance_integrations.update_approval_task_step_optional)
    update_approval_task_run_optional = _bind_legacy_store_method(_governance_integrations.update_approval_task_run_optional)
    create_task = _bind_legacy_store_method(_governance_integrations.create_task)
    get_task_optional = _bind_legacy_store_method(_governance_integrations.get_task_optional)
    get_task_by_approval_optional = _bind_legacy_store_method(_governance_integrations.get_task_by_approval_optional)
    list_tasks = _bind_legacy_store_method(_governance_integrations.list_tasks)
    update_task_status_by_approval_optional = _bind_legacy_store_method(_governance_integrations.update_task_status_by_approval_optional)
    update_task_execution_by_approval_optional = _bind_legacy_store_method(_governance_integrations.update_task_execution_by_approval_optional)
    update_task_status_optional = _bind_legacy_store_method(_governance_integrations.update_task_status_optional)
    create_gmail_account = _bind_legacy_store_method(_governance_integrations.create_gmail_account)
    create_gmail_account_credential = _bind_legacy_store_method(_governance_integrations.create_gmail_account_credential)
    get_gmail_account_optional = _bind_legacy_store_method(_governance_integrations.get_gmail_account_optional)
    get_gmail_account_credential_optional = _bind_legacy_store_method(_governance_integrations.get_gmail_account_credential_optional)
    update_gmail_account_credential = _bind_legacy_store_method(_governance_integrations.update_gmail_account_credential)
    get_gmail_account_by_provider_account_id_optional = _bind_legacy_store_method(_governance_integrations.get_gmail_account_by_provider_account_id_optional)
    list_gmail_accounts = _bind_legacy_store_method(_governance_integrations.list_gmail_accounts)
    create_calendar_account = _bind_legacy_store_method(_governance_integrations.create_calendar_account)
    create_calendar_account_credential = _bind_legacy_store_method(_governance_integrations.create_calendar_account_credential)
    get_calendar_account_optional = _bind_legacy_store_method(_governance_integrations.get_calendar_account_optional)
    get_calendar_account_credential_optional = _bind_legacy_store_method(_governance_integrations.get_calendar_account_credential_optional)
    get_calendar_account_by_provider_account_id_optional = _bind_legacy_store_method(_governance_integrations.get_calendar_account_by_provider_account_id_optional)
    list_calendar_accounts = _bind_legacy_store_method(_governance_integrations.list_calendar_accounts)

    lock_task_workspaces = _bind_legacy_store_method(_task_execution.lock_task_workspaces)
    create_task_workspace = _bind_legacy_store_method(_task_execution.create_task_workspace)
    get_task_workspace_optional = _bind_legacy_store_method(_task_execution.get_task_workspace_optional)
    get_active_task_workspace_for_task_optional = _bind_legacy_store_method(_task_execution.get_active_task_workspace_for_task_optional)
    list_task_workspaces = _bind_legacy_store_method(_task_execution.list_task_workspaces)
    lock_task_artifacts = _bind_legacy_store_method(_task_execution.lock_task_artifacts)
    create_task_artifact = _bind_legacy_store_method(_task_execution.create_task_artifact)
    get_task_artifact_optional = _bind_legacy_store_method(_task_execution.get_task_artifact_optional)
    get_task_artifact_by_workspace_relative_path_optional = _bind_legacy_store_method(_task_execution.get_task_artifact_by_workspace_relative_path_optional)
    list_task_artifacts = _bind_legacy_store_method(_task_execution.list_task_artifacts)
    list_task_artifacts_for_task = _bind_legacy_store_method(_task_execution.list_task_artifacts_for_task)
    lock_task_artifact_ingestion = _bind_legacy_store_method(_task_execution.lock_task_artifact_ingestion)
    create_task_artifact_chunk = _bind_legacy_store_method(_task_execution.create_task_artifact_chunk)
    get_task_artifact_chunk_optional = _bind_legacy_store_method(_task_execution.get_task_artifact_chunk_optional)
    list_task_artifact_chunks = _bind_legacy_store_method(_task_execution.list_task_artifact_chunks)
    create_task_artifact_chunk_embedding = _bind_legacy_store_method(_task_execution.create_task_artifact_chunk_embedding)
    get_task_artifact_chunk_embedding_optional = _bind_legacy_store_method(_task_execution.get_task_artifact_chunk_embedding_optional)
    get_task_artifact_chunk_embedding_by_chunk_and_config_optional = _bind_legacy_store_method(_task_execution.get_task_artifact_chunk_embedding_by_chunk_and_config_optional)
    list_task_artifact_chunk_embeddings_for_chunk = _bind_legacy_store_method(_task_execution.list_task_artifact_chunk_embeddings_for_chunk)
    list_task_artifact_chunk_embeddings_for_artifact = _bind_legacy_store_method(_task_execution.list_task_artifact_chunk_embeddings_for_artifact)
    update_task_artifact_chunk_embedding = _bind_legacy_store_method(_task_execution.update_task_artifact_chunk_embedding)
    update_task_artifact_ingestion_status = _bind_legacy_store_method(_task_execution.update_task_artifact_ingestion_status)
    lock_task_steps = _bind_legacy_store_method(_task_execution.lock_task_steps)
    create_task_step = _bind_legacy_store_method(_task_execution.create_task_step)
    get_task_step_optional = _bind_legacy_store_method(_task_execution.get_task_step_optional)
    get_task_step_for_task_sequence_optional = _bind_legacy_store_method(_task_execution.get_task_step_for_task_sequence_optional)
    list_task_steps_for_task = _bind_legacy_store_method(_task_execution.list_task_steps_for_task)
    update_task_step_for_task_sequence_optional = _bind_legacy_store_method(_task_execution.update_task_step_for_task_sequence_optional)
    update_task_step_optional = _bind_legacy_store_method(_task_execution.update_task_step_optional)
    lock_task_runs = _bind_legacy_store_method(_task_execution.lock_task_runs)
    create_task_run = _bind_legacy_store_method(_task_execution.create_task_run)
    get_task_run_optional = _bind_legacy_store_method(_task_execution.get_task_run_optional)
    list_task_runs_for_task = _bind_legacy_store_method(_task_execution.list_task_runs_for_task)
    update_task_run_optional = _bind_legacy_store_method(_task_execution.update_task_run_optional)
    acquire_next_task_run_optional = _bind_legacy_store_method(_task_execution.acquire_next_task_run_optional)
    create_tool_execution = _bind_legacy_store_method(_task_execution.create_tool_execution)
    get_tool_execution_optional = _bind_legacy_store_method(_task_execution.get_tool_execution_optional)
    list_tool_executions = _bind_legacy_store_method(_task_execution.list_tool_executions)
    get_tool_execution_by_idempotency_optional = _bind_legacy_store_method(_task_execution.get_tool_execution_by_idempotency_optional)
    create_execution_budget = _bind_legacy_store_method(_task_execution.create_execution_budget)
    get_execution_budget_optional = _bind_legacy_store_method(_task_execution.get_execution_budget_optional)
    list_execution_budgets = _bind_legacy_store_method(_task_execution.list_execution_budgets)
    deactivate_execution_budget_optional = _bind_legacy_store_method(_task_execution.deactivate_execution_budget_optional)
    supersede_execution_budget_optional = _bind_legacy_store_method(_task_execution.supersede_execution_budget_optional)

    update_event = _bind_legacy_store_method(_conversation_memory.update_event)
    delete_event = _bind_legacy_store_method(_conversation_memory.delete_event)
    update_trace_event = _bind_legacy_store_method(_conversation_memory.update_trace_event)
    delete_trace_event = _bind_legacy_store_method(_conversation_memory.delete_trace_event)
