import type {
  ApprovalItem,
  ApprovalRequestPayload,
  RequestHistoryEntry,
  ResponseHistoryEntry,
  TaskItem,
  TaskStepItem,
  TaskStepListSummary,
  ToolExecutionItem,
  ToolRecord,
} from "./api";
import type { TraceItem } from "../components/trace-list";

const PURCHASE_TOOL: ToolRecord = {
  id: "22222222-2222-4222-8222-222222222222",
  tool_key: "merchant_proxy",
  name: "Merchant Proxy",
  description: "Proxy for governed ecommerce actions.",
  version: "0.1.0",
  metadata_version: "tool_metadata_v0",
  active: true,
  tags: ["commerce", "approval"],
  action_hints: ["place_order"],
  scope_hints: ["supplements"],
  domain_hints: ["ecommerce"],
  risk_hints: ["purchase"],
  metadata: {},
  created_at: "2026-03-15T08:00:00Z",
};

const THREAD_MAGNESIUM = "11111111-1111-4111-8111-111111111111";
const THREAD_VITAMIN_D = "11111111-1111-4111-8111-111111111112";

export const traceFixtures: TraceItem[] = [
  {
    id: "trace-ctx-401",
    kind: "context.compile",
    status: "completed",
    title: "Context compile review",
    summary:
      "Compiled prior task state, admitted memories, and recent thread continuity before assistant response assembly.",
    eventCount: 3,
    createdAt: "2026-03-17T08:45:00Z",
    source: "continuity_v0",
    scope: "Thread magnesium review",
    related: {
      threadId: "thread-magnesium",
      compilerVersion: "continuity_v0",
    },
    metadata: [
      "Trace: trace-ctx-401",
      "Thread: thread-magnesium",
      "Compiler: continuity_v0",
      "Status: completed",
      "Limit max_sessions: 3",
      "Limit max_events: 8",
    ],
    evidence: [
      "Memory evidence admitted for supplement preference and merchant history.",
      "Recent approval state included as part of the continuity pack.",
      "Task-step lineage referenced before response generation.",
    ],
    events: [
      {
        id: "event-1",
        kind: "compiler.scope",
        title: "Scope resolved",
        detail: "Single-user thread scope and compile limits were established for the request.",
        facts: ["Sequence 1", "Captured at Mar 17, 08:45"],
      },
      {
        id: "event-2",
        kind: "memory.retrieve",
        title: "Memory evidence attached",
        detail: "Preference and purchase-history memories were ranked into the response context pack.",
        facts: ["Sequence 2", "Captured at Mar 17, 08:45"],
      },
      {
        id: "event-3",
        kind: "task.retrieve",
        title: "Task lifecycle linked",
        detail: "Open task and step state were included so the answer could acknowledge the approval dependency.",
        facts: ["Sequence 3", "Captured at Mar 17, 08:45"],
      },
    ],
    detailSource: "fixture",
    eventSource: "fixture",
  },
  {
    id: "trace-response-101",
    kind: "response.generate",
    status: "completed",
    title: "Assistant response review",
    summary:
      "The assistant response used the compiled thread context and returned a bounded reply with persisted trace metadata.",
    eventCount: 2,
    createdAt: "2026-03-17T08:45:04Z",
    source: "response_generation_v0",
    scope: "Thread magnesium response",
    related: {
      threadId: "thread-magnesium",
      compilerVersion: "response_generation_v0",
    },
    metadata: [
      "Trace: trace-response-101",
      "Thread: thread-magnesium",
      "Linked compile trace: trace-ctx-401",
      "Compiler: response_generation_v0",
      "Status: completed",
    ],
    evidence: [
      "Prompt assembly stayed inside the shipped no-tools response path.",
      "Assistant output was persisted as an immutable continuity event.",
    ],
    events: [
      {
        id: "event-10",
        kind: "response.prompt.assembled",
        title: "Prompt assembled",
        detail: "System, developer, context, and conversation sections were combined into one response prompt.",
        facts: ["Sequence 1", "Linked compile trace: trace-ctx-401"],
      },
      {
        id: "event-11",
        kind: "response.model.completed",
        title: "Model completed",
        detail: "The assistant returned a natural-language summary without invoking tools or hidden routing.",
        facts: ["Sequence 2", "Provider: openai_responses"],
      },
    ],
    detailSource: "fixture",
    eventSource: "fixture",
  },
  {
    id: "trace-approval-101",
    kind: "approval.request",
    status: "requires_review",
    title: "Approval request review",
    summary:
      "Routing required user approval before the merchant proxy could execute the purchase request.",
    eventCount: 3,
    createdAt: "2026-03-17T06:50:00Z",
    source: "approval_request_v0",
    scope: "Supplement purchase review",
    related: {
      threadId: "thread-magnesium",
      taskId: "task-201",
      approvalId: "approval-101",
      compilerVersion: "approval_request_v0",
    },
    metadata: [
      "Trace: trace-approval-101",
      "Thread: thread-magnesium",
      "Task: task-201",
      "Approval: approval-101",
      "Compiler: approval_request_v0",
      "Status: requires_review",
    ],
    evidence: [
      "Policy rule marked purchase actions as approval-gated.",
      "Tool metadata matched the requested action and scope.",
      "Task-step trace link points back to the original governed request.",
    ],
    events: [
      {
        id: "event-4",
        kind: "tool.route",
        title: "Routing completed",
        detail: "The merchant proxy was selected as the governing tool for the request.",
        facts: ["Sequence 1", "Captured at Mar 17, 06:50"],
      },
      {
        id: "event-5",
        kind: "approval.state",
        title: "Approval opened",
        detail: "Approval record persisted with pending resolution state and task-step linkage.",
        facts: ["Sequence 2", "Captured at Mar 17, 06:50"],
      },
      {
        id: "event-6",
        kind: "task.lifecycle",
        title: "Task updated",
        detail: "Task lifecycle moved into a pending approval state while retaining request provenance.",
        facts: ["Sequence 3", "Captured at Mar 17, 06:50"],
      },
    ],
    detailSource: "fixture",
    eventSource: "fixture",
  },
  {
    id: "trace-response-100",
    kind: "response.generate",
    status: "completed",
    title: "Assistant response review",
    summary:
      "The assistant summarized the last governed Vitamin D action and kept the linked response trace readable for operator review.",
    eventCount: 2,
    createdAt: "2026-03-16T14:32:00Z",
    source: "response_generation_v0",
    scope: "Thread vitamin D response",
    related: {
      threadId: "thread-vitamin-d",
      compilerVersion: "response_generation_v0",
    },
    metadata: [
      "Trace: trace-response-100",
      "Thread: thread-vitamin-d",
      "Linked compile trace: trace-ctx-401",
      "Compiler: response_generation_v0",
      "Status: completed",
    ],
    evidence: [
      "The response referenced prior approval and execution state already stored on the thread.",
      "Trace review remains separated from governed execution controls.",
    ],
    events: [
      {
        id: "event-12",
        kind: "response.prompt.assembled",
        title: "Prompt assembled",
        detail: "Conversation history and prior execution state were assembled into a bounded response prompt.",
        facts: ["Sequence 1", "Linked compile trace: trace-ctx-401"],
      },
      {
        id: "event-13",
        kind: "response.model.completed",
        title: "Model completed",
        detail: "The assistant returned an answer that pointed the operator back to task and trace review instead of acting.",
        facts: ["Sequence 2", "Provider: openai_responses"],
      },
    ],
    detailSource: "fixture",
    eventSource: "fixture",
  },
  {
    id: "trace-exec-311",
    kind: "tool.proxy.execute",
    status: "completed",
    title: "Proxy execution review",
    summary:
      "Approved supplement purchase request executed through the proxy handler with task and trace linkage preserved.",
    eventCount: 3,
    createdAt: "2026-03-16T14:24:00Z",
    source: "proxy_execution_v0",
    scope: "Supplement execution review",
    related: {
      threadId: "thread-vitamin-d",
      taskId: "task-182",
      approvalId: "approval-100",
      executionId: "execution-311",
      compilerVersion: "proxy_execution_v0",
    },
    metadata: [
      "Trace: trace-exec-311",
      "Thread: thread-vitamin-d",
      "Task: task-182",
      "Approval: approval-100",
      "Execution: execution-311",
      "Compiler: proxy_execution_v0",
      "Status: completed",
    ],
    evidence: [
      "Execution occurred only after approval resolution.",
      "Handler output and trace references stayed attached to the governed action record.",
      "Task and task-step lifecycle traces were appended alongside execution status.",
    ],
    events: [
      {
        id: "event-7",
        kind: "approval.check",
        title: "Approval validated",
        detail: "Execution preflight confirmed the approval was in an executable state.",
        facts: ["Sequence 1", "Captured at Mar 16, 14:24"],
      },
      {
        id: "event-8",
        kind: "budget.check",
        title: "Budget check passed",
        detail: "Execution budget constraints did not block the governed action.",
        facts: ["Sequence 2", "Captured at Mar 16, 14:24"],
      },
      {
        id: "event-9",
        kind: "execution.result",
        title: "Handler completed",
        detail:
          "Proxy output was recorded for the approved supplement reorder with a linked execution trace and task-step status update.",
        facts: ["Sequence 3", "Captured at Mar 16, 14:24"],
      },
    ],
    detailSource: "fixture",
    eventSource: "fixture",
  },
];

export const requestHistoryFixtures: RequestHistoryEntry[] = [
  {
    id: "trace-request-101",
    submittedAt: "2026-03-17T06:50:00Z",
    source: "fixture",
    threadId: THREAD_MAGNESIUM,
    toolId: PURCHASE_TOOL.id,
    toolName: PURCHASE_TOOL.name,
    action: "place_order",
    scope: "supplements",
    domainHint: "ecommerce",
    riskHint: "purchase",
    attributes: {
      merchant: "Thorne",
      item: "Magnesium Bisglycinate",
      quantity: "1",
      package: "90 capsules",
    },
    decision: "approval_required",
    taskId: "33333333-3333-4333-8333-333333333333",
    taskStatus: "pending_approval",
    approvalId: "44444444-4444-4444-8444-444444444444",
    approvalStatus: "pending",
    summary:
      "The request persisted a pending approval and created a task that remains paused at explicit operator review.",
    reasons: [
      "Purchases require explicit user approval before execution.",
      "Merchant proxy matches the requested supplement purchase scope.",
    ],
    trace: {
      routingTraceId: "55555555-5555-4555-8555-555555555555",
      routingTraceEventCount: 3,
      requestTraceId: "66666666-6666-4666-8666-666666666666",
      requestTraceEventCount: 6,
    },
  },
  {
    id: "trace-request-100",
    submittedAt: "2026-03-16T14:10:00Z",
    source: "fixture",
    threadId: THREAD_VITAMIN_D,
    toolId: PURCHASE_TOOL.id,
    toolName: PURCHASE_TOOL.name,
    action: "place_order",
    scope: "supplements",
    domainHint: "ecommerce",
    riskHint: "purchase",
    attributes: {
      merchant: "Fullscript",
      item: "Vitamin D3 + K2",
      quantity: "1",
    },
    decision: "approval_required",
    taskId: "33333333-3333-4333-8333-333333333334",
    taskStatus: "approved",
    approvalId: "44444444-4444-4444-8444-444444444445",
    approvalStatus: "approved",
    summary:
      "The governed request produced an approval-linked task, and the operator already resolved the approval as approved.",
    reasons: [
      "Repeat supplement purchases remain approval-gated even when the merchant and dosage are known.",
    ],
    trace: {
      routingTraceId: "55555555-5555-4555-8555-555555555556",
      routingTraceEventCount: 3,
      requestTraceId: "66666666-6666-4666-8666-666666666667",
      requestTraceEventCount: 6,
    },
  },
];

export const responseHistoryFixtures: ResponseHistoryEntry[] = [
  {
    id: "trace-response-101",
    submittedAt: "2026-03-17T08:45:00Z",
    source: "fixture",
    threadId: THREAD_MAGNESIUM,
    message: "Summarize my current magnesium supplement context before I decide whether to reorder.",
    assistantText:
      "You previously reordered Thorne Magnesium Bisglycinate and the latest governed request is still waiting on approval. The current thread context also reflects a preference for keeping merchant and package size explicit before any purchase action.",
    assistantEventId: "assistant-event-101",
    assistantSequenceNo: 14,
    modelProvider: "openai_responses",
    model: "gpt-5-mini",
    summary:
      "Fixture mode shows the assistant-response layout and linked traces without persisting continuity events to the backend.",
    trace: {
      compileTraceId: "trace-ctx-401",
      compileTraceEventCount: 3,
      responseTraceId: "trace-response-101",
      responseTraceEventCount: 2,
    },
  },
  {
    id: "trace-response-100",
    submittedAt: "2026-03-16T14:32:00Z",
    source: "fixture",
    threadId: THREAD_VITAMIN_D,
    message: "What do I need to know about the last Vitamin D request?",
    assistantText:
      "The prior Vitamin D3 + K2 request already moved through approval and execution. The trace history shows the approval was resolved before the proxy handler completed, so the remaining question is whether you want to open the task or execution review for detail.",
    assistantEventId: "assistant-event-100",
    assistantSequenceNo: 11,
    modelProvider: "openai_responses",
    model: "gpt-5-mini",
    summary:
      "Response history stays bounded with the operator prompt, assistant answer, and both compile and response trace references visible.",
    trace: {
      compileTraceId: "trace-ctx-401",
      compileTraceEventCount: 3,
      responseTraceId: "trace-response-100",
      responseTraceEventCount: 2,
    },
  },
];

export const approvalFixtures: ApprovalItem[] = [
  {
    id: "44444444-4444-4444-8444-444444444444",
    thread_id: THREAD_MAGNESIUM,
    task_step_id: "77777777-7777-4777-8777-777777777777",
    status: "pending",
    request: {
      thread_id: THREAD_MAGNESIUM,
      tool_id: PURCHASE_TOOL.id,
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Thorne",
        item: "Magnesium Bisglycinate",
        quantity: "1",
        budget_note: "Prefer previously approved merchant and package size.",
      },
    },
    tool: PURCHASE_TOOL,
    routing: {
      decision: "require_approval",
      reasons: [
        {
          code: "policy_effect_require_approval",
          source: "policy",
          message: "Purchases require explicit user approval before execution.",
          tool_id: PURCHASE_TOOL.id,
          policy_id: "88888888-8888-4888-8888-888888888888",
          consent_key: null,
        },
        {
          code: "tool_metadata_matched",
          source: "tool",
          message: "Merchant proxy supports the requested purchase scope.",
          tool_id: PURCHASE_TOOL.id,
          policy_id: null,
          consent_key: null,
        },
      ],
      trace: {
        trace_id: "55555555-5555-4555-8555-555555555555",
        trace_event_count: 3,
      },
    },
    created_at: "2026-03-17T06:50:00Z",
    resolution: null,
  },
  {
    id: "44444444-4444-4444-8444-444444444445",
    thread_id: THREAD_VITAMIN_D,
    task_step_id: "77777777-7777-4777-8777-777777777778",
    status: "approved",
    request: {
      thread_id: THREAD_VITAMIN_D,
      tool_id: PURCHASE_TOOL.id,
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Fullscript",
        item: "Vitamin D3 + K2",
        quantity: "1",
        note: "Matched prior merchant and approved dosage plan.",
      },
    },
    tool: PURCHASE_TOOL,
    routing: {
      decision: "require_approval",
      reasons: [
        {
          code: "matched_policy",
          source: "policy",
          message:
            "Repeat supplement purchases remain approval-gated even when the merchant and dosage are known.",
          tool_id: PURCHASE_TOOL.id,
          policy_id: "88888888-8888-4888-8888-888888888888",
          consent_key: null,
        },
      ],
      trace: {
        trace_id: "55555555-5555-4555-8555-555555555556",
        trace_event_count: 3,
      },
    },
    created_at: "2026-03-16T14:10:00Z",
    resolution: {
      resolved_at: "2026-03-16T14:22:00Z",
      resolved_by_user_id: "99999999-9999-4999-8999-999999999999",
    },
  },
];

export const taskFixtures: TaskItem[] = [
  {
    id: "33333333-3333-4333-8333-333333333333",
    thread_id: THREAD_MAGNESIUM,
    tool_id: PURCHASE_TOOL.id,
    status: "pending_approval",
    request: {
      thread_id: THREAD_MAGNESIUM,
      tool_id: PURCHASE_TOOL.id,
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Thorne",
        item: "Magnesium Bisglycinate",
      },
    },
    tool: PURCHASE_TOOL,
    latest_approval_id: "44444444-4444-4444-8444-444444444444",
    latest_execution_id: null,
    created_at: "2026-03-17T06:49:00Z",
    updated_at: "2026-03-17T06:50:00Z",
  },
  {
    id: "33333333-3333-4333-8333-333333333334",
    thread_id: THREAD_VITAMIN_D,
    tool_id: PURCHASE_TOOL.id,
    status: "executed",
    request: {
      thread_id: THREAD_VITAMIN_D,
      tool_id: PURCHASE_TOOL.id,
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Fullscript",
        item: "Vitamin D3 + K2",
      },
    },
    tool: PURCHASE_TOOL,
    latest_approval_id: "44444444-4444-4444-8444-444444444445",
    latest_execution_id: "99999999-1111-4111-8111-111111111111",
    created_at: "2026-03-16T14:00:00Z",
    updated_at: "2026-03-16T14:24:00Z",
  },
];

export const executionFixtures: ToolExecutionItem[] = [
  {
    id: "99999999-1111-4111-8111-111111111111",
    approval_id: "44444444-4444-4444-8444-444444444445",
    task_step_id: "77777777-7777-4777-8777-777777777778",
    thread_id: THREAD_VITAMIN_D,
    tool_id: PURCHASE_TOOL.id,
    trace_id: "trace-exec-311",
    request_event_id: "event-request-311",
    result_event_id: "event-result-311",
    status: "completed",
    handler_key: "proxy.echo",
    request: {
      thread_id: THREAD_VITAMIN_D,
      tool_id: PURCHASE_TOOL.id,
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Fullscript",
        item: "Vitamin D3 + K2",
        quantity: "1",
      },
    },
    tool: PURCHASE_TOOL,
    result: {
      handler_key: "proxy.echo",
      status: "completed",
      output: {
        mode: "no_side_effect",
        tool_key: "proxy.echo",
        action: "place_order",
        scope: "supplements",
        merchant: "Fullscript",
        item: "Vitamin D3 + K2",
      },
      reason: null,
    },
    executed_at: "2026-03-16T14:24:00Z",
  },
];

export const taskStepFixtures: Record<string, TaskStepItem[]> = {
  "33333333-3333-4333-8333-333333333333": [
    {
      id: "77777777-7777-4777-8777-777777777777",
      task_id: "33333333-3333-4333-8333-333333333333",
      sequence_no: 1,
      kind: "governed_request",
      status: "created",
      request: {
        thread_id: THREAD_MAGNESIUM,
        tool_id: PURCHASE_TOOL.id,
        action: "place_order",
        scope: "supplements",
        domain_hint: "ecommerce",
        risk_hint: "purchase",
        attributes: {
          merchant: "Thorne",
          item: "Magnesium Bisglycinate",
          package: "90 capsules",
        },
      },
      outcome: {
        routing_decision: "require_approval",
        approval_id: "44444444-4444-4444-8444-444444444444",
        approval_status: "pending",
        execution_id: null,
        execution_status: null,
        blocked_reason: null,
      },
      lineage: {
        parent_step_id: null,
        source_approval_id: null,
        source_execution_id: null,
      },
      trace: {
        trace_id: "66666666-6666-4666-8666-666666666666",
        trace_kind: "approval_request",
      },
      created_at: "2026-03-17T06:49:00Z",
      updated_at: "2026-03-17T06:50:00Z",
    },
  ],
  "33333333-3333-4333-8333-333333333334": [
    {
      id: "77777777-7777-4777-8777-777777777778",
      task_id: "33333333-3333-4333-8333-333333333334",
      sequence_no: 1,
      kind: "governed_request",
      status: "executed",
      request: {
        thread_id: THREAD_VITAMIN_D,
        tool_id: PURCHASE_TOOL.id,
        action: "place_order",
        scope: "supplements",
        domain_hint: "ecommerce",
        risk_hint: "purchase",
        attributes: {
          merchant: "Fullscript",
          item: "Vitamin D3 + K2",
          quantity: "1",
        },
      },
      outcome: {
        routing_decision: "require_approval",
        approval_id: "44444444-4444-4444-8444-444444444445",
        approval_status: "approved",
        execution_id: "99999999-1111-4111-8111-111111111111",
        execution_status: "completed",
        blocked_reason: null,
      },
      lineage: {
        parent_step_id: null,
        source_approval_id: null,
        source_execution_id: "99999999-1111-4111-8111-111111111111",
      },
      trace: {
        trace_id: "trace-exec-311",
        trace_kind: "tool.proxy.execute",
      },
      created_at: "2026-03-16T14:00:00Z",
      updated_at: "2026-03-16T14:24:00Z",
    },
  ],
};

export function getFixtureApproval(approvalId: string) {
  return approvalFixtures.find((item) => item.id === approvalId) ?? null;
}

export function getFixtureTrace(traceId: string) {
  return traceFixtures.find((item) => item.id === traceId) ?? null;
}

export function getFixtureTask(taskId: string) {
  return taskFixtures.find((item) => item.id === taskId) ?? null;
}

export function getFixtureExecution(executionId: string) {
  return executionFixtures.find((item) => item.id === executionId) ?? null;
}

export function getFixtureExecutionByApprovalId(approvalId: string) {
  return executionFixtures.find((item) => item.approval_id === approvalId) ?? null;
}

export function getFixtureTaskSteps(taskId: string) {
  return taskStepFixtures[taskId] ?? [];
}

export function getFixtureTaskStepSummary(taskId: string): TaskStepListSummary {
  const items = getFixtureTaskSteps(taskId);
  const latest = items[items.length - 1];

  return {
    task_id: taskId,
    total_count: items.length,
    latest_sequence_no: latest?.sequence_no ?? null,
    latest_status: latest?.status ?? null,
    next_sequence_no: (latest?.sequence_no ?? 0) + 1,
    append_allowed: false,
    order: items.map((item) => item.id),
  };
}

export function buildFixtureRequestEntry(payload: ApprovalRequestPayload): RequestHistoryEntry {
  const nonce = Date.now().toString(36);

  return {
    id: `fixture-request-${nonce}`,
    submittedAt: new Date().toISOString(),
    source: "fixture",
    threadId: payload.thread_id,
    toolId: payload.tool_id,
    toolName: "Configured tool",
    action: payload.action,
    scope: payload.scope,
    domainHint: payload.domain_hint,
    riskHint: payload.risk_hint,
    attributes: payload.attributes,
    decision: "approval_required",
    taskId: `fixture-task-${nonce}`,
    taskStatus: "pending_approval",
    approvalId: `fixture-approval-${nonce}`,
    approvalStatus: "pending",
    summary:
      "Fixture mode prepared a governed request preview only. Add live API configuration to persist an approval and downstream task.",
    reasons: [
      "Fixture mode keeps the approval-request seam explicit without inventing backend state.",
    ],
    trace: {
      routingTraceId: `fixture-route-${nonce}`,
      routingTraceEventCount: 3,
      requestTraceId: `fixture-trace-${nonce}`,
      requestTraceEventCount: 6,
    },
  };
}

export function buildFixtureResponseEntry(
  payload: Pick<ResponseHistoryEntry, "threadId" | "message">,
): ResponseHistoryEntry {
  const nonce = Date.now().toString(36);

  return {
    id: `fixture-response-${nonce}`,
    submittedAt: new Date().toISOString(),
    source: "fixture",
    threadId: payload.threadId,
    message: payload.message,
    assistantText:
      "Fixture mode generated a preview response only. Add live API configuration to persist the operator message, assistant reply, and linked continuity traces.",
    assistantEventId: `fixture-assistant-${nonce}`,
    assistantSequenceNo: 0,
    modelProvider: "openai_responses",
    model: "fixture-preview",
    summary:
      "The preview keeps the assistant-response seam explicit without inventing stored backend history.",
    trace: {
      compileTraceId: `fixture-compile-${nonce}`,
      compileTraceEventCount: 3,
      responseTraceId: `fixture-response-trace-${nonce}`,
      responseTraceEventCount: 2,
    },
  };
}
