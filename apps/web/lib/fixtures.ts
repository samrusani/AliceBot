import type {
  ApprovalItem,
  ApprovalRequestPayload,
  RequestHistoryEntry,
  TaskItem,
  TaskStepItem,
  TaskStepListSummary,
  ToolRecord,
} from "./api";

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
      },
    },
    tool: PURCHASE_TOOL,
    latest_approval_id: "44444444-4444-4444-8444-444444444445",
    latest_execution_id: null,
    created_at: "2026-03-16T14:00:00Z",
    updated_at: "2026-03-16T14:22:00Z",
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
        },
      },
      outcome: {
        routing_decision: "require_approval",
        approval_id: "44444444-4444-4444-8444-444444444445",
        approval_status: "approved",
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
        trace_id: "66666666-6666-4666-8666-666666666667",
        trace_kind: "approval_resolution",
      },
      created_at: "2026-03-16T14:00:00Z",
      updated_at: "2026-03-16T14:22:00Z",
    },
  ],
};

export function getFixtureApproval(approvalId: string) {
  return approvalFixtures.find((item) => item.id === approvalId) ?? null;
}

export function getFixtureTask(taskId: string) {
  return taskFixtures.find((item) => item.id === taskId) ?? null;
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
