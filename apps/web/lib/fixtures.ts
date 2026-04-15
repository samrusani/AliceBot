import type {
  AgentProfileItem,
  AgentProfileListSummary,
  ApprovalItem,
  ApprovalRequestPayload,
  CalendarAccountListSummary,
  CalendarAccountRecord,
  CalendarEventListSummary,
  CalendarEventSummaryRecord,
  EntityEdgeListSummary,
  EntityEdgeRecord,
  EntityListSummary,
  EntityRecord,
  GmailAccountListSummary,
  GmailAccountRecord,
  MemoryEvaluationSummary,
  MemoryReviewLabelRecord,
  MemoryReviewLabelSummary,
  MemoryReviewListSummary,
  MemoryReviewQueueItem,
  MemoryReviewQueueSummary,
  MemoryReviewRecord,
  MemoryRevisionReviewRecord,
  MemoryRevisionReviewListSummary,
  TaskArtifactChunkListSummary,
  TaskArtifactChunkRecord,
  TaskArtifactListSummary,
  TaskArtifactRecord,
  TaskWorkspaceListSummary,
  TaskWorkspaceRecord,
  RequestHistoryEntry,
  ResponseHistoryEntry,
  ThreadEventItem,
  ThreadItem,
  ThreadSessionItem,
  TaskItem,
  TaskStepItem,
  TaskStepListSummary,
  ToolExecutionItem,
  ToolRecord,
} from "./api";
import { DEFAULT_AGENT_PROFILE_ID } from "./api";
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
const THREAD_CLEANUP = "11111111-1111-4111-8111-111111111113";

export const threadFixtures: ThreadItem[] = [
  {
    id: THREAD_MAGNESIUM,
    title: "Magnesium continuity review",
    agent_profile_id: "assistant_default",
    created_at: "2026-03-17T06:40:00Z",
    updated_at: "2026-03-17T08:45:00Z",
  },
  {
    id: THREAD_VITAMIN_D,
    title: "Vitamin D reorder follow-up",
    agent_profile_id: "coach_default",
    created_at: "2026-03-16T13:58:00Z",
    updated_at: "2026-03-16T14:32:00Z",
  },
  {
    id: THREAD_CLEANUP,
    title: "Quarterly routine cleanup",
    agent_profile_id: "assistant_default",
    created_at: "2026-03-15T09:20:00Z",
    updated_at: "2026-03-15T09:20:00Z",
  },
];

export const agentProfileFixtures: AgentProfileItem[] = [
  {
    id: "assistant_default",
    name: "Assistant Default",
    description: "General-purpose assistant profile for baseline conversations.",
  },
  {
    id: "coach_default",
    name: "Coach Default",
    description: "Coaching-oriented profile focused on guidance and accountability.",
  },
];

export const agentProfileFixtureSummary: AgentProfileListSummary = {
  total_count: agentProfileFixtures.length,
  order: ["id_asc"],
};

export const threadSessionFixtures: Record<string, ThreadSessionItem[]> = {
  [THREAD_MAGNESIUM]: [
    {
      id: "session-magnesium-1",
      thread_id: THREAD_MAGNESIUM,
      status: "completed",
      started_at: "2026-03-17T06:40:00Z",
      ended_at: "2026-03-17T06:52:00Z",
      created_at: "2026-03-17T06:40:00Z",
    },
    {
      id: "session-magnesium-2",
      thread_id: THREAD_MAGNESIUM,
      status: "active",
      started_at: "2026-03-17T08:40:00Z",
      ended_at: null,
      created_at: "2026-03-17T08:40:00Z",
    },
  ],
  [THREAD_VITAMIN_D]: [
    {
      id: "session-vitamin-d-1",
      thread_id: THREAD_VITAMIN_D,
      status: "completed",
      started_at: "2026-03-16T14:00:00Z",
      ended_at: "2026-03-16T14:32:00Z",
      created_at: "2026-03-16T14:00:00Z",
    },
  ],
  [THREAD_CLEANUP]: [],
};

export const threadEventFixtures: Record<string, ThreadEventItem[]> = {
  [THREAD_MAGNESIUM]: [
    {
      id: "event-magnesium-1",
      thread_id: THREAD_MAGNESIUM,
      session_id: "session-magnesium-1",
      sequence_no: 1,
      kind: "message.user",
      payload: {
        text: "Review my magnesium reorder context before I place another order.",
      },
      created_at: "2026-03-17T06:41:00Z",
    },
    {
      id: "event-magnesium-2",
      thread_id: THREAD_MAGNESIUM,
      session_id: "session-magnesium-1",
      sequence_no: 2,
      kind: "approval.request",
      payload: {
        action: "place_order",
        scope: "supplements",
        status: "pending",
      },
      created_at: "2026-03-17T06:50:00Z",
    },
    {
      id: "event-magnesium-3",
      thread_id: THREAD_MAGNESIUM,
      session_id: "session-magnesium-2",
      sequence_no: 3,
      kind: "message.user",
      payload: {
        text: "Summarize what is still waiting for approval.",
      },
      created_at: "2026-03-17T08:43:00Z",
    },
    {
      id: "event-magnesium-4",
      thread_id: THREAD_MAGNESIUM,
      session_id: "session-magnesium-2",
      sequence_no: 4,
      kind: "message.assistant",
      payload: {
        text: "The latest magnesium purchase request is still waiting on approval and keeps the merchant and package details explicit.",
      },
      created_at: "2026-03-17T08:45:00Z",
    },
  ],
  [THREAD_VITAMIN_D]: [
    {
      id: "event-vitamin-d-1",
      thread_id: THREAD_VITAMIN_D,
      session_id: "session-vitamin-d-1",
      sequence_no: 1,
      kind: "message.user",
      payload: {
        text: "What happened with my last Vitamin D reorder?",
      },
      created_at: "2026-03-16T14:05:00Z",
    },
    {
      id: "event-vitamin-d-2",
      thread_id: THREAD_VITAMIN_D,
      session_id: "session-vitamin-d-1",
      sequence_no: 2,
      kind: "approval.resolution",
      payload: {
        status: "approved",
        summary: "The operator approved the reorder before execution.",
      },
      created_at: "2026-03-16T14:22:00Z",
    },
    {
      id: "event-vitamin-d-3",
      thread_id: THREAD_VITAMIN_D,
      session_id: "session-vitamin-d-1",
      sequence_no: 3,
      kind: "tool.execution",
      payload: {
        status: "completed",
        summary: "Merchant proxy completed the approved supplement reorder.",
      },
      created_at: "2026-03-16T14:24:00Z",
    },
    {
      id: "event-vitamin-d-4",
      thread_id: THREAD_VITAMIN_D,
      session_id: "session-vitamin-d-1",
      sequence_no: 4,
      kind: "message.assistant",
      payload: {
        text: "The prior Vitamin D request was approved and executed. Open the task or trace review if you need the full record.",
      },
      created_at: "2026-03-16T14:32:00Z",
    },
  ],
  [THREAD_CLEANUP]: [],
};

const MEMORY_MERCHANT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1";
const MEMORY_MAGNESIUM = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2";
const MEMORY_DELIVERY = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3";

const MEMORY_LABEL_VALUE_ORDER: MemoryReviewLabelSummary["order"] = [
  "correct",
  "incorrect",
  "outdated",
  "insufficient_evidence",
];

export const memoryFixtures: MemoryReviewRecord[] = [
  {
    id: MEMORY_MERCHANT,
    memory_key: "user.preference.merchant.supplements",
    value: {
      merchant: "Thorne",
      confidence: "high",
      reason: "Previously approved orders favored this merchant for magnesium.",
    },
    status: "active",
    source_event_ids: ["event-magnesium-2", "event-magnesium-3"],
    created_at: "2026-03-16T10:20:00Z",
    updated_at: "2026-03-17T08:10:00Z",
    deleted_at: null,
  },
  {
    id: MEMORY_MAGNESIUM,
    memory_key: "user.preference.supplement.magnesium_bisglycinate",
    value: {
      item: "Magnesium Bisglycinate",
      quantity: "1",
      package: "90 capsules",
    },
    status: "active",
    source_event_ids: ["event-magnesium-1", "event-magnesium-2"],
    created_at: "2026-03-16T10:25:00Z",
    updated_at: "2026-03-17T08:12:00Z",
    deleted_at: null,
  },
  {
    id: MEMORY_DELIVERY,
    memory_key: "user.preference.delivery.window",
    value: {
      window: "weekday_morning",
      note: "Avoid weekend deliveries for supplements.",
    },
    status: "active",
    source_event_ids: ["event-vitamin-d-1"],
    created_at: "2026-03-14T09:10:00Z",
    updated_at: "2026-03-16T09:10:00Z",
    deleted_at: null,
  },
];

export const memoryReviewQueueFixtures: MemoryReviewQueueItem[] = [
  {
    id: MEMORY_MAGNESIUM,
    memory_key: "user.preference.supplement.magnesium_bisglycinate",
    value: {
      item: "Magnesium Bisglycinate",
      quantity: "1",
      package: "90 capsules",
    },
    status: "active",
    source_event_ids: ["event-magnesium-1", "event-magnesium-2"],
    is_high_risk: true,
    is_stale_truth: false,
    queue_priority_mode: "recent_first",
    priority_reason: "recent_first",
    created_at: "2026-03-16T10:25:00Z",
    updated_at: "2026-03-17T08:12:00Z",
  },
  {
    id: MEMORY_DELIVERY,
    memory_key: "user.preference.delivery.window",
    value: {
      window: "weekday_morning",
      note: "Avoid weekend deliveries for supplements.",
    },
    status: "active",
    source_event_ids: ["event-vitamin-d-1"],
    is_high_risk: true,
    is_stale_truth: false,
    queue_priority_mode: "recent_first",
    priority_reason: "recent_first",
    created_at: "2026-03-14T09:10:00Z",
    updated_at: "2026-03-16T09:10:00Z",
  },
];

export const memoryReviewListSummaryFixture: MemoryReviewListSummary = {
  status: "active",
  limit: 20,
  returned_count: memoryFixtures.length,
  total_count: memoryFixtures.length,
  has_more: false,
  order: ["updated_at_desc", "created_at_desc", "id_desc"],
};

export const memoryReviewQueueSummaryFixture: MemoryReviewQueueSummary = {
  memory_status: "active",
  review_state: "unlabeled",
  priority_mode: "recent_first",
  available_priority_modes: [
    "oldest_first",
    "recent_first",
    "high_risk_first",
    "stale_truth_first",
  ],
  limit: 20,
  returned_count: memoryReviewQueueFixtures.length,
  total_count: memoryReviewQueueFixtures.length,
  has_more: false,
  order: ["updated_at_desc", "created_at_desc", "id_desc"],
};

export const memoryEvaluationSummaryFixture: MemoryEvaluationSummary = {
  total_memory_count: 4,
  active_memory_count: 3,
  deleted_memory_count: 1,
  labeled_memory_count: 1,
  unlabeled_memory_count: 3,
  total_label_row_count: 2,
  label_row_counts_by_value: {
    correct: 1,
    incorrect: 0,
    outdated: 1,
    insufficient_evidence: 0,
  },
  label_value_order: [...MEMORY_LABEL_VALUE_ORDER],
  quality_gate: {
    status: "insufficient_sample",
    precision: 1,
    precision_target: 0.8,
    adjudicated_sample_count: 1,
    minimum_adjudicated_sample: 10,
    remaining_to_minimum_sample: 9,
    unlabeled_memory_count: 3,
    high_risk_memory_count: 3,
    stale_truth_count: 0,
    superseded_active_conflict_count: 0,
    counts: {
      active_memory_count: 3,
      labeled_active_memory_count: 0,
      adjudicated_correct_count: 1,
      adjudicated_incorrect_count: 0,
      outdated_label_count: 1,
      insufficient_evidence_label_count: 0,
    },
  },
};

export const memoryEvaluationSummaryOnTrackFixture: MemoryEvaluationSummary = {
  total_memory_count: 12,
  active_memory_count: 10,
  deleted_memory_count: 2,
  labeled_memory_count: 12,
  unlabeled_memory_count: 0,
  total_label_row_count: 10,
  label_row_counts_by_value: {
    correct: 8,
    incorrect: 2,
    outdated: 1,
    insufficient_evidence: 1,
  },
  label_value_order: [...MEMORY_LABEL_VALUE_ORDER],
  quality_gate: {
    status: "healthy",
    precision: 0.8,
    precision_target: 0.8,
    adjudicated_sample_count: 10,
    minimum_adjudicated_sample: 10,
    remaining_to_minimum_sample: 0,
    unlabeled_memory_count: 0,
    high_risk_memory_count: 0,
    stale_truth_count: 0,
    superseded_active_conflict_count: 0,
    counts: {
      active_memory_count: 10,
      labeled_active_memory_count: 10,
      adjudicated_correct_count: 8,
      adjudicated_incorrect_count: 2,
      outdated_label_count: 1,
      insufficient_evidence_label_count: 1,
    },
  },
};

export const memoryEvaluationSummaryNeedsReviewFixture: MemoryEvaluationSummary = {
  total_memory_count: 12,
  active_memory_count: 10,
  deleted_memory_count: 2,
  labeled_memory_count: 12,
  unlabeled_memory_count: 3,
  total_label_row_count: 10,
  label_row_counts_by_value: {
    correct: 6,
    incorrect: 4,
    outdated: 0,
    insufficient_evidence: 0,
  },
  label_value_order: [...MEMORY_LABEL_VALUE_ORDER],
  quality_gate: {
    status: "degraded",
    precision: 0.6,
    precision_target: 0.8,
    adjudicated_sample_count: 10,
    minimum_adjudicated_sample: 10,
    remaining_to_minimum_sample: 0,
    unlabeled_memory_count: 3,
    high_risk_memory_count: 3,
    stale_truth_count: 0,
    superseded_active_conflict_count: 0,
    counts: {
      active_memory_count: 10,
      labeled_active_memory_count: 7,
      adjudicated_correct_count: 6,
      adjudicated_incorrect_count: 4,
      outdated_label_count: 0,
      insufficient_evidence_label_count: 0,
    },
  },
};

export const memoryRevisionFixtures: Record<string, MemoryRevisionReviewRecord[]> = {
  [MEMORY_MERCHANT]: [
    {
      id: "memory-revision-1",
      memory_id: MEMORY_MERCHANT,
      sequence_no: 1,
      action: "ADD",
      memory_key: "user.preference.merchant.supplements",
      previous_value: null,
      new_value: {
        merchant: "Thorne",
      },
      source_event_ids: ["event-magnesium-1"],
      created_at: "2026-03-16T10:20:00Z",
    },
    {
      id: "memory-revision-2",
      memory_id: MEMORY_MERCHANT,
      sequence_no: 2,
      action: "UPDATE",
      memory_key: "user.preference.merchant.supplements",
      previous_value: {
        merchant: "Thorne",
      },
      new_value: {
        merchant: "Thorne",
        confidence: "high",
        reason: "Previously approved orders favored this merchant for magnesium.",
      },
      source_event_ids: ["event-magnesium-2", "event-magnesium-3"],
      created_at: "2026-03-17T08:10:00Z",
    },
  ],
  [MEMORY_MAGNESIUM]: [
    {
      id: "memory-revision-3",
      memory_id: MEMORY_MAGNESIUM,
      sequence_no: 1,
      action: "ADD",
      memory_key: "user.preference.supplement.magnesium_bisglycinate",
      previous_value: null,
      new_value: {
        item: "Magnesium Bisglycinate",
        quantity: "1",
        package: "90 capsules",
      },
      source_event_ids: ["event-magnesium-1", "event-magnesium-2"],
      created_at: "2026-03-16T10:25:00Z",
    },
  ],
  [MEMORY_DELIVERY]: [
    {
      id: "memory-revision-4",
      memory_id: MEMORY_DELIVERY,
      sequence_no: 1,
      action: "ADD",
      memory_key: "user.preference.delivery.window",
      previous_value: null,
      new_value: {
        window: "weekday_morning",
        note: "Avoid weekend deliveries for supplements.",
      },
      source_event_ids: ["event-vitamin-d-1"],
      created_at: "2026-03-14T09:10:00Z",
    },
  ],
};

export const memoryLabelFixtures: Record<string, MemoryReviewLabelRecord[]> = {
  [MEMORY_MERCHANT]: [
    {
      id: "memory-label-1",
      memory_id: MEMORY_MERCHANT,
      reviewer_user_id: "99999999-9999-4999-8999-999999999999",
      label: "correct",
      note: "Still matches the latest approved reorder context.",
      created_at: "2026-03-17T08:20:00Z",
    },
    {
      id: "memory-label-2",
      memory_id: MEMORY_MERCHANT,
      reviewer_user_id: "99999999-9999-4999-8999-999999999999",
      label: "outdated",
      note: "Verify against any newer merchant change before next order.",
      created_at: "2026-03-17T08:21:00Z",
    },
  ],
};

export const memoryLabelSummaryFixtures: Record<string, MemoryReviewLabelSummary> = {
  [MEMORY_MERCHANT]: {
    memory_id: MEMORY_MERCHANT,
    total_count: 2,
    counts_by_label: {
      correct: 1,
      incorrect: 0,
      outdated: 1,
      insufficient_evidence: 0,
    },
    order: [...MEMORY_LABEL_VALUE_ORDER],
  },
};

const ENTITY_ALICE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1";
const ENTITY_THORNE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2";
const ENTITY_MAGNESIUM = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb3";
const ENTITY_ROUTINE = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb4";

const ENTITY_EDGE_A = "cccccccc-cccc-4ccc-8ccc-ccccccccccc1";
const ENTITY_EDGE_B = "cccccccc-cccc-4ccc-8ccc-ccccccccccc2";
const ENTITY_EDGE_C = "cccccccc-cccc-4ccc-8ccc-ccccccccccc3";

export const entityFixtures: EntityRecord[] = [
  {
    id: ENTITY_ALICE,
    entity_type: "person",
    name: "Alice",
    source_memory_ids: [MEMORY_MERCHANT, MEMORY_MAGNESIUM],
    created_at: "2026-03-16T10:30:00Z",
  },
  {
    id: ENTITY_THORNE,
    entity_type: "merchant",
    name: "Thorne",
    source_memory_ids: [MEMORY_MERCHANT],
    created_at: "2026-03-16T10:31:00Z",
  },
  {
    id: ENTITY_MAGNESIUM,
    entity_type: "product",
    name: "Magnesium Bisglycinate 90 capsules",
    source_memory_ids: [MEMORY_MAGNESIUM],
    created_at: "2026-03-16T10:32:00Z",
  },
  {
    id: ENTITY_ROUTINE,
    entity_type: "routine",
    name: "Morning supplement routine",
    source_memory_ids: [MEMORY_MAGNESIUM, MEMORY_DELIVERY],
    created_at: "2026-03-16T10:33:00Z",
  },
];

export const entityListSummaryFixture: EntityListSummary = {
  total_count: entityFixtures.length,
  order: ["created_at_asc", "id_asc"],
};

const entityEdgeCatalog: EntityEdgeRecord[] = [
  {
    id: ENTITY_EDGE_A,
    from_entity_id: ENTITY_ALICE,
    to_entity_id: ENTITY_THORNE,
    relationship_type: "prefers_merchant",
    valid_from: "2026-03-16T10:20:00Z",
    valid_to: null,
    source_memory_ids: [MEMORY_MERCHANT],
    created_at: "2026-03-16T10:40:00Z",
  },
  {
    id: ENTITY_EDGE_B,
    from_entity_id: ENTITY_ALICE,
    to_entity_id: ENTITY_MAGNESIUM,
    relationship_type: "prefers_product",
    valid_from: "2026-03-16T10:25:00Z",
    valid_to: null,
    source_memory_ids: [MEMORY_MAGNESIUM],
    created_at: "2026-03-16T10:42:00Z",
  },
  {
    id: ENTITY_EDGE_C,
    from_entity_id: ENTITY_ROUTINE,
    to_entity_id: ENTITY_MAGNESIUM,
    relationship_type: "includes_product",
    valid_from: "2026-03-16T10:33:00Z",
    valid_to: null,
    source_memory_ids: [MEMORY_MAGNESIUM, MEMORY_DELIVERY],
    created_at: "2026-03-16T10:44:00Z",
  },
];

export const entityEdgeFixtures: Record<string, EntityEdgeRecord[]> = {
  [ENTITY_ALICE]: entityEdgeCatalog.filter(
    (edge) => edge.from_entity_id === ENTITY_ALICE || edge.to_entity_id === ENTITY_ALICE,
  ),
  [ENTITY_THORNE]: entityEdgeCatalog.filter(
    (edge) => edge.from_entity_id === ENTITY_THORNE || edge.to_entity_id === ENTITY_THORNE,
  ),
  [ENTITY_MAGNESIUM]: entityEdgeCatalog.filter(
    (edge) => edge.from_entity_id === ENTITY_MAGNESIUM || edge.to_entity_id === ENTITY_MAGNESIUM,
  ),
  [ENTITY_ROUTINE]: entityEdgeCatalog.filter(
    (edge) => edge.from_entity_id === ENTITY_ROUTINE || edge.to_entity_id === ENTITY_ROUTINE,
  ),
};

const TASK_WORKSPACE_MAGNESIUM = "dddddddd-dddd-4ddd-8ddd-ddddddddddd1";
const TASK_WORKSPACE_VITAMIN_D = "dddddddd-dddd-4ddd-8ddd-ddddddddddd2";

const TASK_ARTIFACT_MAGNESIUM_NOTE = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee1";
const TASK_ARTIFACT_VITAMIN_EMAIL = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee2";
const TASK_ARTIFACT_PENDING_PDF = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeee3";

export const gmailAccountFixtures: GmailAccountRecord[] = [
  {
    id: "f1f1f1f1-f1f1-4f1f-8f1f-f1f1f1f1f1f1",
    provider: "gmail",
    auth_kind: "oauth_access_token",
    provider_account_id: "acct-owner-001",
    email_address: "owner@gmail.example",
    display_name: "Owner",
    scope: "https://www.googleapis.com/auth/gmail.readonly",
    created_at: "2026-03-16T14:00:00Z",
    updated_at: "2026-03-16T14:00:00Z",
  },
  {
    id: "f2f2f2f2-f2f2-4f2f-8f2f-f2f2f2f2f2f2",
    provider: "gmail",
    auth_kind: "oauth_access_token",
    provider_account_id: "acct-ops-002",
    email_address: "ops@gmail.example",
    display_name: "Ops",
    scope: "https://www.googleapis.com/auth/gmail.readonly",
    created_at: "2026-03-17T08:32:00Z",
    updated_at: "2026-03-17T08:32:00Z",
  },
];

export const gmailAccountListSummaryFixture: GmailAccountListSummary = {
  total_count: gmailAccountFixtures.length,
  order: ["created_at_asc", "id_asc"],
};

export const calendarAccountFixtures: CalendarAccountRecord[] = [
  {
    id: "c1c1c1c1-c1c1-4c1c-8c1c-c1c1c1c1c1c1",
    provider: "google_calendar",
    auth_kind: "oauth_access_token",
    provider_account_id: "acct-owner-001",
    email_address: "owner@gmail.example",
    display_name: "Owner",
    scope: "https://www.googleapis.com/auth/calendar.readonly",
    created_at: "2026-03-16T14:00:00Z",
    updated_at: "2026-03-16T14:00:00Z",
  },
  {
    id: "c2c2c2c2-c2c2-4c2c-8c2c-c2c2c2c2c2c2",
    provider: "google_calendar",
    auth_kind: "oauth_access_token",
    provider_account_id: "acct-ops-002",
    email_address: "ops@gmail.example",
    display_name: "Ops",
    scope: "https://www.googleapis.com/auth/calendar.readonly",
    created_at: "2026-03-17T08:32:00Z",
    updated_at: "2026-03-17T08:32:00Z",
  },
];

export const calendarAccountListSummaryFixture: CalendarAccountListSummary = {
  total_count: calendarAccountFixtures.length,
  order: ["created_at_asc", "id_asc"],
};

export const calendarEventFixtures: Record<string, CalendarEventSummaryRecord[]> = {
  "c1c1c1c1-c1c1-4c1c-8c1c-c1c1c1c1c1c1": [
    {
      provider_event_id: "evt-owner-planning",
      status: "confirmed",
      summary: "Sprint planning review",
      start_time: "2026-03-20T09:00:00+00:00",
      end_time: "2026-03-20T09:30:00+00:00",
      html_link: "https://calendar.google.com/event?eid=evt-owner-planning",
      updated_at: "2026-03-19T08:14:00+00:00",
    },
    {
      provider_event_id: "evt-owner-retro",
      status: "tentative",
      summary: "Retro prep",
      start_time: "2026-03-20T11:00:00+00:00",
      end_time: "2026-03-20T11:45:00+00:00",
      html_link: "https://calendar.google.com/event?eid=evt-owner-retro",
      updated_at: "2026-03-19T08:42:00+00:00",
    },
    {
      provider_event_id: "evt-owner-all-day",
      status: "confirmed",
      summary: "Quarterly planning day",
      start_time: "2026-03-21",
      end_time: "2026-03-22",
      html_link: null,
      updated_at: "2026-03-18T10:00:00+00:00",
    },
  ],
  "c2c2c2c2-c2c2-4c2c-8c2c-c2c2c2c2c2c2": [
    {
      provider_event_id: "evt-ops-review",
      status: "confirmed",
      summary: "Ops account audit",
      start_time: "2026-03-20T14:00:00+00:00",
      end_time: "2026-03-20T14:30:00+00:00",
      html_link: "https://calendar.google.com/event?eid=evt-ops-review",
      updated_at: "2026-03-19T07:55:00+00:00",
    },
    {
      provider_event_id: "evt-ops-hand-off",
      status: "confirmed",
      summary: "Shift hand-off",
      start_time: "2026-03-20T16:00:00+00:00",
      end_time: "2026-03-20T16:20:00+00:00",
      html_link: "https://calendar.google.com/event?eid=evt-ops-hand-off",
      updated_at: "2026-03-19T09:20:00+00:00",
    },
  ],
};

export const taskWorkspaceFixtures: TaskWorkspaceRecord[] = [
  {
    id: TASK_WORKSPACE_MAGNESIUM,
    task_id: "33333333-3333-4333-8333-333333333333",
    status: "active",
    local_path: "/var/alicebot/workspaces/33333333-3333-4333-8333-333333333333",
    created_at: "2026-03-17T06:48:00Z",
    updated_at: "2026-03-17T06:48:00Z",
  },
  {
    id: TASK_WORKSPACE_VITAMIN_D,
    task_id: "33333333-3333-4333-8333-333333333334",
    status: "active",
    local_path: "/var/alicebot/workspaces/33333333-3333-4333-8333-333333333334",
    created_at: "2026-03-16T13:58:00Z",
    updated_at: "2026-03-16T13:58:00Z",
  },
];

export const taskWorkspaceListSummaryFixture: TaskWorkspaceListSummary = {
  total_count: taskWorkspaceFixtures.length,
  order: ["created_at_asc", "id_asc"],
};

export const taskArtifactFixtures: TaskArtifactRecord[] = [
  {
    id: TASK_ARTIFACT_MAGNESIUM_NOTE,
    task_id: "33333333-3333-4333-8333-333333333333",
    task_workspace_id: TASK_WORKSPACE_MAGNESIUM,
    status: "registered",
    ingestion_status: "ingested",
    relative_path: "notes/magnesium-review.md",
    media_type_hint: "text/markdown",
    created_at: "2026-03-17T07:10:00Z",
    updated_at: "2026-03-17T07:12:00Z",
  },
  {
    id: TASK_ARTIFACT_VITAMIN_EMAIL,
    task_id: "33333333-3333-4333-8333-333333333334",
    task_workspace_id: TASK_WORKSPACE_VITAMIN_D,
    status: "registered",
    ingestion_status: "ingested",
    relative_path: "gmail/2026-03-16-order-confirmation.eml",
    media_type_hint: "message/rfc822",
    created_at: "2026-03-16T14:18:00Z",
    updated_at: "2026-03-16T14:19:00Z",
  },
  {
    id: TASK_ARTIFACT_PENDING_PDF,
    task_id: "33333333-3333-4333-8333-333333333333",
    task_workspace_id: TASK_WORKSPACE_MAGNESIUM,
    status: "registered",
    ingestion_status: "pending",
    relative_path: "docs/lab-panel.pdf",
    media_type_hint: "application/pdf",
    created_at: "2026-03-17T08:01:00Z",
    updated_at: "2026-03-17T08:01:00Z",
  },
];

export const taskArtifactListSummaryFixture: TaskArtifactListSummary = {
  total_count: taskArtifactFixtures.length,
  order: ["created_at_asc", "id_asc"],
};

export const taskArtifactChunkFixtures: Record<string, TaskArtifactChunkRecord[]> = {
  [TASK_ARTIFACT_MAGNESIUM_NOTE]: [
    {
      id: "ffffffff-ffff-4fff-8fff-fffffffffff1",
      task_artifact_id: TASK_ARTIFACT_MAGNESIUM_NOTE,
      sequence_no: 1,
      char_start: 0,
      char_end_exclusive: 196,
      text: "## Magnesium review\nLast approved merchant: Thorne.\nPreferred package size: 90 capsules.\nPending approval still blocks any new purchase action.\n",
      created_at: "2026-03-17T07:12:00Z",
      updated_at: "2026-03-17T07:12:00Z",
    },
    {
      id: "ffffffff-ffff-4fff-8fff-fffffffffff2",
      task_artifact_id: TASK_ARTIFACT_MAGNESIUM_NOTE,
      sequence_no: 2,
      char_start: 196,
      char_end_exclusive: 392,
      text: "## Follow-up\nOperator should confirm whether merchant preference still matches current constraints before requesting execution.\n",
      created_at: "2026-03-17T07:12:00Z",
      updated_at: "2026-03-17T07:12:00Z",
    },
  ],
  [TASK_ARTIFACT_VITAMIN_EMAIL]: [
    {
      id: "ffffffff-ffff-4fff-8fff-fffffffffff3",
      task_artifact_id: TASK_ARTIFACT_VITAMIN_EMAIL,
      sequence_no: 1,
      char_start: 0,
      char_end_exclusive: 238,
      text: "From: orders@example.com\nSubject: Vitamin D3 + K2 order confirmation\nBody: Your order was approved and fulfilled on 2026-03-16.\n",
      created_at: "2026-03-16T14:19:00Z",
      updated_at: "2026-03-16T14:19:00Z",
    },
  ],
};

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
    task_run_id: null,
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
    task_run_id: null,
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
    task_run_id: null,
    task_step_id: "77777777-7777-4777-8777-777777777778",
    thread_id: THREAD_VITAMIN_D,
    tool_id: PURCHASE_TOOL.id,
    trace_id: "trace-exec-311",
    request_event_id: "event-request-311",
    result_event_id: "event-result-311",
    status: "completed",
    handler_key: "proxy.echo",
    idempotency_key: null,
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

export function getFixtureThread(threadId: string) {
  return threadFixtures.find((item) => item.id === threadId) ?? null;
}

export function getFixtureMemory(memoryId: string) {
  return memoryFixtures.find((item) => item.id === memoryId) ?? null;
}

export function getFixtureEntity(entityId: string) {
  return entityFixtures.find((item) => item.id === entityId) ?? null;
}

export function getFixtureGmailAccount(gmailAccountId: string) {
  return gmailAccountFixtures.find((item) => item.id === gmailAccountId) ?? null;
}

export function getFixtureCalendarAccount(calendarAccountId: string) {
  return calendarAccountFixtures.find((item) => item.id === calendarAccountId) ?? null;
}

function parseFixtureDate(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed;
}

function normalizeFixtureCalendarEventSortKey(startTime: string | null) {
  if (!startTime) {
    return "~";
  }

  const parsed = parseFixtureDate(startTime);
  return parsed ? parsed.toISOString() : "~";
}

export function getFixtureCalendarEvents(calendarAccountId: string) {
  return calendarEventFixtures[calendarAccountId] ?? [];
}

export function getFixtureCalendarEventList(
  calendarAccountId: string,
  options?: {
    limit?: number;
    timeMin?: string;
    timeMax?: string;
  },
): {
  items: CalendarEventSummaryRecord[];
  summary: CalendarEventListSummary;
} {
  const boundedLimit = Math.max(1, Math.min(50, options?.limit ?? 20));
  const timeMin = options?.timeMin?.trim() ? options.timeMin.trim() : null;
  const timeMax = options?.timeMax?.trim() ? options.timeMax.trim() : null;
  const timeMinDate = parseFixtureDate(timeMin);
  const timeMaxDate = parseFixtureDate(timeMax);

  const filteredItems = getFixtureCalendarEvents(calendarAccountId).filter((item) => {
    const startDate = parseFixtureDate(item.start_time);

    if (timeMinDate && startDate && startDate < timeMinDate) {
      return false;
    }
    if (timeMaxDate && startDate && startDate > timeMaxDate) {
      return false;
    }

    return true;
  });

  const items = [...filteredItems]
    .sort((left, right) => {
      const leftStart = normalizeFixtureCalendarEventSortKey(left.start_time);
      const rightStart = normalizeFixtureCalendarEventSortKey(right.start_time);
      if (leftStart === rightStart) {
        return left.provider_event_id.localeCompare(right.provider_event_id);
      }
      return leftStart.localeCompare(rightStart);
    })
    .slice(0, boundedLimit);

  return {
    items,
    summary: {
      total_count: items.length,
      limit: boundedLimit,
      order: ["start_time_asc", "provider_event_id_asc"],
      time_min: timeMin,
      time_max: timeMax,
    },
  };
}

export function getFixtureTaskWorkspace(taskWorkspaceId: string) {
  return taskWorkspaceFixtures.find((item) => item.id === taskWorkspaceId) ?? null;
}

export function getFixtureTaskArtifact(taskArtifactId: string) {
  return taskArtifactFixtures.find((item) => item.id === taskArtifactId) ?? null;
}

export function getFixtureTaskArtifactChunks(taskArtifactId: string) {
  return taskArtifactChunkFixtures[taskArtifactId] ?? [];
}

export function getFixtureTaskArtifactChunkSummary(taskArtifactId: string): TaskArtifactChunkListSummary {
  const artifact = getFixtureTaskArtifact(taskArtifactId);
  const items = getFixtureTaskArtifactChunks(taskArtifactId);
  const totalCharacters = items.reduce((acc, item) => acc + Math.max(0, item.char_end_exclusive - item.char_start), 0);

  return {
    total_count: items.length,
    total_characters: totalCharacters,
    media_type: artifact?.media_type_hint ?? "text/plain",
    chunking_rule: "artifact_ingestion_v0",
    order: ["sequence_no_asc", "id_asc"],
  };
}

export function getFixtureEntityEdges(entityId: string) {
  return entityEdgeFixtures[entityId] ?? [];
}

export function getFixtureEntityEdgeSummary(entityId: string): EntityEdgeListSummary {
  const items = getFixtureEntityEdges(entityId);
  return {
    entity_id: entityId,
    total_count: items.length,
    order: ["created_at_asc", "id_asc"],
  };
}

export function getFixtureMemoryRevisions(memoryId: string) {
  return memoryRevisionFixtures[memoryId] ?? [];
}

export function getFixtureMemoryRevisionSummary(memoryId: string): MemoryRevisionReviewListSummary {
  const items = getFixtureMemoryRevisions(memoryId);
  return {
    memory_id: memoryId,
    limit: 20,
    returned_count: items.length,
    total_count: items.length,
    has_more: false,
    order: ["sequence_no_asc"],
  };
}

export function getFixtureMemoryLabels(memoryId: string) {
  return memoryLabelFixtures[memoryId] ?? [];
}

export function getFixtureMemoryLabelSummary(memoryId: string): MemoryReviewLabelSummary {
  const existing = memoryLabelSummaryFixtures[memoryId];
  if (existing) {
    return existing;
  }

  return {
    memory_id: memoryId,
    total_count: 0,
    counts_by_label: {
      correct: 0,
      incorrect: 0,
      outdated: 0,
      insufficient_evidence: 0,
    },
    order: [...MEMORY_LABEL_VALUE_ORDER],
  };
}

export function getFixtureThreadSessions(threadId: string) {
  return threadSessionFixtures[threadId] ?? [];
}

export function getFixtureThreadEvents(threadId: string) {
  return threadEventFixtures[threadId] ?? [];
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

export function buildFixtureThread(title: string): ThreadItem {
  const nonce = Date.now().toString(36);
  const timestamp = new Date().toISOString();

  return {
    id: `fixture-thread-${nonce}`,
    title,
    agent_profile_id: DEFAULT_AGENT_PROFILE_ID,
    created_at: timestamp,
    updated_at: timestamp,
  };
}
