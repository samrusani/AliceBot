export type ApiSource = "live" | "fixture";
export type PageDataMode = "live" | "fixture" | "mixed";

export type ApiConfig = {
  apiBaseUrl: string;
  userId: string;
  defaultThreadId: string;
  defaultToolId: string;
};

export type ThreadItem = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ThreadSessionItem = {
  id: string;
  thread_id: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

export type ThreadEventItem = {
  id: string;
  thread_id: string;
  session_id: string | null;
  sequence_no: number;
  kind: string;
  payload: unknown;
  created_at: string;
};

export type ThreadCreatePayload = {
  user_id: string;
  title: string;
};

export type ThreadListSummary = {
  total_count: number;
  order: string[];
};

export type ThreadSessionListSummary = {
  thread_id: string;
  total_count: number;
  order: string[];
};

export type ThreadEventListSummary = {
  thread_id: string;
  total_count: number;
  order: string[];
};

export type ToolRoutingReason = {
  code: string;
  source: string;
  message: string;
  tool_id: string | null;
  policy_id: string | null;
  consent_key: string | null;
};

export type ToolRecord = {
  id: string;
  tool_key: string;
  name: string;
  description: string;
  version: string;
  metadata_version: string;
  active: boolean;
  tags: string[];
  action_hints: string[];
  scope_hints: string[];
  domain_hints: string[];
  risk_hints: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type JsonObject = Record<string, unknown>;

export type GovernedRequestRecord = {
  thread_id: string;
  tool_id: string;
  action: string;
  scope: string;
  domain_hint: string | null;
  risk_hint: string | null;
  attributes: Record<string, unknown>;
};

export type ApprovalItem = {
  id: string;
  thread_id: string;
  task_step_id: string | null;
  status: string;
  request: GovernedRequestRecord;
  tool: ToolRecord;
  routing: {
    decision: string;
    reasons: ToolRoutingReason[];
    trace: {
      trace_id: string;
      trace_event_count: number;
    };
  };
  created_at: string;
  resolution: {
    resolved_at: string;
    resolved_by_user_id: string;
  } | null;
};

export type TaskItem = {
  id: string;
  thread_id: string;
  tool_id: string;
  status: string;
  request: GovernedRequestRecord;
  tool: ToolRecord;
  latest_approval_id: string | null;
  latest_execution_id: string | null;
  created_at: string;
  updated_at: string;
};

export type TaskStepItem = {
  id: string;
  task_id: string;
  sequence_no: number;
  kind: string;
  status: string;
  request: GovernedRequestRecord;
  outcome: {
    routing_decision: string;
    approval_id: string | null;
    approval_status: string | null;
    execution_id: string | null;
    execution_status: string | null;
    blocked_reason: string | null;
  };
  lineage: {
    parent_step_id: string | null;
    source_approval_id: string | null;
    source_execution_id: string | null;
  };
  trace: {
    trace_id: string;
    trace_kind: string;
  };
  created_at: string;
  updated_at: string;
};

export type TaskStepListSummary = {
  task_id: string;
  total_count: number;
  latest_sequence_no: number | null;
  latest_status: string | null;
  next_sequence_no: number;
  append_allowed: boolean;
  order: string[];
};

export type ToolExecutionResult = {
  handler_key: string | null;
  status: string;
  output: JsonObject | null;
  reason: string | null;
  budget_decision?: JsonObject;
};

export type ToolExecutionItem = {
  id: string;
  approval_id: string;
  task_step_id: string;
  thread_id: string;
  tool_id: string;
  trace_id: string;
  request_event_id: string | null;
  result_event_id: string | null;
  status: string;
  handler_key: string | null;
  request: GovernedRequestRecord;
  tool: ToolRecord;
  result: ToolExecutionResult;
  executed_at: string;
};

export type ApprovalExecutionResponse = {
  request: {
    approval_id: string;
    task_step_id: string;
  };
  approval: ApprovalItem;
  tool: ToolRecord;
  result: ToolExecutionResult;
  events: {
    request_event_id: string;
    request_sequence_no: number;
    result_event_id: string;
    result_sequence_no: number;
  } | null;
  trace: {
    trace_id: string;
    trace_event_count: number;
  };
};

export type TraceReviewSummaryItem = {
  id: string;
  thread_id: string;
  kind: string;
  compiler_version: string;
  status: string;
  created_at: string;
  trace_event_count: number;
};

export type TraceReviewItem = TraceReviewSummaryItem & {
  limits: Record<string, unknown>;
};

export type TraceReviewEventItem = {
  id: string;
  trace_id: string;
  sequence_no: number;
  kind: string;
  payload: unknown;
  created_at: string;
};

export type TraceReviewListSummary = {
  total_count: number;
  order: string[];
};

export type TraceReviewEventListSummary = {
  trace_id: string;
  total_count: number;
  order: string[];
};

export type MemoryReviewStatus = "active" | "deleted";
export type MemoryReviewStatusFilter = MemoryReviewStatus | "all";
export type MemoryReviewLabelValue =
  | "correct"
  | "incorrect"
  | "outdated"
  | "insufficient_evidence";

export type MemoryReviewRecord = {
  id: string;
  memory_key: string;
  value: unknown;
  status: MemoryReviewStatus;
  source_event_ids: string[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type MemoryReviewListSummary = {
  status: MemoryReviewStatusFilter;
  limit: number;
  returned_count: number;
  total_count: number;
  has_more: boolean;
  order: string[];
};

export type MemoryRevisionReviewRecord = {
  id: string;
  memory_id: string;
  sequence_no: number;
  action: string;
  memory_key: string;
  previous_value: unknown | null;
  new_value: unknown | null;
  source_event_ids: string[];
  created_at: string;
};

export type MemoryRevisionReviewListSummary = {
  memory_id: string;
  limit: number;
  returned_count: number;
  total_count: number;
  has_more: boolean;
  order: string[];
};

export type MemoryReviewLabelCounts = {
  correct: number;
  incorrect: number;
  outdated: number;
  insufficient_evidence: number;
};

export type MemoryReviewLabelRecord = {
  id: string;
  memory_id: string;
  reviewer_user_id: string;
  label: MemoryReviewLabelValue;
  note: string | null;
  created_at: string;
};

export type MemoryReviewLabelSummary = {
  memory_id: string;
  total_count: number;
  counts_by_label: MemoryReviewLabelCounts;
  order: MemoryReviewLabelValue[];
};

export type MemoryReviewQueueItem = {
  id: string;
  memory_key: string;
  value: unknown;
  status: "active";
  source_event_ids: string[];
  created_at: string;
  updated_at: string;
};

export type MemoryReviewQueueSummary = {
  memory_status: "active";
  review_state: "unlabeled";
  limit: number;
  returned_count: number;
  total_count: number;
  has_more: boolean;
  order: string[];
};

export type MemoryEvaluationSummary = {
  total_memory_count: number;
  active_memory_count: number;
  deleted_memory_count: number;
  labeled_memory_count: number;
  unlabeled_memory_count: number;
  total_label_row_count: number;
  label_row_counts_by_value: MemoryReviewLabelCounts;
  label_value_order: MemoryReviewLabelValue[];
};

export type MemoryReviewLabelPayload = {
  user_id: string;
  label: MemoryReviewLabelValue;
  note?: string | null;
};

export type ApprovalRequestPayload = {
  user_id: string;
  thread_id: string;
  tool_id: string;
  action: string;
  scope: string;
  domain_hint: string | null;
  risk_hint: string | null;
  attributes: Record<string, unknown>;
};

export type ApprovalRequestResponse = {
  request: GovernedRequestRecord;
  decision: string;
  tool: ToolRecord;
  reasons: ToolRoutingReason[];
  task: TaskItem;
  approval: ApprovalItem | null;
  routing_trace: {
    trace_id: string;
    trace_event_count: number;
  };
  trace: {
    trace_id: string;
    trace_event_count: number;
  };
};

export type ThreadWorkflowState = {
  approval: ApprovalItem | null;
  task: TaskItem | null;
  execution: ToolExecutionItem | null;
};

export type ApprovalResolutionResponse = {
  approval: ApprovalItem;
  trace: {
    trace_id: string;
    trace_event_count: number;
  };
};

export type AssistantResponsePayload = {
  user_id: string;
  thread_id: string;
  message: string;
  max_sessions?: number;
  max_events?: number;
  max_memories?: number;
  max_entities?: number;
  max_entity_edges?: number;
};

export type AssistantResponseTrace = {
  compile_trace_id: string;
  compile_trace_event_count: number;
  response_trace_id: string;
  response_trace_event_count: number;
};

export type AssistantResponseSuccess = {
  assistant: {
    event_id: string;
    sequence_no: number;
    text: string;
    model_provider: string;
    model: string;
  };
  trace: AssistantResponseTrace;
};

export type RequestHistoryEntry = {
  id: string;
  submittedAt: string;
  source: ApiSource;
  threadId: string;
  toolId: string;
  toolName: string;
  action: string;
  scope: string;
  domainHint: string | null;
  riskHint: string | null;
  attributes: Record<string, unknown>;
  decision: string;
  taskId: string;
  taskStatus: string;
  approvalId: string | null;
  approvalStatus: string | null;
  summary: string;
  reasons: string[];
  trace: {
    routingTraceId: string;
    routingTraceEventCount: number;
    requestTraceId: string;
    requestTraceEventCount: number;
  };
};

export type ResponseHistoryEntry = {
  id: string;
  submittedAt: string;
  source: ApiSource;
  threadId: string;
  message: string;
  assistantText: string;
  assistantEventId: string;
  assistantSequenceNo: number;
  modelProvider: string;
  model: string;
  summary: string;
  trace: {
    compileTraceId: string;
    compileTraceEventCount: number;
    responseTraceId: string;
    responseTraceEventCount: number;
  };
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readEnv(publicValue: string | undefined, serverValue: string | undefined) {
  if (typeof window !== "undefined") {
    return publicValue ?? "";
  }

  return publicValue ?? serverValue ?? "";
}

export function getApiConfig(): ApiConfig {
  return {
    apiBaseUrl: readEnv(
      process.env.NEXT_PUBLIC_ALICEBOT_API_BASE_URL,
      process.env.ALICEBOT_API_BASE_URL,
    ),
    userId: readEnv(process.env.NEXT_PUBLIC_ALICEBOT_USER_ID, process.env.ALICEBOT_USER_ID),
    defaultThreadId: readEnv(
      process.env.NEXT_PUBLIC_ALICEBOT_THREAD_ID,
      process.env.ALICEBOT_THREAD_ID,
    ),
    defaultToolId: readEnv(process.env.NEXT_PUBLIC_ALICEBOT_TOOL_ID, process.env.ALICEBOT_TOOL_ID),
  };
}

export function hasLiveApiConfig(config: Pick<ApiConfig, "apiBaseUrl" | "userId">) {
  return Boolean(config.apiBaseUrl && config.userId);
}

export function combinePageModes(...modes: Array<ApiSource | null | undefined>): PageDataMode {
  const presentModes = modes.filter(Boolean) as ApiSource[];
  if (presentModes.length === 0) {
    return "fixture";
  }

  const uniqueModes = Array.from(new Set(presentModes));
  if (uniqueModes.length === 1) {
    return uniqueModes[0];
  }

  return "mixed";
}

export function pageModeLabel(mode: PageDataMode) {
  if (mode === "live") {
    return "Live API";
  }

  if (mode === "mixed") {
    return "Mixed fallback";
  }

  return "Fixture-backed";
}

function compareIsoDatesDesc(left: string, right: string) {
  return new Date(right).getTime() - new Date(left).getTime();
}

function pickLatestApproval(items: ApprovalItem[]) {
  return [...items].sort((left, right) => compareIsoDatesDesc(left.created_at, right.created_at))[0] ?? null;
}

function pickLatestTask(items: TaskItem[], approval: ApprovalItem | null) {
  if (approval) {
    const linkedTask =
      [...items]
        .filter((item) => item.latest_approval_id === approval.id)
        .sort((left, right) => {
          const updatedDelta = compareIsoDatesDesc(left.updated_at, right.updated_at);
          if (updatedDelta !== 0) {
            return updatedDelta;
          }

          return compareIsoDatesDesc(left.created_at, right.created_at);
        })[0] ?? null;

    if (linkedTask) {
      return linkedTask;
    }
  }

  return [...items].sort((left, right) => {
    const updatedDelta = compareIsoDatesDesc(left.updated_at, right.updated_at);
    if (updatedDelta !== 0) {
      return updatedDelta;
    }

    return compareIsoDatesDesc(left.created_at, right.created_at);
  })[0] ?? null;
}

function pickExplicitlyLinkedExecution(
  items: ToolExecutionItem[],
  task: TaskItem | null,
  approval: ApprovalItem | null,
) {
  if (task?.latest_execution_id) {
    return items.find((item) => item.id === task.latest_execution_id) ?? null;
  }

  if (approval) {
    return (
      [...items]
        .filter((item) => item.approval_id === approval.id)
        .sort((left, right) => compareIsoDatesDesc(left.executed_at, right.executed_at))[0] ?? null
    );
  }

  return null;
}

export function deriveThreadWorkflowState(
  threadId: string,
  approvals: ApprovalItem[],
  tasks: TaskItem[],
  executions: ToolExecutionItem[],
): ThreadWorkflowState {
  const threadApprovals = approvals.filter((item) => item.thread_id === threadId);
  const approval = pickLatestApproval(threadApprovals);
  const threadTasks = tasks.filter((item) => item.thread_id === threadId);
  const task = pickLatestTask(threadTasks, approval);
  const threadExecutions = executions.filter((item) => item.thread_id === threadId);
  const execution = pickExplicitlyLinkedExecution(threadExecutions, task, approval);

  return {
    approval,
    task,
    execution,
  };
}

export function shouldExpectThreadExecutionReview(
  approval: ApprovalItem | null,
  task: TaskItem | null,
) {
  const normalizedApprovalStatus = approval?.status.trim().toLowerCase() ?? "";
  const normalizedTaskStatus = task?.status.trim().toLowerCase() ?? "";

  return Boolean(
    task?.latest_execution_id ||
      ["approved", "executed", "completed"].includes(normalizedApprovalStatus) ||
      ["executed", "completed"].includes(normalizedTaskStatus),
  );
}

function buildApiUrl(
  apiBaseUrl: string,
  path: string,
  query?: Record<string, string | undefined>,
) {
  const url = new URL(path, `${apiBaseUrl.replace(/\/$/, "")}/`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value) {
      url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

async function requestJson<T>(
  apiBaseUrl: string,
  path: string,
  init?: RequestInit,
  query?: Record<string, string | undefined>,
): Promise<T> {
  const response = await fetch(buildApiUrl(apiBaseUrl, path, query), {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
  if (!response.ok) {
    throw new ApiError(payload?.detail ?? "Request failed", response.status);
  }

  return payload as T;
}

export function submitApprovalRequest(
  apiBaseUrl: string,
  payload: ApprovalRequestPayload,
) {
  return requestJson<ApprovalRequestResponse>(apiBaseUrl, "/v0/approvals/requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitAssistantResponse(
  apiBaseUrl: string,
  payload: AssistantResponsePayload,
) {
  return requestJson<AssistantResponseSuccess>(apiBaseUrl, "/v0/responses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createThread(apiBaseUrl: string, payload: ThreadCreatePayload) {
  return requestJson<{ thread: ThreadItem }>(apiBaseUrl, "/v0/threads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listThreads(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: ThreadItem[]; summary: ThreadListSummary }>(
    apiBaseUrl,
    "/v0/threads",
    undefined,
    { user_id: userId },
  );
}

export function getThreadDetail(apiBaseUrl: string, threadId: string, userId: string) {
  return requestJson<{ thread: ThreadItem }>(
    apiBaseUrl,
    `/v0/threads/${threadId}`,
    undefined,
    { user_id: userId },
  );
}

export function getThreadSessions(apiBaseUrl: string, threadId: string, userId: string) {
  return requestJson<{ items: ThreadSessionItem[]; summary: ThreadSessionListSummary }>(
    apiBaseUrl,
    `/v0/threads/${threadId}/sessions`,
    undefined,
    { user_id: userId },
  );
}

export function getThreadEvents(apiBaseUrl: string, threadId: string, userId: string) {
  return requestJson<{ items: ThreadEventItem[]; summary: ThreadEventListSummary }>(
    apiBaseUrl,
    `/v0/threads/${threadId}/events`,
    undefined,
    { user_id: userId },
  );
}

export function listApprovals(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: ApprovalItem[]; summary: { total_count: number; order: string[] } }>(
    apiBaseUrl,
    "/v0/approvals",
    undefined,
    { user_id: userId },
  );
}

export function getApprovalDetail(apiBaseUrl: string, approvalId: string, userId: string) {
  return requestJson<{ approval: ApprovalItem }>(
    apiBaseUrl,
    `/v0/approvals/${approvalId}`,
    undefined,
    { user_id: userId },
  );
}

export function resolveApproval(
  apiBaseUrl: string,
  approvalId: string,
  action: "approve" | "reject",
  userId: string,
) {
  return requestJson<ApprovalResolutionResponse>(apiBaseUrl, `/v0/approvals/${approvalId}/${action}`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export function listTasks(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: TaskItem[]; summary: { total_count: number; order: string[] } }>(
    apiBaseUrl,
    "/v0/tasks",
    undefined,
    { user_id: userId },
  );
}

export function getTaskDetail(apiBaseUrl: string, taskId: string, userId: string) {
  return requestJson<{ task: TaskItem }>(
    apiBaseUrl,
    `/v0/tasks/${taskId}`,
    undefined,
    { user_id: userId },
  );
}

export function getTaskSteps(apiBaseUrl: string, taskId: string, userId: string) {
  return requestJson<{ items: TaskStepItem[]; summary: TaskStepListSummary }>(
    apiBaseUrl,
    `/v0/tasks/${taskId}/steps`,
    undefined,
    { user_id: userId },
  );
}

export function executeApproval(apiBaseUrl: string, approvalId: string, userId: string) {
  return requestJson<ApprovalExecutionResponse>(apiBaseUrl, `/v0/approvals/${approvalId}/execute`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export function listToolExecutions(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: ToolExecutionItem[]; summary: { total_count: number; order: string[] } }>(
    apiBaseUrl,
    "/v0/tool-executions",
    undefined,
    { user_id: userId },
  );
}

export function getToolExecution(apiBaseUrl: string, executionId: string, userId: string) {
  return requestJson<{ execution: ToolExecutionItem }>(
    apiBaseUrl,
    `/v0/tool-executions/${executionId}`,
    undefined,
    { user_id: userId },
  );
}

export function listTraces(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: TraceReviewSummaryItem[]; summary: TraceReviewListSummary }>(
    apiBaseUrl,
    "/v0/traces",
    undefined,
    { user_id: userId },
  );
}

export function getTraceDetail(apiBaseUrl: string, traceId: string, userId: string) {
  return requestJson<{ trace: TraceReviewItem }>(
    apiBaseUrl,
    `/v0/traces/${traceId}`,
    undefined,
    { user_id: userId },
  );
}

export function getTraceEvents(apiBaseUrl: string, traceId: string, userId: string) {
  return requestJson<{ items: TraceReviewEventItem[]; summary: TraceReviewEventListSummary }>(
    apiBaseUrl,
    `/v0/traces/${traceId}/events`,
    undefined,
    { user_id: userId },
  );
}

export function listMemories(
  apiBaseUrl: string,
  userId: string,
  options?: {
    status?: MemoryReviewStatusFilter;
    limit?: number;
  },
) {
  return requestJson<{ items: MemoryReviewRecord[]; summary: MemoryReviewListSummary }>(
    apiBaseUrl,
    "/v0/memories",
    undefined,
    {
      user_id: userId,
      status: options?.status,
      limit: options?.limit ? String(options.limit) : undefined,
    },
  );
}

export function listMemoryReviewQueue(apiBaseUrl: string, userId: string, limit?: number) {
  return requestJson<{ items: MemoryReviewQueueItem[]; summary: MemoryReviewQueueSummary }>(
    apiBaseUrl,
    "/v0/memories/review-queue",
    undefined,
    {
      user_id: userId,
      limit: limit ? String(limit) : undefined,
    },
  );
}

export function getMemoryEvaluationSummary(apiBaseUrl: string, userId: string) {
  return requestJson<{ summary: MemoryEvaluationSummary }>(
    apiBaseUrl,
    "/v0/memories/evaluation-summary",
    undefined,
    { user_id: userId },
  );
}

export function getMemoryDetail(apiBaseUrl: string, memoryId: string, userId: string) {
  return requestJson<{ memory: MemoryReviewRecord }>(
    apiBaseUrl,
    `/v0/memories/${memoryId}`,
    undefined,
    { user_id: userId },
  );
}

export function getMemoryRevisions(
  apiBaseUrl: string,
  memoryId: string,
  userId: string,
  limit?: number,
) {
  return requestJson<{ items: MemoryRevisionReviewRecord[]; summary: MemoryRevisionReviewListSummary }>(
    apiBaseUrl,
    `/v0/memories/${memoryId}/revisions`,
    undefined,
    {
      user_id: userId,
      limit: limit ? String(limit) : undefined,
    },
  );
}

export function listMemoryLabels(apiBaseUrl: string, memoryId: string, userId: string) {
  return requestJson<{ items: MemoryReviewLabelRecord[]; summary: MemoryReviewLabelSummary }>(
    apiBaseUrl,
    `/v0/memories/${memoryId}/labels`,
    undefined,
    { user_id: userId },
  );
}

export function submitMemoryLabel(
  apiBaseUrl: string,
  memoryId: string,
  payload: MemoryReviewLabelPayload,
) {
  return requestJson<{ label: MemoryReviewLabelRecord; summary: MemoryReviewLabelSummary }>(
    apiBaseUrl,
    `/v0/memories/${memoryId}/labels`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
