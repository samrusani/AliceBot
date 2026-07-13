"""Per-operation OpenAPI success response schemas.

This registry deliberately uses literal ``(METHOD, path)`` keys so route coverage can
be checked without executing the application. Schemas that are not yet backed by a
TypedDict remain open, but still expose operation-specific top-level fields instead
of falling back to a domain-wide catch-all component.
"""

from __future__ import annotations


def _typed_properties(
    *,
    objects: tuple[str, ...] = (),
    nullable_objects: tuple[str, ...] = (),
    object_arrays: tuple[str, ...] = (),
    string_arrays: tuple[str, ...] = (),
    strings: tuple[str, ...] = (),
    nullable_strings: tuple[str, ...] = (),
    integers: tuple[str, ...] = (),
    booleans: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    """Build an explicitly classified per-operation property map."""

    properties: dict[str, dict[str, object]] = {}
    for field in objects:
        properties[field] = {"type": "object", "additionalProperties": True}
    for field in nullable_objects:
        properties[field] = {
            "anyOf": [
                {"type": "object", "additionalProperties": True},
                {"type": "null"},
            ]
        }
    for field in object_arrays:
        properties[field] = {
            "type": "array",
            "items": {"type": "object", "additionalProperties": True},
        }
    for field in string_arrays:
        properties[field] = {"type": "array", "items": {"type": "string"}}
    for field in strings:
        properties[field] = {"type": "string"}
    for field in nullable_strings:
        properties[field] = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    for field in integers:
        properties[field] = {"type": "integer"}
    for field in booleans:
        properties[field] = {"type": "boolean"}
    classified_count = sum(
        len(fields)
        for fields in (
            objects,
            nullable_objects,
            object_arrays,
            string_arrays,
            strings,
            nullable_strings,
            integers,
            booleans,
        )
    )
    if len(properties) != classified_count:
        raise RuntimeError("OpenAPI property was assigned more than one JSON type")
    return properties


_ARTIFACT_RESPONSE_FIELDS = (
    "artifact_type",
    "content_markdown",
    "created_at",
    "domain",
    "generated_by",
    "id",
    "metadata_json",
    "model_info_json",
    "prompt_hash",
    "promoted_at",
    "reviewed_at",
    "sensitivity",
    "status",
    "title",
    "user_id",
)


def _artifact_response_properties() -> dict[str, dict[str, object]]:
    """Describe the artifact object returned directly by generator handlers."""

    properties = _typed_properties(
        objects=("metadata_json", "model_info_json"),
        strings=(
            "artifact_type",
            "content_markdown",
            "domain",
            "generated_by",
            "sensitivity",
            "status",
            "title",
        ),
        nullable_strings=("prompt_hash",),
    )
    properties.update(
        {
            "id": {"type": "string", "format": "uuid"},
            "user_id": {"type": "string", "format": "uuid"},
            "created_at": {"type": "string", "format": "date-time"},
            "reviewed_at": {
                "anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]
            },
            "promoted_at": {
                "anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]
            },
        }
    )
    return properties


def _operation_schema(
    title: str,
    fields: tuple[str, ...],
    *,
    required: tuple[str, ...] | None = None,
    closed: bool = False,
) -> dict[str, object]:
    schema: dict[str, object] = {
        "title": title,
        "type": "object",
        # Unverified fields stay unconstrained until a source-backed entry is
        # applied below. An empty JSON Schema is honest; claiming every unknown
        # scalar/array/null field is an object is not.
        "properties": {field: {} for field in fields},
        "additionalProperties": not closed,
    }
    if required is not None:
        schema["required"] = list(required)
    elif closed:
        schema["required"] = list(fields)
    return schema


OPENAPI_OPERATION_RESPONSE_SCHEMAS: dict[tuple[str, str], tuple[str, dict[str, object]]] = {
    ("GET", "/healthz"): (
        "HealthcheckSuccessResponse",
        _operation_schema(
            "HealthcheckSuccessResponse",
            (
                "status",
                "environment",
                "services",
            ),
            closed=True,
        ),
    ),
    ("POST", "/v0/context/compile"): (
        "CompileContextSuccessResponse",
        _operation_schema(
            "CompileContextSuccessResponse",
            ("context_pack", "metadata", "trace_event_count", "trace_id"),
            required=("context_pack", "metadata", "trace_event_count", "trace_id"),
            closed=True,
        ),
    ),
    ("POST", "/v0/responses"): (
        "GenerateAssistantResponseSuccessResponse",
        _operation_schema(
            "GenerateAssistantResponseSuccessResponse",
            (
                "assistant",
                "detail",
                "metadata",
                "response_job",
                "trace",
            ),
            closed=False,
        ),
    ),
    ("GET", "/v0/traces"): (
        "ListTracesSuccessResponse",
        _operation_schema(
            "ListTracesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/traces/{trace_id}"): (
        "GetTraceSuccessResponse",
        _operation_schema(
            "GetTraceSuccessResponse",
            (
                "trace",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/traces/{trace_id}/events"): (
        "ListTraceEventsSuccessResponse",
        _operation_schema(
            "ListTraceEventsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/memories/admit"): (
        "AdmitMemorySuccessResponse",
        _operation_schema(
            "AdmitMemorySuccessResponse",
            ("decision", "memory", "open_loop", "reason", "revision"),
            required=("decision", "memory", "reason", "revision"),
            closed=True,
        ),
    ),
    ("GET", "/v0/open-loops"): (
        "ListOpenLoopsSuccessResponse",
        _operation_schema(
            "ListOpenLoopsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/open-loops/{open_loop_id}"): (
        "GetOpenLoopSuccessResponse",
        _operation_schema(
            "GetOpenLoopSuccessResponse",
            (
                "open_loop",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/open-loops"): (
        "CreateOpenLoopSuccessResponse",
        _operation_schema(
            "CreateOpenLoopSuccessResponse",
            (
                "open_loop",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/open-loops/{open_loop_id}/status"): (
        "UpdateOpenLoopStatusSuccessResponse",
        _operation_schema(
            "UpdateOpenLoopStatusSuccessResponse",
            (
                "open_loop",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/consents"): (
        "UpsertConsentSuccessResponse",
        _operation_schema(
            "UpsertConsentSuccessResponse",
            (
                "consent",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/consents"): (
        "ListConsentsSuccessResponse",
        _operation_schema(
            "ListConsentsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/policies"): (
        "CreatePolicySuccessResponse",
        _operation_schema(
            "CreatePolicySuccessResponse",
            (
                "policy",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/policies"): (
        "ListPoliciesSuccessResponse",
        _operation_schema(
            "ListPoliciesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/policies/{policy_id}"): (
        "GetPolicySuccessResponse",
        _operation_schema(
            "GetPolicySuccessResponse",
            (
                "policy",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/policies/evaluate"): (
        "EvaluatePolicySuccessResponse",
        _operation_schema(
            "EvaluatePolicySuccessResponse",
            (
                "policy",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/tools"): (
        "CreateToolSuccessResponse",
        _operation_schema(
            "CreateToolSuccessResponse",
            (
                "tool",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/tools"): (
        "ListToolsSuccessResponse",
        _operation_schema(
            "ListToolsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/tools/allowlist/evaluate"): (
        "EvaluateToolsAllowlistSuccessResponse",
        _operation_schema(
            "EvaluateToolsAllowlistSuccessResponse",
            (
                "allowlist",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/tools/route"): (
        "RouteToolSuccessResponse",
        _operation_schema(
            "RouteToolSuccessResponse",
            (
                "tool",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/approvals/requests"): (
        "CreateApprovalRequestSuccessResponse",
        _operation_schema(
            "CreateApprovalRequestSuccessResponse",
            (
                "request",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/approvals"): (
        "ListApprovalsSuccessResponse",
        _operation_schema(
            "ListApprovalsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/approvals/{approval_id}"): (
        "GetApprovalSuccessResponse",
        _operation_schema(
            "GetApprovalSuccessResponse",
            (
                "approval",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/approvals/{approval_id}/approve"): (
        "ApproveApprovalSuccessResponse",
        _operation_schema(
            "ApproveApprovalSuccessResponse",
            (
                "approval",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/approvals/{approval_id}/reject"): (
        "RejectApprovalSuccessResponse",
        _operation_schema(
            "RejectApprovalSuccessResponse",
            (
                "approval",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/approvals/{approval_id}/execute"): (
        "ExecuteApprovedProxySuccessResponse",
        _operation_schema(
            "ExecuteApprovedProxySuccessResponse",
            (
                "approval",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/tasks"): (
        "ListTasksSuccessResponse",
        _operation_schema(
            "ListTasksSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/tasks/{task_id}"): (
        "GetTaskSuccessResponse",
        _operation_schema(
            "GetTaskSuccessResponse",
            (
                "task",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/tasks/{task_id}/runs"): (
        "CreateTaskRunSuccessResponse",
        _operation_schema(
            "CreateTaskRunSuccessResponse",
            (
                "run",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/tasks/{task_id}/runs"): (
        "ListTaskRunsSuccessResponse",
        _operation_schema(
            "ListTaskRunsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/task-runs/{task_run_id}"): (
        "GetTaskRunSuccessResponse",
        _operation_schema(
            "GetTaskRunSuccessResponse",
            (
                "task_run",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-runs/{task_run_id}/tick"): (
        "TickTaskRunSuccessResponse",
        _operation_schema(
            "TickTaskRunSuccessResponse",
            (
                "task_run",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-runs/{task_run_id}/pause"): (
        "PauseTaskRunSuccessResponse",
        _operation_schema(
            "PauseTaskRunSuccessResponse",
            (
                "task_run",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-runs/{task_run_id}/resume"): (
        "ResumeTaskRunSuccessResponse",
        _operation_schema(
            "ResumeTaskRunSuccessResponse",
            (
                "task_run",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-runs/{task_run_id}/cancel"): (
        "CancelTaskRunSuccessResponse",
        _operation_schema(
            "CancelTaskRunSuccessResponse",
            (
                "task_run",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/gmail-accounts"): (
        "ConnectGmailAccountSuccessResponse",
        _operation_schema(
            "ConnectGmailAccountSuccessResponse",
            (
                "gmail_account",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/gmail-accounts"): (
        "ListGmailAccountsSuccessResponse",
        _operation_schema(
            "ListGmailAccountsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/gmail-accounts/{gmail_account_id}"): (
        "GetGmailAccountSuccessResponse",
        _operation_schema(
            "GetGmailAccountSuccessResponse",
            (
                "gmail_account",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/gmail-accounts/{gmail_account_id}/messages/{provider_message_id}/ingest"): (
        "IngestGmailMessageSuccessResponse",
        _operation_schema(
            "IngestGmailMessageSuccessResponse",
            (
                "ingest",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/calendar-accounts"): (
        "ConnectCalendarAccountSuccessResponse",
        _operation_schema(
            "ConnectCalendarAccountSuccessResponse",
            (
                "calendar_account",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/calendar-accounts"): (
        "ListCalendarAccountsSuccessResponse",
        _operation_schema(
            "ListCalendarAccountsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/calendar-accounts/{calendar_account_id}"): (
        "GetCalendarAccountSuccessResponse",
        _operation_schema(
            "GetCalendarAccountSuccessResponse",
            (
                "calendar_account",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/calendar-accounts/{calendar_account_id}/events"): (
        "ListCalendarEventsSuccessResponse",
        _operation_schema(
            "ListCalendarEventsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/calendar-accounts/{calendar_account_id}/events/{provider_event_id}/ingest"): (
        "IngestCalendarEventSuccessResponse",
        _operation_schema(
            "IngestCalendarEventSuccessResponse",
            (
                "ingest",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/tasks/{task_id}/workspace"): (
        "CreateTaskWorkspaceSuccessResponse",
        _operation_schema(
            "CreateTaskWorkspaceSuccessResponse",
            (
                "workspace",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/task-workspaces"): (
        "ListTaskWorkspacesSuccessResponse",
        _operation_schema(
            "ListTaskWorkspacesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/task-workspaces/{task_workspace_id}"): (
        "GetTaskWorkspaceSuccessResponse",
        _operation_schema(
            "GetTaskWorkspaceSuccessResponse",
            (
                "task_workspace",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/tasks/{task_id}/steps"): (
        "ListTaskStepsSuccessResponse",
        _operation_schema(
            "ListTaskStepsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/task-steps/{task_step_id}"): (
        "GetTaskStepSuccessResponse",
        _operation_schema(
            "GetTaskStepSuccessResponse",
            (
                "task_step",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-workspaces/{task_workspace_id}/artifacts"): (
        "RegisterTaskArtifactSuccessResponse",
        _operation_schema(
            "RegisterTaskArtifactSuccessResponse",
            (
                "artifact",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/task-artifacts"): (
        "ListTaskArtifactsSuccessResponse",
        _operation_schema(
            "ListTaskArtifactsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/task-artifacts/{task_artifact_id}"): (
        "GetTaskArtifactSuccessResponse",
        _operation_schema(
            "GetTaskArtifactSuccessResponse",
            (
                "task_artifact",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-artifacts/{task_artifact_id}/ingest"): (
        "IngestTaskArtifactSuccessResponse",
        _operation_schema(
            "IngestTaskArtifactSuccessResponse",
            (
                "ingest",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/task-artifacts/{task_artifact_id}/chunks"): (
        "ListTaskArtifactChunksSuccessResponse",
        _operation_schema(
            "ListTaskArtifactChunksSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/tasks/{task_id}/artifact-chunks/retrieve"): (
        "RetrieveTaskArtifactChunksSuccessResponse",
        _operation_schema(
            "RetrieveTaskArtifactChunksSuccessResponse",
            (
                "retrieve",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-artifacts/{task_artifact_id}/chunks/retrieve"): (
        "RetrieveTaskArtifactChunksForArtifactSuccessResponse",
        _operation_schema(
            "RetrieveTaskArtifactChunksForArtifactSuccessResponse",
            (
                "retrieve",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/tasks/{task_id}/artifact-chunks/semantic-retrieval"): (
        "RetrieveSemanticTaskArtifactChunksSuccessResponse",
        _operation_schema(
            "RetrieveSemanticTaskArtifactChunksSuccessResponse",
            (
                "semantic_retrieval",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-artifacts/{task_artifact_id}/chunks/semantic-retrieval"): (
        "RetrieveSemanticArtifactChunksForArtifactSuccessResponse",
        _operation_schema(
            "RetrieveSemanticArtifactChunksForArtifactSuccessResponse",
            (
                "semantic_retrieval",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/tasks/{task_id}/steps"): (
        "CreateNextTaskStepSuccessResponse",
        _operation_schema(
            "CreateNextTaskStepSuccessResponse",
            (
                "step",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-steps/{task_step_id}/transition"): (
        "TransitionTaskStepSuccessResponse",
        _operation_schema(
            "TransitionTaskStepSuccessResponse",
            (
                "task_step",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/execution-budgets"): (
        "CreateExecutionBudgetSuccessResponse",
        _operation_schema(
            "CreateExecutionBudgetSuccessResponse",
            (
                "execution_budget",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/execution-budgets"): (
        "ListExecutionBudgetsSuccessResponse",
        _operation_schema(
            "ListExecutionBudgetsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/execution-budgets/{execution_budget_id}"): (
        "GetExecutionBudgetSuccessResponse",
        _operation_schema(
            "GetExecutionBudgetSuccessResponse",
            (
                "execution_budget",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/execution-budgets/{execution_budget_id}/deactivate"): (
        "DeactivateExecutionBudgetSuccessResponse",
        _operation_schema(
            "DeactivateExecutionBudgetSuccessResponse",
            (
                "execution_budget",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/execution-budgets/{execution_budget_id}/supersede"): (
        "SupersedeExecutionBudgetSuccessResponse",
        _operation_schema(
            "SupersedeExecutionBudgetSuccessResponse",
            (
                "execution_budget",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/tool-executions"): (
        "ListToolExecutionsSuccessResponse",
        _operation_schema(
            "ListToolExecutionsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/tool-executions/{execution_id}"): (
        "GetToolExecutionSuccessResponse",
        _operation_schema(
            "GetToolExecutionSuccessResponse",
            (
                "tool_execution",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/tools/{tool_id}"): (
        "GetToolSuccessResponse",
        _operation_schema(
            "GetToolSuccessResponse",
            (
                "tool",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/memories/extract-explicit-preferences"): (
        "ExtractExplicitPreferencesSuccessResponse",
        _operation_schema(
            "ExtractExplicitPreferencesSuccessResponse",
            ("admissions", "candidates", "summary"),
        ),
    ),
    ("POST", "/v0/open-loops/extract-explicit-commitments"): (
        "ExtractExplicitCommitmentsSuccessResponse",
        _operation_schema(
            "ExtractExplicitCommitmentsSuccessResponse",
            ("admissions", "candidates", "summary"),
        ),
    ),
    ("POST", "/v0/memories/capture-explicit-signals"): (
        "CaptureExplicitSignalsSuccessResponse",
        _operation_schema(
            "CaptureExplicitSignalsSuccessResponse",
            ("commitments", "preferences", "summary"),
        ),
    ),
    ("POST", "/v0/continuity/captures"): (
        "CreateContinuityCaptureSuccessResponse",
        _operation_schema(
            "CreateContinuityCaptureSuccessResponse",
            (
                "capture",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/workspace"): (
        "GetVnextWorkspaceSuccessResponse",
        _operation_schema(
            "GetVnextWorkspaceSuccessResponse",
            (
                "workspace",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/sources"): (
        "CreateVnextSourceSuccessResponse",
        _operation_schema(
            "CreateVnextSourceSuccessResponse",
            (
                "source",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/projects"): (
        "CreateVnextProjectSuccessResponse",
        _operation_schema("CreateVnextProjectSuccessResponse", ("project",), required=("project",), closed=True),
    ),
    ("GET", "/v0/vnext/projects"): (
        "ListVnextProjectsSuccessResponse",
        _operation_schema(
            "ListVnextProjectsSuccessResponse",
            ("count", "items", "order"),
            required=("count", "items", "order"),
            closed=True,
        ),
    ),
    ("GET", "/v0/vnext/connectors"): (
        "ListVnextConnectorsSuccessResponse",
        _operation_schema(
            "ListVnextConnectorsSuccessResponse",
            ("count", "items", "order"),
            required=("count", "items", "order"),
            closed=True,
        ),
    ),
    ("GET", "/v0/vnext/connectors/health"): (
        "GetVnextConnectorsHealthSuccessResponse",
        _operation_schema(
            "GetVnextConnectorsHealthSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/vnext/connectors/{connector_name}/status"): (
        "GetVnextConnectorStatusSuccessResponse",
        _operation_schema(
            "GetVnextConnectorStatusSuccessResponse",
            ("config", "health", "recent_captures", "recent_failures"),
            required=("config", "health", "recent_captures", "recent_failures"),
            closed=True,
        ),
    ),
    ("PATCH", "/v0/vnext/connectors/{connector_name}/config"): (
        "UpdateVnextConnectorConfigSuccessResponse",
        _operation_schema(
            "UpdateVnextConnectorConfigSuccessResponse",
            (
                "config",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/connectors/{connector_name}/sync"): (
        "SyncVnextConnectorSuccessResponse",
        _operation_schema(
            "SyncVnextConnectorSuccessResponse",
            (
                "connector",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/connectors/telegram/sync"): (
        "SyncVnextTelegramConnectorSuccessResponse",
        _operation_schema(
            "SyncVnextTelegramConnectorSuccessResponse",
            (
                "telegram",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/connectors/local-folder/sync"): (
        "SyncVnextLocalFolderConnectorSuccessResponse",
        _operation_schema(
            "SyncVnextLocalFolderConnectorSuccessResponse",
            (
                "local_folder",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/connectors/browser-clipper/capture"): (
        "CaptureVnextBrowserClipSuccessResponse",
        _operation_schema(
            "CaptureVnextBrowserClipSuccessResponse",
            (
                "browser_clipper",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/agents/ingest-output"): (
        "IngestVnextAgentOutputSuccessResponse",
        _operation_schema(
            "IngestVnextAgentOutputSuccessResponse",
            (
                "ingest_output",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/dogfooding"): (
        "GetVnextDogfoodingDashboardSuccessResponse",
        _operation_schema(
            "GetVnextDogfoodingDashboardSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/vnext/doctor"): (
        "GetVnextDoctorSuccessResponse",
        _operation_schema(
            "GetVnextDoctorSuccessResponse",
            (
                "doctor",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/doctor/run"): (
        "RunVnextDoctorSuccessResponse",
        _operation_schema(
            "RunVnextDoctorSuccessResponse",
            (
                "run",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/artifacts/{artifact_id}/insight-feedback"): (
        "RecordVnextArtifactInsightFeedbackSuccessResponse",
        _operation_schema(
            "RecordVnextArtifactInsightFeedbackSuccessResponse",
            (
                "insight_feedback",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/sources/{source_id}"): (
        "GetVnextSourceSuccessResponse",
        _operation_schema(
            "GetVnextSourceSuccessResponse",
            (
                "source",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/sources/{source_id}/review"): (
        "ReviewVnextSourceSuccessResponse",
        _operation_schema(
            "ReviewVnextSourceSuccessResponse",
            ("archived", "source", "trace"),
            required=("archived", "source", "trace"),
            closed=True,
        ),
    ),
    ("GET", "/v0/vnext/traces/sources/{source_id}"): (
        "GetVnextSourceTraceSuccessResponse",
        _operation_schema(
            "GetVnextSourceTraceSuccessResponse",
            (
                "source",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/traces/artifacts/{artifact_id}"): (
        "GetVnextArtifactTraceSuccessResponse",
        _operation_schema(
            "GetVnextArtifactTraceSuccessResponse",
            (
                "artifact",
                "status",
            ),
        ),
    ),
    ("DELETE", "/v0/vnext/sources/{source_id}"): (
        "DeleteVnextSourceSuccessResponse",
        _operation_schema(
            "DeleteVnextSourceSuccessResponse",
            (
                "status",
                "source_id",
            ),
        ),
    ),
    ("POST", "/v0/vnext/context-packs"): (
        "CreateVnextContextPackSuccessResponse",
        _operation_schema(
            "CreateVnextContextPackSuccessResponse",
            (
                "context_pack",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/context-tree"): (
        "GetVnextContextTreeSuccessResponse",
        _operation_schema(
            "GetVnextContextTreeSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/{memory_id}/review"): (
        "ReviewVnextMemorySuccessResponse",
        _operation_schema(
            "ReviewVnextMemorySuccessResponse",
            ("consolidation_acceptance", "memory"),
            required=("memory",),
            closed=True,
        ),
    ),
    ("POST", "/v0/vnext/memory-proposals"): (
        "CreateVnextMemoryProposalSuccessResponse",
        _operation_schema(
            "CreateVnextMemoryProposalSuccessResponse",
            ("policy_decision", "proposal", "review_required"),
            required=("policy_decision", "proposal", "review_required"),
            closed=True,
        ),
    ),
    ("POST", "/v0/vnext/memories/commit"): (
        "CommitVnextMemorySuccessResponse",
        _operation_schema(
            "CommitVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/confirm"): (
        "ConfirmVnextMemorySuccessResponse",
        _operation_schema(
            "ConfirmVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/undo"): (
        "UndoVnextMemorySuccessResponse",
        _operation_schema(
            "UndoVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/correct"): (
        "CorrectVnextMemorySuccessResponse",
        _operation_schema(
            "CorrectVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/forget"): (
        "ForgetVnextMemorySuccessResponse",
        _operation_schema(
            "ForgetVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/expire"): (
        "ExpireVnextMemorySuccessResponse",
        _operation_schema(
            "ExpireVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/unexpire"): (
        "UnexpireVnextMemorySuccessResponse",
        _operation_schema(
            "UnexpireVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/accept-consolidation"): (
        "AcceptVnextMemoryConsolidationSuccessResponse",
        _operation_schema(
            "AcceptVnextMemoryConsolidationSuccessResponse",
            (
                "accept_consolidation",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/memories/redact"): (
        "RedactVnextMemorySuccessResponse",
        _operation_schema(
            "RedactVnextMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/memories/recent-commits"): (
        "ListVnextRecentMemoryCommitsSuccessResponse",
        _operation_schema(
            "ListVnextRecentMemoryCommitsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/vnext/memories/{memory_id}/audit"): (
        "GetVnextMemoryAuditSuccessResponse",
        _operation_schema(
            "GetVnextMemoryAuditSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/vnext/artifacts/generate/daily-brief"): (
        "GenerateVnextDailyBriefSuccessResponse",
        _operation_schema(
            "GenerateVnextDailyBriefSuccessResponse",
            _ARTIFACT_RESPONSE_FIELDS,
        ),
    ),
    ("POST", "/v0/vnext/artifacts/generate/weekly-synthesis"): (
        "GenerateVnextWeeklySynthesisSuccessResponse",
        _operation_schema(
            "GenerateVnextWeeklySynthesisSuccessResponse",
            _ARTIFACT_RESPONSE_FIELDS,
        ),
    ),
    ("POST", "/v0/vnext/artifacts/generate/connections"): (
        "GenerateVnextConnectionReportSuccessResponse",
        _operation_schema(
            "GenerateVnextConnectionReportSuccessResponse",
            _ARTIFACT_RESPONSE_FIELDS,
        ),
    ),
    ("POST", "/v0/vnext/artifacts/generate/contradictions"): (
        "GenerateVnextContradictionReportSuccessResponse",
        _operation_schema(
            "GenerateVnextContradictionReportSuccessResponse",
            _ARTIFACT_RESPONSE_FIELDS,
        ),
    ),
    ("POST", "/v0/vnext/queue/tasks"): (
        "CreateVnextQueueTaskSuccessResponse",
        _operation_schema(
            "CreateVnextQueueTaskSuccessResponse",
            (
                "task",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/queue/process-next"): (
        "ProcessNextVnextQueueTaskSuccessResponse",
        _operation_schema(
            "ProcessNextVnextQueueTaskSuccessResponse",
            (
                "queue",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/artifacts"): (
        "ListVnextArtifactsSuccessResponse",
        _operation_schema(
            "ListVnextArtifactsSuccessResponse",
            ("count", "items", "order"),
            required=("count", "items", "order"),
            closed=True,
        ),
    ),
    ("GET", "/v0/vnext/artifacts/{artifact_id}"): (
        "GetVnextArtifactSuccessResponse",
        _operation_schema(
            "GetVnextArtifactSuccessResponse",
            (
                "artifact",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/artifacts/{artifact_id}/review"): (
        "ReviewVnextArtifactSuccessResponse",
        _operation_schema(
            "ReviewVnextArtifactSuccessResponse",
            (
                "artifact",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/artifacts/{artifact_id}/quality-ratings"): (
        "RateVnextArtifactQualitySuccessResponse",
        _operation_schema(
            "RateVnextArtifactQualitySuccessResponse",
            (
                "quality_rating",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/quality-evals"): (
        "ListVnextQualityEvalsSuccessResponse",
        _operation_schema(
            "ListVnextQualityEvalsSuccessResponse",
            ("count", "export", "items", "order"),
            required=("count", "export", "items", "order"),
            closed=True,
        ),
    ),
    ("POST", "/v0/vnext/artifacts/{artifact_id}/export"): (
        "ExportVnextArtifactSuccessResponse",
        _operation_schema(
            "ExportVnextArtifactSuccessResponse",
            ("artifact_id", "output_path"),
            required=("artifact_id", "output_path"),
            closed=True,
        ),
    ),
    ("POST", "/v0/vnext/graph/edges/{edge_id}/review"): (
        "ReviewVnextGraphEdgeSuccessResponse",
        _operation_schema(
            "ReviewVnextGraphEdgeSuccessResponse",
            (
                "edge",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/graph/neighborhood/{target_id}"): (
        "GetVnextGraphNeighborhoodSuccessResponse",
        _operation_schema(
            "GetVnextGraphNeighborhoodSuccessResponse",
            (
                "neighborhood",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/beliefs/{belief_id}/review"): (
        "ReviewVnextBeliefSuccessResponse",
        _operation_schema(
            "ReviewVnextBeliefSuccessResponse",
            (
                "belief",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/vnext/beliefs/{belief_id}/state"): (
        "GetVnextBeliefStateSuccessResponse",
        _operation_schema(
            "GetVnextBeliefStateSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/vnext/projects/update-candidates"): (
        "GenerateVnextProjectUpdateCandidateSuccessResponse",
        _operation_schema(
            "GenerateVnextProjectUpdateCandidateSuccessResponse",
            _ARTIFACT_RESPONSE_FIELDS,
        ),
    ),
    ("POST", "/v0/vnext/projects/update-candidates/{artifact_id}/review"): (
        "ReviewVnextProjectUpdateCandidateSuccessResponse",
        _operation_schema(
            "ReviewVnextProjectUpdateCandidateSuccessResponse",
            _ARTIFACT_RESPONSE_FIELDS,
        ),
    ),
    ("GET", "/v0/vnext/projects/{project_id}/dashboard"): (
        "GetVnextProjectDashboardSuccessResponse",
        _operation_schema(
            "GetVnextProjectDashboardSuccessResponse",
            (
                "dashboard",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/open-loops"): (
        "CreateVnextOpenLoopSuccessResponse",
        _operation_schema("CreateVnextOpenLoopSuccessResponse", ("open_loop",), required=("open_loop",), closed=True),
    ),
    ("GET", "/v0/vnext/settings/brain-charter"): (
        "GetVnextBrainCharterSuccessResponse",
        _operation_schema(
            "GetVnextBrainCharterSuccessResponse", ("brain_charter",), required=("brain_charter",), closed=True
        ),
    ),
    ("PUT", "/v0/vnext/settings/brain-charter"): (
        "UpsertVnextBrainCharterSuccessResponse",
        _operation_schema(
            "UpsertVnextBrainCharterSuccessResponse", ("brain_charter",), required=("brain_charter",), closed=True
        ),
    ),
    ("GET", "/v0/vnext/scheduler/status"): (
        "GetVnextSchedulerStatusSuccessResponse",
        _operation_schema("GetVnextSchedulerStatusSuccessResponse", ("daemon",), required=("daemon",), closed=True),
    ),
    ("GET", "/v0/vnext/scheduler/runs"): (
        "ListVnextSchedulerRunsSuccessResponse",
        _operation_schema(
            "ListVnextSchedulerRunsSuccessResponse", ("count", "items"), required=("count", "items"), closed=True
        ),
    ),
    ("GET", "/v0/vnext/scheduler/failures"): (
        "ListVnextSchedulerFailuresSuccessResponse",
        _operation_schema(
            "ListVnextSchedulerFailuresSuccessResponse", ("count", "items"), required=("count", "items"), closed=True
        ),
    ),
    ("GET", "/v0/vnext/agents/policy-telemetry"): (
        "GetVnextAgentPolicyTelemetrySuccessResponse",
        _operation_schema(
            "GetVnextAgentPolicyTelemetrySuccessResponse", ("summary",), required=("summary",), closed=True
        ),
    ),
    ("PATCH", "/v0/vnext/scheduler/workflows/{workflow_type}"): (
        "PatchVnextSchedulerWorkflowSuccessResponse",
        _operation_schema(
            "PatchVnextSchedulerWorkflowSuccessResponse",
            ("policy_decision", "workflow"),
            required=("policy_decision", "workflow"),
            closed=True,
        ),
    ),
    ("POST", "/v0/vnext/scheduler/workflows/{workflow_type}/run-now"): (
        "RunVnextSchedulerWorkflowNowSuccessResponse",
        _operation_schema(
            "RunVnextSchedulerWorkflowNowSuccessResponse",
            ("policy_decision",),
            required=("policy_decision",),
            closed=False,
        ),
    ),
    ("POST", "/v0/vnext/scheduler/run-due"): (
        "RunVnextSchedulerDueSuccessResponse",
        _operation_schema(
            "RunVnextSchedulerDueSuccessResponse", ("policy_decision",), required=("policy_decision",), closed=False
        ),
    ),
    ("POST", "/v0/vnext/scheduler/pause"): (
        "PauseVnextSchedulerSuccessResponse",
        _operation_schema(
            "PauseVnextSchedulerSuccessResponse",
            (
                "scheduler",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/scheduler/resume"): (
        "ResumeVnextSchedulerSuccessResponse",
        _operation_schema(
            "ResumeVnextSchedulerSuccessResponse",
            (
                "scheduler",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/vnext/open-loops/extract"): (
        "ExtractVnextOpenLoopsSuccessResponse",
        _operation_schema(
            "ExtractVnextOpenLoopsSuccessResponse",
            ("created_count", "open_loops"),
            required=("created_count", "open_loops"),
            closed=True,
        ),
    ),
    ("POST", "/v0/vnext/open-loops/{loop_id}/review"): (
        "ReviewVnextOpenLoopSuccessResponse",
        _operation_schema(
            "ReviewVnextOpenLoopSuccessResponse",
            (
                "open_loop",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/continuity/captures/candidates"): (
        "CreateContinuityCaptureCandidatesSuccessResponse",
        _operation_schema(
            "CreateContinuityCaptureCandidatesSuccessResponse",
            (
                "candidate",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/continuity/captures/commit"): (
        "CommitContinuityCaptureCandidatesSuccessResponse",
        _operation_schema(
            "CommitContinuityCaptureCandidatesSuccessResponse",
            (
                "capture",
                "status",
            ),
        ),
    ),
    ("POST", "/v1/memory/operations/candidates/generate"): (
        "GenerateMemoryOperationCandidatesEndpointSuccessResponse",
        _operation_schema(
            "GenerateMemoryOperationCandidatesEndpointSuccessResponse",
            (
                "candidate",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/memory/operations/candidates"): (
        "ListMemoryOperationCandidatesEndpointSuccessResponse",
        _operation_schema(
            "ListMemoryOperationCandidatesEndpointSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v1/memory/operations/commit"): (
        "CommitMemoryOperationsEndpointSuccessResponse",
        _operation_schema(
            "CommitMemoryOperationsEndpointSuccessResponse",
            (
                "operation",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/memory/operations"): (
        "ListMemoryOperationsEndpointSuccessResponse",
        _operation_schema(
            "ListMemoryOperationsEndpointSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/continuity/captures"): (
        "ListContinuityCapturesSuccessResponse",
        _operation_schema(
            "ListContinuityCapturesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/continuity/captures/{capture_event_id}"): (
        "GetContinuityCaptureSuccessResponse",
        _operation_schema(
            "GetContinuityCaptureSuccessResponse",
            (
                "capture",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/continuity/review-queue/{continuity_object_id}/corrections"): (
        "ApplyContinuityCorrectionEndpointSuccessResponse",
        _operation_schema(
            "ApplyContinuityCorrectionEndpointSuccessResponse",
            (
                "correction",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/task-briefs/{task_brief_id}"): (
        "GetV0TaskBriefSuccessResponse",
        _operation_schema(
            "GetV0TaskBriefSuccessResponse",
            (
                "task_brief",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/memories"): (
        "ListMemoriesSuccessResponse",
        _operation_schema(
            "ListMemoriesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/memories/review-queue"): (
        "ListMemoryReviewQueueSuccessResponse",
        _operation_schema(
            "ListMemoryReviewQueueSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/memories/quality-gate"): (
        "GetMemoriesQualityGateSuccessResponse",
        _operation_schema(
            "GetMemoriesQualityGateSuccessResponse",
            (
                "quality_gate",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/memories/evaluation-summary"): (
        "GetMemoriesEvaluationSummarySuccessResponse",
        _operation_schema(
            "GetMemoriesEvaluationSummarySuccessResponse",
            (
                "evaluation_summary",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/memories/semantic-retrieval"): (
        "RetrieveSemanticMemoriesSuccessResponse",
        _operation_schema(
            "RetrieveSemanticMemoriesSuccessResponse",
            (
                "semantic_retrieval",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/memories/{memory_id}"): (
        "GetMemorySuccessResponse",
        _operation_schema(
            "GetMemorySuccessResponse",
            (
                "memory",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/memories/{memory_id}/revisions"): (
        "ListMemoryRevisionsSuccessResponse",
        _operation_schema(
            "ListMemoryRevisionsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/memories/{memory_id}/labels"): (
        "CreateMemoryReviewLabelSuccessResponse",
        _operation_schema(
            "CreateMemoryReviewLabelSuccessResponse",
            (
                "label",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/memories/{memory_id}/labels"): (
        "ListMemoryReviewLabelsSuccessResponse",
        _operation_schema(
            "ListMemoryReviewLabelsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/embedding-configs"): (
        "CreateEmbeddingConfigSuccessResponse",
        _operation_schema(
            "CreateEmbeddingConfigSuccessResponse",
            (
                "embedding_config",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/embedding-configs"): (
        "ListEmbeddingConfigsSuccessResponse",
        _operation_schema(
            "ListEmbeddingConfigsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v0/memory-embeddings"): (
        "UpsertMemoryEmbeddingSuccessResponse",
        _operation_schema(
            "UpsertMemoryEmbeddingSuccessResponse",
            (
                "memory_embedding",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/task-artifact-chunk-embeddings"): (
        "UpsertTaskArtifactChunkEmbeddingSuccessResponse",
        _operation_schema(
            "UpsertTaskArtifactChunkEmbeddingSuccessResponse",
            (
                "task_artifact_chunk_embedding",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/memories/{memory_id}/embeddings"): (
        "ListMemoryEmbeddingsSuccessResponse",
        _operation_schema(
            "ListMemoryEmbeddingsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/task-artifacts/{task_artifact_id}/chunk-embeddings"): (
        "ListTaskArtifactChunkEmbeddingsForArtifactSuccessResponse",
        _operation_schema(
            "ListTaskArtifactChunkEmbeddingsForArtifactSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/task-artifact-chunks/{task_artifact_chunk_id}/embeddings"): (
        "ListTaskArtifactChunkEmbeddingsSuccessResponse",
        _operation_schema(
            "ListTaskArtifactChunkEmbeddingsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/memory-embeddings/{memory_embedding_id}"): (
        "GetMemoryEmbeddingSuccessResponse",
        _operation_schema(
            "GetMemoryEmbeddingSuccessResponse",
            (
                "memory_embedding",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/task-artifact-chunk-embeddings/{task_artifact_chunk_embedding_id}"): (
        "GetTaskArtifactChunkEmbeddingSuccessResponse",
        _operation_schema(
            "GetTaskArtifactChunkEmbeddingSuccessResponse",
            (
                "task_artifact_chunk_embedding",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/entities"): (
        "CreateEntitySuccessResponse",
        _operation_schema(
            "CreateEntitySuccessResponse",
            (
                "entity",
                "status",
            ),
        ),
    ),
    ("POST", "/v0/entity-edges"): (
        "CreateEntityEdgeSuccessResponse",
        _operation_schema(
            "CreateEntityEdgeSuccessResponse",
            (
                "entity_edge",
                "status",
            ),
        ),
    ),
    ("GET", "/v0/entities"): (
        "ListEntitiesSuccessResponse",
        _operation_schema(
            "ListEntitiesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/entities/{entity_id}/edges"): (
        "ListEntityEdgesSuccessResponse",
        _operation_schema(
            "ListEntityEdgesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v0/entities/{entity_id}"): (
        "GetEntitySuccessResponse",
        _operation_schema(
            "GetEntitySuccessResponse",
            (
                "entity",
                "status",
            ),
        ),
    ),
    ("POST", "/v1/auth/magic-link/start"): (
        "StartV1MagicLinkSuccessResponse",
        _operation_schema(
            "StartV1MagicLinkSuccessResponse",
            ("challenge", "delivery"),
            required=("challenge", "delivery"),
            closed=True,
        ),
    ),
    ("POST", "/v1/auth/magic-link/verify"): (
        "VerifyV1MagicLinkSuccessResponse",
        _operation_schema(
            "VerifyV1MagicLinkSuccessResponse",
            (
                "magic_link",
                "status",
                "expires_at",
            ),
        ),
    ),
    ("POST", "/v1/auth/logout"): (
        "LogoutV1AuthSessionSuccessResponse",
        _operation_schema("LogoutV1AuthSessionSuccessResponse", ("status",), required=("status",), closed=True),
    ),
    ("GET", "/v1/auth/session"): (
        "GetV1AuthSessionSuccessResponse",
        _operation_schema(
            "GetV1AuthSessionSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v1/workspaces"): (
        "CreateV1WorkspaceSuccessResponse",
        _operation_schema("CreateV1WorkspaceSuccessResponse", ("workspace",), required=("workspace",), closed=True),
    ),
    ("GET", "/v1/workspaces/current"): (
        "GetV1CurrentWorkspaceSuccessResponse",
        _operation_schema("GetV1CurrentWorkspaceSuccessResponse", ("workspace",), required=("workspace",), closed=True),
    ),
    ("POST", "/v1/workspaces/bootstrap"): (
        "BootstrapV1WorkspaceSuccessResponse",
        _operation_schema(
            "BootstrapV1WorkspaceSuccessResponse",
            ("bootstrap", "feature_flags", "preferences", "telegram_state", "workspace"),
            required=("bootstrap", "feature_flags", "preferences", "telegram_state", "workspace"),
            closed=True,
        ),
    ),
    ("GET", "/v1/workspaces/bootstrap/status"): (
        "GetV1WorkspaceBootstrapStatusSuccessResponse",
        _operation_schema(
            "GetV1WorkspaceBootstrapStatusSuccessResponse",
            ("bootstrap", "feature_flags", "telegram_state", "workspace"),
            required=("bootstrap", "feature_flags", "telegram_state", "workspace"),
            closed=True,
        ),
    ),
    ("POST", "/v1/providers"): (
        "RegisterV1ProviderSuccessResponse",
        _operation_schema(
            "RegisterV1ProviderSuccessResponse",
            ("capabilities", "provider"),
            required=("capabilities", "provider"),
            closed=True,
        ),
    ),
    ("POST", "/v1/providers/ollama/register"): (
        "RegisterV1OllamaProviderSuccessResponse",
        _operation_schema(
            "RegisterV1OllamaProviderSuccessResponse",
            ("capabilities", "provider"),
            required=("capabilities", "provider"),
            closed=True,
        ),
    ),
    ("POST", "/v1/providers/llamacpp/register"): (
        "RegisterV1LlamacppProviderSuccessResponse",
        _operation_schema(
            "RegisterV1LlamacppProviderSuccessResponse",
            ("capabilities", "provider"),
            required=("capabilities", "provider"),
            closed=True,
        ),
    ),
    ("POST", "/v1/providers/vllm/register"): (
        "RegisterV1VllmProviderSuccessResponse",
        _operation_schema(
            "RegisterV1VllmProviderSuccessResponse",
            ("capabilities", "provider"),
            required=("capabilities", "provider"),
            closed=True,
        ),
    ),
    ("POST", "/v1/providers/azure/register"): (
        "RegisterV1AzureProviderSuccessResponse",
        _operation_schema(
            "RegisterV1AzureProviderSuccessResponse",
            ("capabilities", "provider"),
            required=("capabilities", "provider"),
            closed=True,
        ),
    ),
    ("GET", "/v1/providers"): (
        "ListV1ProvidersSuccessResponse",
        _operation_schema(
            "ListV1ProvidersSuccessResponse", ("items", "summary"), required=("items", "summary"), closed=True
        ),
    ),
    ("GET", "/v1/providers/{provider_id}"): (
        "GetV1ProviderSuccessResponse",
        _operation_schema(
            "GetV1ProviderSuccessResponse",
            ("capabilities", "provider"),
            required=("capabilities", "provider"),
            closed=True,
        ),
    ),
    ("PATCH", "/v1/providers/{provider_id}"): (
        "UpdateV1ProviderSuccessResponse",
        _operation_schema(
            "UpdateV1ProviderSuccessResponse",
            ("capabilities", "provider"),
            required=("capabilities", "provider"),
            closed=True,
        ),
    ),
    ("POST", "/v1/providers/test"): (
        "TestV1ProviderSuccessResponse",
        _operation_schema(
            "TestV1ProviderSuccessResponse",
            ("capabilities", "provider", "result"),
            required=("capabilities", "provider", "result"),
            closed=True,
        ),
    ),
    ("GET", "/v1/model-packs"): (
        "ListV1ModelPacksSuccessResponse",
        _operation_schema(
            "ListV1ModelPacksSuccessResponse", ("items", "summary"), required=("items", "summary"), closed=True
        ),
    ),
    ("GET", "/v1/model-packs/{pack_id}"): (
        "GetV1ModelPackSuccessResponse",
        _operation_schema("GetV1ModelPackSuccessResponse", ("model_pack",), required=("model_pack",), closed=True),
    ),
    ("POST", "/v1/model-packs"): (
        "CreateV1ModelPackSuccessResponse",
        _operation_schema("CreateV1ModelPackSuccessResponse", ("model_pack",), required=("model_pack",), closed=True),
    ),
    ("POST", "/v1/model-packs/{pack_id}/bind"): (
        "BindV1ModelPackSuccessResponse",
        _operation_schema("BindV1ModelPackSuccessResponse", ("binding",), required=("binding",), closed=True),
    ),
    ("GET", "/v1/workspaces/{workspace_id}/model-pack-binding"): (
        "GetV1WorkspaceModelPackBindingSuccessResponse",
        _operation_schema(
            "GetV1WorkspaceModelPackBindingSuccessResponse", ("binding",), required=("binding",), closed=True
        ),
    ),
    ("POST", "/v1/runtime/invoke"): (
        "InvokeV1RuntimeSuccessResponse",
        _operation_schema(
            "InvokeV1RuntimeSuccessResponse",
            (
                "assistant",
                "detail",
                "metadata",
                "response_job",
                "trace",
            ),
            closed=False,
        ),
    ),
    ("POST", "/v1/devices/link/start"): (
        "StartV1DeviceLinkSuccessResponse",
        _operation_schema("StartV1DeviceLinkSuccessResponse", ("challenge",), required=("challenge",), closed=True),
    ),
    ("POST", "/v1/devices/link/confirm"): (
        "ConfirmV1DeviceLinkSuccessResponse",
        _operation_schema("ConfirmV1DeviceLinkSuccessResponse", ("device",), required=("device",), closed=True),
    ),
    ("GET", "/v1/devices"): (
        "ListV1DevicesSuccessResponse",
        _operation_schema(
            "ListV1DevicesSuccessResponse", ("items", "summary"), required=("items", "summary"), closed=True
        ),
    ),
    ("DELETE", "/v1/devices/{device_id}"): (
        "DeleteV1DeviceSuccessResponse",
        _operation_schema("DeleteV1DeviceSuccessResponse", ("device",), required=("device",), closed=True),
    ),
    ("GET", "/v1/preferences"): (
        "GetV1PreferencesSuccessResponse",
        _operation_schema("GetV1PreferencesSuccessResponse", ("preferences",), required=("preferences",), closed=True),
    ),
    ("PATCH", "/v1/preferences"): (
        "PatchV1PreferencesSuccessResponse",
        _operation_schema(
            "PatchV1PreferencesSuccessResponse", ("preferences",), required=("preferences",), closed=True
        ),
    ),
    ("GET", "/v1/admin/hosted/overview"): (
        "GetV1AdminHostedOverviewSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedOverviewSuccessResponse",
            (
                "overview",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/admin/hosted/design-partners/dashboard"): (
        "GetV1AdminHostedDesignPartnerDashboardSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedDesignPartnerDashboardSuccessResponse",
            (
                "dashboard",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/admin/hosted/design-partners"): (
        "GetV1AdminHostedDesignPartnersSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedDesignPartnersSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v1/admin/hosted/design-partners"): (
        "PostV1AdminHostedDesignPartnerSuccessResponse",
        _operation_schema(
            "PostV1AdminHostedDesignPartnerSuccessResponse",
            (
                "design_partner",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/admin/hosted/design-partners/{design_partner_id}"): (
        "GetV1AdminHostedDesignPartnerDetailSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedDesignPartnerDetailSuccessResponse",
            (
                "design_partner",
                "status",
            ),
        ),
    ),
    ("PATCH", "/v1/admin/hosted/design-partners/{design_partner_id}"): (
        "PatchV1AdminHostedDesignPartnerSuccessResponse",
        _operation_schema(
            "PatchV1AdminHostedDesignPartnerSuccessResponse",
            (
                "design_partner",
                "status",
            ),
        ),
    ),
    ("POST", "/v1/admin/hosted/design-partners/{design_partner_id}/workspaces"): (
        "PostV1AdminHostedDesignPartnerWorkspaceSuccessResponse",
        _operation_schema(
            "PostV1AdminHostedDesignPartnerWorkspaceSuccessResponse",
            (
                "workspace",
                "status",
            ),
        ),
    ),
    ("POST", "/v1/admin/hosted/design-partners/{design_partner_id}/feedback"): (
        "PostV1AdminHostedDesignPartnerFeedbackSuccessResponse",
        _operation_schema(
            "PostV1AdminHostedDesignPartnerFeedbackSuccessResponse",
            (
                "feedback",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/admin/hosted/workspaces"): (
        "GetV1AdminHostedWorkspacesSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedWorkspacesSuccessResponse",
            ("items", "summary"),
            required=("items", "summary"),
            closed=True,
        ),
    ),
    ("GET", "/v1/admin/hosted/delivery-receipts"): (
        "GetV1AdminHostedDeliveryReceiptsSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedDeliveryReceiptsSuccessResponse",
            ("items", "summary"),
            required=("items", "summary"),
            closed=True,
        ),
    ),
    ("GET", "/v1/admin/hosted/incidents"): (
        "GetV1AdminHostedIncidentsSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedIncidentsSuccessResponse", ("items", "summary"), required=("items", "summary"), closed=True
        ),
    ),
    ("GET", "/v1/admin/hosted/rollout-flags"): (
        "GetV1AdminHostedRolloutFlagsSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedRolloutFlagsSuccessResponse",
            ("items", "summary"),
            required=("items", "summary"),
            closed=True,
        ),
    ),
    ("PATCH", "/v1/admin/hosted/rollout-flags"): (
        "PatchV1AdminHostedRolloutFlagsSuccessResponse",
        _operation_schema(
            "PatchV1AdminHostedRolloutFlagsSuccessResponse",
            ("items", "summary", "updated"),
            required=("items", "summary", "updated"),
            closed=True,
        ),
    ),
    ("GET", "/v1/admin/hosted/analytics"): (
        "GetV1AdminHostedAnalyticsSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedAnalyticsSuccessResponse", ("analytics",), required=("analytics",), closed=True
        ),
    ),
    ("GET", "/v1/admin/hosted/rate-limits"): (
        "GetV1AdminHostedRateLimitsSuccessResponse",
        _operation_schema(
            "GetV1AdminHostedRateLimitsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v1/channels/telegram/link/start"): (
        "StartV1TelegramLinkSuccessResponse",
        _operation_schema(
            "StartV1TelegramLinkSuccessResponse",
            ("challenge", "instructions", "workspace_id"),
            required=("challenge", "instructions", "workspace_id"),
            closed=True,
        ),
    ),
    ("POST", "/v1/channels/telegram/link/confirm"): (
        "ConfirmV1TelegramLinkSuccessResponse",
        _operation_schema(
            "ConfirmV1TelegramLinkSuccessResponse",
            ("challenge", "identity"),
            required=("challenge", "identity"),
            closed=True,
        ),
    ),
    ("POST", "/v1/channels/telegram/unlink"): (
        "UnlinkV1TelegramSuccessResponse",
        _operation_schema("UnlinkV1TelegramSuccessResponse", ("identity",), required=("identity",), closed=True),
    ),
    ("GET", "/v1/channels/telegram/status"): (
        "GetV1TelegramStatusSuccessResponse",
        _operation_schema(
            "GetV1TelegramStatusSuccessResponse",
            (
                "telegram",
                "status",
            ),
        ),
    ),
    ("POST", "/v1/channels/telegram/webhook"): (
        "IngestV1TelegramWebhookSuccessResponse",
        _operation_schema(
            "IngestV1TelegramWebhookSuccessResponse",
            ("ingest", "status"),
            required=("ingest", "status"),
            closed=True,
        ),
    ),
    ("GET", "/v1/channels/telegram/messages"): (
        "ListV1TelegramMessagesSuccessResponse",
        _operation_schema(
            "ListV1TelegramMessagesSuccessResponse", ("items", "summary"), required=("items", "summary"), closed=True
        ),
    ),
    ("GET", "/v1/channels/telegram/threads"): (
        "ListV1TelegramThreadsSuccessResponse",
        _operation_schema(
            "ListV1TelegramThreadsSuccessResponse", ("items", "summary"), required=("items", "summary"), closed=True
        ),
    ),
    ("POST", "/v1/channels/telegram/messages/{message_id}/dispatch"): (
        "DispatchV1TelegramMessageSuccessResponse",
        _operation_schema(
            "DispatchV1TelegramMessageSuccessResponse",
            ("message", "receipt"),
            required=("message", "receipt"),
            closed=True,
        ),
    ),
    ("GET", "/v1/channels/telegram/delivery-receipts"): (
        "ListV1TelegramDeliveryReceiptsSuccessResponse",
        _operation_schema(
            "ListV1TelegramDeliveryReceiptsSuccessResponse",
            ("items", "summary"),
            required=("items", "summary"),
            closed=True,
        ),
    ),
    ("GET", "/v1/channels/telegram/notification-preferences"): (
        "GetV1TelegramNotificationPreferencesSuccessResponse",
        _operation_schema(
            "GetV1TelegramNotificationPreferencesSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("PATCH", "/v1/channels/telegram/notification-preferences"): (
        "PatchV1TelegramNotificationPreferencesSuccessResponse",
        _operation_schema(
            "PatchV1TelegramNotificationPreferencesSuccessResponse",
            (
                "notification_preference",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/channels/telegram/daily-brief"): (
        "GetV1TelegramDailyBriefSuccessResponse",
        _operation_schema(
            "GetV1TelegramDailyBriefSuccessResponse",
            (
                "daily_brief",
                "status",
            ),
        ),
    ),
    ("POST", "/v1/channels/telegram/daily-brief/deliver"): (
        "PostV1TelegramDailyBriefDeliverSuccessResponse",
        _operation_schema(
            "PostV1TelegramDailyBriefDeliverSuccessResponse",
            (
                "daily_brief",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/channels/telegram/open-loop-prompts"): (
        "ListV1TelegramOpenLoopPromptsSuccessResponse",
        _operation_schema(
            "ListV1TelegramOpenLoopPromptsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver"): (
        "PostV1TelegramOpenLoopPromptDeliverSuccessResponse",
        _operation_schema(
            "PostV1TelegramOpenLoopPromptDeliverSuccessResponse",
            (
                "open_loop_prompt",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/channels/telegram/scheduler/jobs"): (
        "ListV1TelegramSchedulerJobsSuccessResponse",
        _operation_schema(
            "ListV1TelegramSchedulerJobsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v1/channels/telegram/messages/{message_id}/handle"): (
        "HandleV1TelegramMessageSuccessResponse",
        _operation_schema(
            "HandleV1TelegramMessageSuccessResponse",
            (
                "message",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/channels/telegram/messages/{message_id}/result"): (
        "GetV1TelegramMessageResultSuccessResponse",
        _operation_schema(
            "GetV1TelegramMessageResultSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("GET", "/v1/channels/telegram/recall"): (
        "ListV1TelegramRecallSuccessResponse",
        _operation_schema(
            "ListV1TelegramRecallSuccessResponse",
            ("recall", "workspace_id"),
            required=("recall", "workspace_id"),
            closed=True,
        ),
    ),
    ("GET", "/v1/channels/telegram/resume"): (
        "GetV1TelegramResumptionBriefSuccessResponse",
        _operation_schema(
            "GetV1TelegramResumptionBriefSuccessResponse",
            ("resume", "workspace_id"),
            required=("resume", "workspace_id"),
            closed=True,
        ),
    ),
    ("GET", "/v1/channels/telegram/open-loops"): (
        "GetV1TelegramOpenLoopsSuccessResponse",
        _operation_schema(
            "GetV1TelegramOpenLoopsSuccessResponse",
            ("open_loops", "workspace_id"),
            required=("open_loops", "workspace_id"),
            closed=True,
        ),
    ),
    ("POST", "/v1/channels/telegram/open-loops/{open_loop_id}/review-action"): (
        "ReviewActionV1TelegramOpenLoopSuccessResponse",
        _operation_schema(
            "ReviewActionV1TelegramOpenLoopSuccessResponse",
            (
                "review_action",
                "status",
            ),
        ),
    ),
    ("GET", "/v1/channels/telegram/approvals"): (
        "ListV1TelegramApprovalsSuccessResponse",
        _operation_schema(
            "ListV1TelegramApprovalsSuccessResponse",
            (
                "items",
                "summary",
            ),
        ),
    ),
    ("POST", "/v1/channels/telegram/approvals/{approval_id}/approve"): (
        "ApproveV1TelegramApprovalSuccessResponse",
        _operation_schema(
            "ApproveV1TelegramApprovalSuccessResponse",
            (
                "approval",
                "status",
            ),
        ),
    ),
    ("POST", "/v1/channels/telegram/approvals/{approval_id}/reject"): (
        "RejectV1TelegramApprovalSuccessResponse",
        _operation_schema(
            "RejectV1TelegramApprovalSuccessResponse",
            (
                "approval",
                "status",
            ),
        ),
    ),
}


# Property types are recorded by operation, never inferred from a field name.
# Closed envelopes cover every declared property; the two asynchronous
# operations also receive explicit types and variant requirements while their
# top-level envelope remains permissive for forward-compatible metadata.
_OPENAPI_EXPLICIT_PROPERTY_SCHEMAS: dict[tuple[str, str], dict[str, dict[str, object]]] = {
    ("GET", "/healthz"): _typed_properties(objects=("services",), strings=("status", "environment")),
    ("POST", "/v0/context/compile"): _typed_properties(
        objects=("context_pack", "metadata"),
        integers=("trace_event_count",),
        strings=("trace_id",),
    ),
    ("POST", "/v0/responses"): _typed_properties(objects=("assistant", "detail", "metadata", "response_job", "trace")),
    ("POST", "/v0/memories/admit"): _typed_properties(
        objects=("open_loop",),
        nullable_objects=("memory", "revision"),
        strings=("decision", "reason"),
    ),
    ("POST", "/v0/vnext/projects"): _typed_properties(objects=("project",)),
    ("GET", "/v0/vnext/projects"): _typed_properties(
        object_arrays=("items",), string_arrays=("order",), integers=("count",)
    ),
    ("GET", "/v0/vnext/connectors"): _typed_properties(
        object_arrays=("items",), string_arrays=("order",), integers=("count",)
    ),
    ("GET", "/v0/vnext/connectors/{connector_name}/status"): _typed_properties(
        objects=("config", "health"), object_arrays=("recent_captures", "recent_failures")
    ),
    ("POST", "/v0/vnext/sources/{source_id}/review"): _typed_properties(
        objects=("source", "trace"), booleans=("archived",)
    ),
    ("POST", "/v0/vnext/memories/{memory_id}/review"): _typed_properties(
        objects=("memory",), nullable_objects=("consolidation_acceptance",)
    ),
    ("POST", "/v0/vnext/memory-proposals"): _typed_properties(
        objects=("policy_decision", "proposal"), booleans=("review_required",)
    ),
    ("GET", "/v0/vnext/artifacts"): _typed_properties(
        object_arrays=("items",), string_arrays=("order",), integers=("count",)
    ),
    ("GET", "/v0/vnext/quality-evals"): _typed_properties(
        objects=("export",),
        object_arrays=("items",),
        string_arrays=("order",),
        integers=("count",),
    ),
    ("POST", "/v0/vnext/artifacts/{artifact_id}/export"): _typed_properties(strings=("artifact_id", "output_path")),
    ("POST", "/v0/vnext/open-loops"): _typed_properties(objects=("open_loop",)),
    ("GET", "/v0/vnext/settings/brain-charter"): _typed_properties(objects=("brain_charter",)),
    ("PUT", "/v0/vnext/settings/brain-charter"): _typed_properties(objects=("brain_charter",)),
    ("GET", "/v0/vnext/scheduler/status"): _typed_properties(objects=("daemon",)),
    ("GET", "/v0/vnext/scheduler/runs"): _typed_properties(object_arrays=("items",), integers=("count",)),
    ("GET", "/v0/vnext/scheduler/failures"): _typed_properties(object_arrays=("items",), integers=("count",)),
    ("GET", "/v0/vnext/agents/policy-telemetry"): _typed_properties(objects=("summary",)),
    ("PATCH", "/v0/vnext/scheduler/workflows/{workflow_type}"): _typed_properties(
        objects=("policy_decision", "workflow")
    ),
    ("POST", "/v0/vnext/scheduler/workflows/{workflow_type}/run-now"): _typed_properties(objects=("policy_decision",)),
    ("POST", "/v0/vnext/scheduler/run-due"): _typed_properties(objects=("policy_decision",)),
    ("POST", "/v0/vnext/open-loops/extract"): _typed_properties(
        object_arrays=("open_loops",), integers=("created_count",)
    ),
    ("POST", "/v1/auth/magic-link/start"): _typed_properties(objects=("challenge", "delivery")),
    ("POST", "/v1/auth/logout"): _typed_properties(strings=("status",)),
    ("POST", "/v1/workspaces"): _typed_properties(objects=("workspace",)),
    ("GET", "/v1/workspaces/current"): _typed_properties(objects=("workspace",)),
    ("POST", "/v1/workspaces/bootstrap"): _typed_properties(
        objects=("bootstrap", "preferences", "workspace"),
        string_arrays=("feature_flags",),
        strings=("telegram_state",),
    ),
    ("GET", "/v1/workspaces/bootstrap/status"): _typed_properties(
        objects=("bootstrap", "workspace"),
        string_arrays=("feature_flags",),
        strings=("telegram_state",),
    ),
    ("POST", "/v1/providers"): _typed_properties(objects=("capabilities", "provider")),
    ("POST", "/v1/providers/ollama/register"): _typed_properties(objects=("capabilities", "provider")),
    ("POST", "/v1/providers/llamacpp/register"): _typed_properties(objects=("capabilities", "provider")),
    ("POST", "/v1/providers/vllm/register"): _typed_properties(objects=("capabilities", "provider")),
    ("POST", "/v1/providers/azure/register"): _typed_properties(objects=("capabilities", "provider")),
    ("GET", "/v1/providers"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("GET", "/v1/providers/{provider_id}"): _typed_properties(objects=("capabilities", "provider")),
    ("PATCH", "/v1/providers/{provider_id}"): _typed_properties(objects=("capabilities", "provider")),
    ("POST", "/v1/providers/test"): _typed_properties(objects=("capabilities", "provider", "result")),
    ("GET", "/v1/model-packs"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("GET", "/v1/model-packs/{pack_id}"): _typed_properties(objects=("model_pack",)),
    ("POST", "/v1/model-packs"): _typed_properties(objects=("model_pack",)),
    ("POST", "/v1/model-packs/{pack_id}/bind"): _typed_properties(objects=("binding",)),
    ("GET", "/v1/workspaces/{workspace_id}/model-pack-binding"): _typed_properties(nullable_objects=("binding",)),
    ("POST", "/v1/runtime/invoke"): _typed_properties(
        objects=("assistant", "detail", "metadata", "response_job", "trace")
    ),
    ("POST", "/v1/devices/link/start"): _typed_properties(objects=("challenge",)),
    ("POST", "/v1/devices/link/confirm"): _typed_properties(objects=("device",)),
    ("GET", "/v1/devices"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("DELETE", "/v1/devices/{device_id}"): _typed_properties(objects=("device",)),
    ("GET", "/v1/preferences"): _typed_properties(objects=("preferences",)),
    ("PATCH", "/v1/preferences"): _typed_properties(objects=("preferences",)),
    ("GET", "/v1/admin/hosted/workspaces"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("GET", "/v1/admin/hosted/delivery-receipts"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("GET", "/v1/admin/hosted/incidents"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("GET", "/v1/admin/hosted/rollout-flags"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("PATCH", "/v1/admin/hosted/rollout-flags"): _typed_properties(
        objects=("summary",), object_arrays=("items", "updated")
    ),
    ("GET", "/v1/admin/hosted/analytics"): _typed_properties(objects=("analytics",)),
    ("POST", "/v1/channels/telegram/link/start"): _typed_properties(
        objects=("challenge", "instructions"), strings=("workspace_id",)
    ),
    ("POST", "/v1/channels/telegram/link/confirm"): _typed_properties(objects=("challenge", "identity")),
    ("POST", "/v1/channels/telegram/unlink"): _typed_properties(objects=("identity",)),
    ("POST", "/v1/channels/telegram/webhook"): _typed_properties(objects=("ingest",), strings=("status",)),
    ("GET", "/v1/channels/telegram/messages"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("GET", "/v1/channels/telegram/threads"): _typed_properties(objects=("summary",), object_arrays=("items",)),
    ("POST", "/v1/channels/telegram/messages/{message_id}/dispatch"): _typed_properties(objects=("message", "receipt")),
    ("GET", "/v1/channels/telegram/delivery-receipts"): _typed_properties(
        objects=("summary",), object_arrays=("items",)
    ),
    ("GET", "/v1/channels/telegram/recall"): _typed_properties(objects=("recall",), strings=("workspace_id",)),
    ("GET", "/v1/channels/telegram/resume"): _typed_properties(objects=("resume",), strings=("workspace_id",)),
    ("GET", "/v1/channels/telegram/open-loops"): _typed_properties(objects=("open_loops",), strings=("workspace_id",)),
}


# The remaining permissive envelopes are still typed by literal operation
# key. They intentionally keep optional fields/additional properties because
# their full envelope is helper- or variable-backed, but their declared
# properties are not guessed from spelling conventions.
_OPENAPI_EXPLICIT_PROPERTY_SCHEMAS.update(
    {
        ("GET", "/v0/traces"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/traces/{trace_id}"): _typed_properties(objects=("trace",), strings=("status",)),
        ("GET", "/v0/traces/{trace_id}/events"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/open-loops"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/open-loops/{open_loop_id}"): _typed_properties(objects=("open_loop",), strings=("status",)),
        ("POST", "/v0/open-loops"): _typed_properties(objects=("open_loop",), strings=("status",)),
        ("POST", "/v0/open-loops/{open_loop_id}/status"): _typed_properties(
            objects=("open_loop",), strings=("status",)
        ),
        ("POST", "/v0/consents"): _typed_properties(objects=("consent",), strings=("status",)),
        ("GET", "/v0/consents"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v0/policies"): _typed_properties(objects=("policy",), strings=("status",)),
        ("GET", "/v0/policies"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/policies/{policy_id}"): _typed_properties(objects=("policy",), strings=("status",)),
        ("POST", "/v0/policies/evaluate"): _typed_properties(objects=("policy",), strings=("status",)),
        ("POST", "/v0/tools"): _typed_properties(objects=("tool",), strings=("status",)),
        ("GET", "/v0/tools"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v0/tools/allowlist/evaluate"): _typed_properties(objects=("allowlist",), strings=("status",)),
        ("POST", "/v0/tools/route"): _typed_properties(objects=("tool",), strings=("status",)),
        ("POST", "/v0/approvals/requests"): _typed_properties(objects=("request",), strings=("status",)),
        ("GET", "/v0/approvals"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/approvals/{approval_id}"): _typed_properties(objects=("approval",), strings=("status",)),
        ("POST", "/v0/approvals/{approval_id}/approve"): _typed_properties(objects=("approval",), strings=("status",)),
        ("POST", "/v0/approvals/{approval_id}/reject"): _typed_properties(objects=("approval",), strings=("status",)),
        ("POST", "/v0/approvals/{approval_id}/execute"): _typed_properties(objects=("approval",), strings=("status",)),
        ("GET", "/v0/tasks"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/tasks/{task_id}"): _typed_properties(objects=("task",), strings=("status",)),
        ("POST", "/v0/tasks/{task_id}/runs"): _typed_properties(objects=("run",), strings=("status",)),
        ("GET", "/v0/tasks/{task_id}/runs"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/task-runs/{task_run_id}"): _typed_properties(objects=("task_run",), strings=("status",)),
        ("POST", "/v0/task-runs/{task_run_id}/tick"): _typed_properties(objects=("task_run",), strings=("status",)),
        ("POST", "/v0/task-runs/{task_run_id}/pause"): _typed_properties(objects=("task_run",), strings=("status",)),
        ("POST", "/v0/task-runs/{task_run_id}/resume"): _typed_properties(objects=("task_run",), strings=("status",)),
        ("POST", "/v0/task-runs/{task_run_id}/cancel"): _typed_properties(objects=("task_run",), strings=("status",)),
        ("POST", "/v0/gmail-accounts"): _typed_properties(objects=("gmail_account",), strings=("status",)),
        ("GET", "/v0/gmail-accounts"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/gmail-accounts/{gmail_account_id}"): _typed_properties(
            objects=("gmail_account",), strings=("status",)
        ),
        ("POST", "/v0/gmail-accounts/{gmail_account_id}/messages/{provider_message_id}/ingest"): _typed_properties(
            objects=("ingest",), strings=("status",)
        ),
        ("POST", "/v0/calendar-accounts"): _typed_properties(objects=("calendar_account",), strings=("status",)),
        ("GET", "/v0/calendar-accounts"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/calendar-accounts/{calendar_account_id}"): _typed_properties(
            objects=("calendar_account",), strings=("status",)
        ),
        ("GET", "/v0/calendar-accounts/{calendar_account_id}/events"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v0/calendar-accounts/{calendar_account_id}/events/{provider_event_id}/ingest"): _typed_properties(
            objects=("ingest",), strings=("status",)
        ),
        ("POST", "/v0/tasks/{task_id}/workspace"): _typed_properties(objects=("workspace",), strings=("status",)),
        ("GET", "/v0/task-workspaces"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/task-workspaces/{task_workspace_id}"): _typed_properties(
            objects=("task_workspace",), strings=("status",)
        ),
        ("GET", "/v0/tasks/{task_id}/steps"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/task-steps/{task_step_id}"): _typed_properties(objects=("task_step",), strings=("status",)),
        ("POST", "/v0/task-workspaces/{task_workspace_id}/artifacts"): _typed_properties(
            objects=("artifact",), strings=("status",)
        ),
        ("GET", "/v0/task-artifacts"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/task-artifacts/{task_artifact_id}"): _typed_properties(
            objects=("task_artifact",), strings=("status",)
        ),
        ("POST", "/v0/task-artifacts/{task_artifact_id}/ingest"): _typed_properties(
            objects=("ingest",), strings=("status",)
        ),
        ("GET", "/v0/task-artifacts/{task_artifact_id}/chunks"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v0/tasks/{task_id}/artifact-chunks/retrieve"): _typed_properties(
            objects=("retrieve",), strings=("status",)
        ),
        ("POST", "/v0/task-artifacts/{task_artifact_id}/chunks/retrieve"): _typed_properties(
            objects=("retrieve",), strings=("status",)
        ),
        ("POST", "/v0/tasks/{task_id}/artifact-chunks/semantic-retrieval"): _typed_properties(
            objects=("semantic_retrieval",), strings=("status",)
        ),
        ("POST", "/v0/task-artifacts/{task_artifact_id}/chunks/semantic-retrieval"): _typed_properties(
            objects=("semantic_retrieval",), strings=("status",)
        ),
        ("POST", "/v0/tasks/{task_id}/steps"): _typed_properties(objects=("step",), strings=("status",)),
        ("POST", "/v0/task-steps/{task_step_id}/transition"): _typed_properties(
            objects=("task_step",), strings=("status",)
        ),
        ("POST", "/v0/execution-budgets"): _typed_properties(objects=("execution_budget",), strings=("status",)),
        ("GET", "/v0/execution-budgets"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/execution-budgets/{execution_budget_id}"): _typed_properties(
            objects=("execution_budget",), strings=("status",)
        ),
        ("POST", "/v0/execution-budgets/{execution_budget_id}/deactivate"): _typed_properties(
            objects=("execution_budget",), strings=("status",)
        ),
        ("POST", "/v0/execution-budgets/{execution_budget_id}/supersede"): _typed_properties(
            objects=("execution_budget",), strings=("status",)
        ),
        ("GET", "/v0/tool-executions"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/tool-executions/{execution_id}"): _typed_properties(
            objects=("tool_execution",), strings=("status",)
        ),
        ("GET", "/v0/tools/{tool_id}"): _typed_properties(objects=("tool",), strings=("status",)),
        ("POST", "/v0/memories/extract-explicit-preferences"): _typed_properties(
            objects=("summary",), object_arrays=("admissions", "candidates")
        ),
        ("POST", "/v0/open-loops/extract-explicit-commitments"): _typed_properties(
            objects=("summary",), object_arrays=("admissions", "candidates")
        ),
        ("POST", "/v0/memories/capture-explicit-signals"): _typed_properties(
            objects=("commitments", "preferences", "summary")
        ),
        ("POST", "/v0/continuity/captures"): _typed_properties(objects=("capture",), strings=("status",)),
        ("GET", "/v0/vnext/workspace"): _typed_properties(objects=("workspace",), strings=("status",)),
        ("POST", "/v0/vnext/sources"): _typed_properties(objects=("source",), strings=("status",)),
        ("GET", "/v0/vnext/connectors/health"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("PATCH", "/v0/vnext/connectors/{connector_name}/config"): _typed_properties(
            objects=("config",), strings=("status",)
        ),
        ("POST", "/v0/vnext/connectors/{connector_name}/sync"): _typed_properties(
            objects=("connector",), strings=("status",)
        ),
        ("POST", "/v0/vnext/connectors/telegram/sync"): _typed_properties(objects=("telegram",), strings=("status",)),
        ("POST", "/v0/vnext/connectors/local-folder/sync"): _typed_properties(
            objects=("local_folder",), strings=("status",)
        ),
        ("POST", "/v0/vnext/connectors/browser-clipper/capture"): _typed_properties(
            objects=("browser_clipper",), strings=("status",)
        ),
        ("POST", "/v0/vnext/agents/ingest-output"): _typed_properties(objects=("ingest_output",), strings=("status",)),
        ("GET", "/v0/vnext/dogfooding"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/vnext/doctor"): _typed_properties(objects=("doctor",), strings=("status",)),
        ("POST", "/v0/vnext/doctor/run"): _typed_properties(objects=("run",), strings=("status",)),
        ("POST", "/v0/vnext/artifacts/{artifact_id}/insight-feedback"): _typed_properties(
            objects=("insight_feedback",), strings=("status",)
        ),
        ("GET", "/v0/vnext/sources/{source_id}"): _typed_properties(objects=("source",), strings=("status",)),
        ("GET", "/v0/vnext/traces/sources/{source_id}"): _typed_properties(objects=("source",), strings=("status",)),
        ("GET", "/v0/vnext/traces/artifacts/{artifact_id}"): _typed_properties(
            objects=("artifact",), strings=("status",)
        ),
        ("DELETE", "/v0/vnext/sources/{source_id}"): _typed_properties(strings=("status", "source_id")),
        ("POST", "/v0/vnext/context-packs"): _typed_properties(objects=("context_pack",), strings=("status",)),
        ("GET", "/v0/vnext/context-tree"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v0/vnext/memories/commit"): _typed_properties(objects=("memory",), strings=("status",)),
        ("POST", "/v0/vnext/memories/confirm"): _typed_properties(objects=("memory",), strings=("status",)),
        ("POST", "/v0/vnext/memories/undo"): _typed_properties(objects=("memory",), strings=("status",)),
        ("POST", "/v0/vnext/memories/correct"): _typed_properties(objects=("memory",), strings=("status",)),
        ("POST", "/v0/vnext/memories/forget"): _typed_properties(objects=("memory",), strings=("status",)),
        ("POST", "/v0/vnext/memories/expire"): _typed_properties(objects=("memory",), strings=("status",)),
        ("POST", "/v0/vnext/memories/unexpire"): _typed_properties(objects=("memory",), strings=("status",)),
        ("POST", "/v0/vnext/memories/accept-consolidation"): _typed_properties(
            objects=("accept_consolidation",), strings=("status",)
        ),
        ("POST", "/v0/vnext/memories/redact"): _typed_properties(objects=("memory",), strings=("status",)),
        ("GET", "/v0/vnext/memories/recent-commits"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/vnext/memories/{memory_id}/audit"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v0/vnext/artifacts/generate/daily-brief"): _artifact_response_properties(),
        ("POST", "/v0/vnext/artifacts/generate/weekly-synthesis"): _artifact_response_properties(),
        ("POST", "/v0/vnext/artifacts/generate/connections"): _artifact_response_properties(),
        ("POST", "/v0/vnext/artifacts/generate/contradictions"): _artifact_response_properties(),
        ("POST", "/v0/vnext/queue/tasks"): _typed_properties(objects=("task",), strings=("status",)),
        ("POST", "/v0/vnext/queue/process-next"): _typed_properties(objects=("queue",), strings=("status",)),
        ("GET", "/v0/vnext/artifacts/{artifact_id}"): _typed_properties(objects=("artifact",), strings=("status",)),
        ("POST", "/v0/vnext/artifacts/{artifact_id}/review"): _typed_properties(
            objects=("artifact",), strings=("status",)
        ),
        ("POST", "/v0/vnext/artifacts/{artifact_id}/quality-ratings"): _typed_properties(
            objects=("quality_rating",), strings=("status",)
        ),
        ("POST", "/v0/vnext/graph/edges/{edge_id}/review"): _typed_properties(objects=("edge",), strings=("status",)),
        ("GET", "/v0/vnext/graph/neighborhood/{target_id}"): _typed_properties(
            objects=("neighborhood",), strings=("status",)
        ),
        ("POST", "/v0/vnext/beliefs/{belief_id}/review"): _typed_properties(objects=("belief",), strings=("status",)),
        ("GET", "/v0/vnext/beliefs/{belief_id}/state"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v0/vnext/projects/update-candidates"): _artifact_response_properties(),
        ("POST", "/v0/vnext/projects/update-candidates/{artifact_id}/review"): _artifact_response_properties(),
        ("GET", "/v0/vnext/projects/{project_id}/dashboard"): _typed_properties(
            objects=("dashboard",), strings=("status",)
        ),
        ("POST", "/v0/vnext/scheduler/pause"): _typed_properties(objects=("scheduler",), strings=("status",)),
        ("POST", "/v0/vnext/scheduler/resume"): _typed_properties(objects=("scheduler",), strings=("status",)),
        ("POST", "/v0/vnext/open-loops/{loop_id}/review"): _typed_properties(
            objects=("open_loop",), strings=("status",)
        ),
        ("POST", "/v0/continuity/captures/candidates"): _typed_properties(objects=("candidate",), strings=("status",)),
        ("POST", "/v0/continuity/captures/commit"): _typed_properties(objects=("capture",), strings=("status",)),
        ("POST", "/v1/memory/operations/candidates/generate"): _typed_properties(
            objects=("candidate",), strings=("status",)
        ),
        ("GET", "/v1/memory/operations/candidates"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v1/memory/operations/commit"): _typed_properties(objects=("operation",), strings=("status",)),
        ("GET", "/v1/memory/operations"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/continuity/captures"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/continuity/captures/{capture_event_id}"): _typed_properties(
            objects=("capture",), strings=("status",)
        ),
        ("POST", "/v0/continuity/review-queue/{continuity_object_id}/corrections"): _typed_properties(
            objects=("correction",), strings=("status",)
        ),
        ("GET", "/v0/task-briefs/{task_brief_id}"): _typed_properties(objects=("task_brief",), strings=("status",)),
        ("GET", "/v0/memories"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/memories/review-queue"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/memories/quality-gate"): _typed_properties(objects=("quality_gate",), strings=("status",)),
        ("GET", "/v0/memories/evaluation-summary"): _typed_properties(
            objects=("evaluation_summary",), strings=("status",)
        ),
        ("POST", "/v0/memories/semantic-retrieval"): _typed_properties(
            objects=("semantic_retrieval",), strings=("status",)
        ),
        ("GET", "/v0/memories/{memory_id}"): _typed_properties(objects=("memory",), strings=("status",)),
        ("GET", "/v0/memories/{memory_id}/revisions"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v0/memories/{memory_id}/labels"): _typed_properties(objects=("label",), strings=("status",)),
        ("GET", "/v0/memories/{memory_id}/labels"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v0/embedding-configs"): _typed_properties(objects=("embedding_config",), strings=("status",)),
        ("GET", "/v0/embedding-configs"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v0/memory-embeddings"): _typed_properties(objects=("memory_embedding",), strings=("status",)),
        ("POST", "/v0/task-artifact-chunk-embeddings"): _typed_properties(
            objects=("task_artifact_chunk_embedding",), strings=("status",)
        ),
        ("GET", "/v0/memories/{memory_id}/embeddings"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("GET", "/v0/task-artifacts/{task_artifact_id}/chunk-embeddings"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("GET", "/v0/task-artifact-chunks/{task_artifact_chunk_id}/embeddings"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("GET", "/v0/memory-embeddings/{memory_embedding_id}"): _typed_properties(
            objects=("memory_embedding",), strings=("status",)
        ),
        ("GET", "/v0/task-artifact-chunk-embeddings/{task_artifact_chunk_embedding_id}"): _typed_properties(
            objects=("task_artifact_chunk_embedding",), strings=("status",)
        ),
        ("POST", "/v0/entities"): _typed_properties(objects=("entity",), strings=("status",)),
        ("POST", "/v0/entity-edges"): _typed_properties(objects=("entity_edge",), strings=("status",)),
        ("GET", "/v0/entities"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/entities/{entity_id}/edges"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v0/entities/{entity_id}"): _typed_properties(objects=("entity",), strings=("status",)),
        ("POST", "/v1/auth/magic-link/verify"): {
            "magic_link": {"type": "object", "additionalProperties": True},
            "status": {"type": "string"},
            "expires_at": {"type": "string", "format": "date-time"},
        },
        ("GET", "/v1/auth/session"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v1/admin/hosted/overview"): _typed_properties(objects=("overview",), strings=("status",)),
        ("GET", "/v1/admin/hosted/design-partners/dashboard"): _typed_properties(
            objects=("dashboard",), strings=("status",)
        ),
        ("GET", "/v1/admin/hosted/design-partners"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v1/admin/hosted/design-partners"): _typed_properties(
            objects=("design_partner",), strings=("status",)
        ),
        ("GET", "/v1/admin/hosted/design-partners/{design_partner_id}"): _typed_properties(
            objects=("design_partner",), strings=("status",)
        ),
        ("PATCH", "/v1/admin/hosted/design-partners/{design_partner_id}"): _typed_properties(
            objects=("design_partner",), strings=("status",)
        ),
        ("POST", "/v1/admin/hosted/design-partners/{design_partner_id}/workspaces"): _typed_properties(
            objects=("workspace",), strings=("status",)
        ),
        ("POST", "/v1/admin/hosted/design-partners/{design_partner_id}/feedback"): _typed_properties(
            objects=("feedback",), strings=("status",)
        ),
        ("GET", "/v1/admin/hosted/rate-limits"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("GET", "/v1/channels/telegram/status"): _typed_properties(objects=("telegram",), strings=("status",)),
        ("GET", "/v1/channels/telegram/notification-preferences"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("PATCH", "/v1/channels/telegram/notification-preferences"): _typed_properties(
            objects=("notification_preference",), strings=("status",)
        ),
        ("GET", "/v1/channels/telegram/daily-brief"): _typed_properties(objects=("daily_brief",), strings=("status",)),
        ("POST", "/v1/channels/telegram/daily-brief/deliver"): _typed_properties(
            objects=("daily_brief",), strings=("status",)
        ),
        ("GET", "/v1/channels/telegram/open-loop-prompts"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v1/channels/telegram/open-loop-prompts/{prompt_id}/deliver"): _typed_properties(
            objects=("open_loop_prompt",), strings=("status",)
        ),
        ("GET", "/v1/channels/telegram/scheduler/jobs"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v1/channels/telegram/messages/{message_id}/handle"): _typed_properties(
            objects=("message",), strings=("status",)
        ),
        ("GET", "/v1/channels/telegram/messages/{message_id}/result"): _typed_properties(
            objects=("summary",), object_arrays=("items",)
        ),
        ("POST", "/v1/channels/telegram/open-loops/{open_loop_id}/review-action"): _typed_properties(
            objects=("review_action",), strings=("status",)
        ),
        ("GET", "/v1/channels/telegram/approvals"): _typed_properties(objects=("summary",), object_arrays=("items",)),
        ("POST", "/v1/channels/telegram/approvals/{approval_id}/approve"): _typed_properties(
            objects=("approval",), strings=("status",)
        ),
        ("POST", "/v1/channels/telegram/approvals/{approval_id}/reject"): _typed_properties(
            objects=("approval",), strings=("status",)
        ),
    }
)


for _operation_key, _property_schemas in _OPENAPI_EXPLICIT_PROPERTY_SCHEMAS.items():
    if _operation_key not in OPENAPI_OPERATION_RESPONSE_SCHEMAS:
        raise RuntimeError(f"OpenAPI typed property registry has unknown operation {_operation_key!r}")
    _component_name, _component_schema = OPENAPI_OPERATION_RESPONSE_SCHEMAS[_operation_key]
    _declared_properties = _component_schema.get("properties")
    if not isinstance(_declared_properties, dict):  # pragma: no cover - construction invariant
        raise RuntimeError(f"OpenAPI component {_component_name} has no properties")
    if set(_property_schemas) != set(_declared_properties):
        raise RuntimeError(
            f"OpenAPI typed properties drifted for {_operation_key!r}; "
            f"declared={sorted(_declared_properties)}, typed={sorted(_property_schemas)}"
        )
    _component_schema["properties"] = _property_schemas


_OPENAPI_POLYMORPHIC_VARIANTS = [
    {
        "type": "object",
        "required": ["assistant", "metadata", "trace"],
        "properties": {
            "assistant": {"type": "object", "additionalProperties": True},
            "metadata": {"type": "object", "additionalProperties": True},
            "trace": {"type": "object", "additionalProperties": True},
        },
    },
    {
        "type": "object",
        "required": ["detail", "response_job"],
        "properties": {
            "detail": {"type": "object", "additionalProperties": True},
            "response_job": {"type": "object", "additionalProperties": True},
        },
    },
]
for _operation_key in (("POST", "/v0/responses"), ("POST", "/v1/runtime/invoke")):
    OPENAPI_OPERATION_RESPONSE_SCHEMAS[_operation_key][1]["oneOf"] = _OPENAPI_POLYMORPHIC_VARIANTS


_closed_operations = {
    operation_key
    for operation_key, (_component_name, schema) in OPENAPI_OPERATION_RESPONSE_SCHEMAS.items()
    if schema.get("additionalProperties") is False
}
_untyped_closed_operations = _closed_operations - set(_OPENAPI_EXPLICIT_PROPERTY_SCHEMAS)
if _untyped_closed_operations:
    raise RuntimeError(
        f"OpenAPI closed operations require explicit property types; missing={sorted(_untyped_closed_operations)}"
    )


OPENAPI_INTENTIONALLY_POLYMORPHIC_OPERATIONS: dict[tuple[str, str], str] = {
    ("POST", "/v0/responses"): ("Returns a completed response for terminal work or an accepted in-progress job."),
    ("POST", "/v1/runtime/invoke"): (
        "Returns a completed invocation for terminal work or an accepted in-progress job."
    ),
}


# These classifications are derived from the literal registry above and are
# exported so OpenAPI generation/tests can fail closed when a route changes
# verification state. Closed schemas are backed by statically visible success
# payloads; open schemas remain deliberately permissive until their helper or
# variable-backed envelopes have equivalent source/test evidence.
OPENAPI_SOURCE_VERIFIED_OPERATIONS = frozenset(
    operation_key
    for operation_key, (_component_name, schema) in OPENAPI_OPERATION_RESPONSE_SCHEMAS.items()
    if schema.get("additionalProperties") is False
)
OPENAPI_OPEN_RESPONSE_OPERATIONS = frozenset(OPENAPI_OPERATION_RESPONSE_SCHEMAS) - (OPENAPI_SOURCE_VERIFIED_OPERATIONS)
