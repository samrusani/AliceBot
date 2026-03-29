export type ApiSource = "live" | "fixture";
export type PageDataMode = "live" | "fixture" | "mixed";

export type ApiConfig = {
  apiBaseUrl: string;
  userId: string;
  defaultThreadId: string;
  defaultToolId: string;
};

export const DEFAULT_AGENT_PROFILE_ID = "assistant_default";

export type ThreadItem = {
  id: string;
  title: string;
  agent_profile_id: string;
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
  agent_profile_id: string;
};

export type ThreadListSummary = {
  total_count: number;
  order: string[];
};

export type AgentProfileItem = {
  id: string;
  name: string;
  description: string;
};

export type AgentProfileListSummary = {
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

export type ResumptionBriefSectionSummary = {
  limit: number;
  returned_count: number;
  total_count: number;
  order: string[];
};

export type ResumptionBriefConversationSummary = ResumptionBriefSectionSummary & {
  kinds: string[];
};

export type ResumptionBriefConversationSection = {
  items: ThreadEventItem[];
  summary: ResumptionBriefConversationSummary;
};

export type ResumptionBriefOpenLoopSection = {
  items: OpenLoopRecord[];
  summary: ResumptionBriefSectionSummary;
};

export type ResumptionBriefMemoryHighlightSection = {
  items: MemoryReviewRecord[];
  summary: ResumptionBriefSectionSummary;
};

export type ResumptionBriefWorkflowSummary = {
  present: boolean;
  task_order: string[];
  task_step_order: string[];
};

export type ResumptionBriefWorkflowPosture = {
  task: TaskItem;
  latest_task_step: TaskStepItem | null;
  summary: ResumptionBriefWorkflowSummary;
};

export type ResumptionBrief = {
  assembly_version: string;
  thread: ThreadItem;
  conversation: ResumptionBriefConversationSection;
  open_loops: ResumptionBriefOpenLoopSection;
  memory_highlights: ResumptionBriefMemoryHighlightSection;
  workflow: ResumptionBriefWorkflowPosture | null;
  sources: string[];
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
  task_run_id: string | null;
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

export type TaskRunStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "waiting_user"
  | "paused"
  | "failed"
  | "done"
  | "cancelled";
export type TaskRunStopReason =
  | "waiting_approval"
  | "waiting_user"
  | "budget_exhausted"
  | "paused"
  | "approval_rejected"
  | "policy_blocked"
  | "retry_exhausted"
  | "fatal_error"
  | "done"
  | "cancelled";
export type TaskRunFailureClass = "transient" | "policy" | "approval" | "budget" | "fatal";
export type TaskRunRetryPosture =
  | "none"
  | "retryable"
  | "exhausted"
  | "terminal"
  | "paused"
  | "awaiting_approval"
  | "awaiting_user";

export type TaskRunItem = {
  id: string;
  task_id: string;
  status: TaskRunStatus;
  checkpoint: JsonObject;
  tick_count: number;
  step_count: number;
  max_ticks: number;
  retry_count: number;
  retry_cap: number;
  retry_posture: TaskRunRetryPosture;
  failure_class: TaskRunFailureClass | null;
  stop_reason: TaskRunStopReason | null;
  last_transitioned_at: string;
  created_at: string;
  updated_at: string;
};

export type TaskRunListSummary = {
  task_id: string;
  total_count: number;
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
  task_run_id: string | null;
  task_step_id: string;
  thread_id: string;
  tool_id: string;
  trace_id: string;
  request_event_id: string | null;
  result_event_id: string | null;
  status: string;
  handler_key: string | null;
  idempotency_key: string | null;
  request: GovernedRequestRecord;
  tool: ToolRecord;
  result: ToolExecutionResult;
  executed_at: string;
};

export type ApprovalExecutionResponse = {
  request: {
    approval_id: string;
    task_run_id: string | null;
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
export type OpenLoopStatus = "open" | "resolved" | "dismissed";
export type OpenLoopStatusFilter = OpenLoopStatus | "all";
export type MemoryReviewLabelValue =
  | "correct"
  | "incorrect"
  | "outdated"
  | "insufficient_evidence";

export type MemoryType =
  | "preference"
  | "identity_fact"
  | "relationship_fact"
  | "project_fact"
  | "decision"
  | "commitment"
  | "routine"
  | "constraint"
  | "working_style";

export type MemoryConfirmationStatus = "unconfirmed" | "confirmed" | "contested";

export type MemoryReviewRecord = {
  id: string;
  memory_key: string;
  value: unknown;
  status: MemoryReviewStatus;
  source_event_ids: string[];
  memory_type?: MemoryType;
  confidence?: number | null;
  salience?: number | null;
  confirmation_status?: MemoryConfirmationStatus;
  valid_from?: string | null;
  valid_to?: string | null;
  last_confirmed_at?: string | null;
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
  memory_type?: MemoryType;
  confidence?: number | null;
  salience?: number | null;
  confirmation_status?: MemoryConfirmationStatus;
  valid_from?: string | null;
  valid_to?: string | null;
  last_confirmed_at?: string | null;
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

export type OpenLoopRecord = {
  id: string;
  memory_id: string | null;
  title: string;
  status: OpenLoopStatus;
  opened_at: string;
  due_at: string | null;
  resolved_at: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
};

export type OpenLoopListSummary = {
  status: OpenLoopStatusFilter;
  limit: number;
  returned_count: number;
  total_count: number;
  has_more: boolean;
  order: string[];
};

export type EntityType = "person" | "merchant" | "product" | "project" | "routine";

export type EntityRecord = {
  id: string;
  entity_type: EntityType;
  name: string;
  source_memory_ids: string[];
  created_at: string;
};

export type EntityListSummary = {
  total_count: number;
  order: string[];
};

export type EntityEdgeRecord = {
  id: string;
  from_entity_id: string;
  to_entity_id: string;
  relationship_type: string;
  valid_from: string | null;
  valid_to: string | null;
  source_memory_ids: string[];
  created_at: string;
};

export type EntityEdgeListSummary = {
  entity_id: string;
  total_count: number;
  order: string[];
};

export type GmailReadonlyScope = "https://www.googleapis.com/auth/gmail.readonly";

export type GmailAccountRecord = {
  id: string;
  provider: string;
  auth_kind: string;
  provider_account_id: string;
  email_address: string;
  display_name: string | null;
  scope: GmailReadonlyScope;
  created_at: string;
  updated_at: string;
};

export type GmailAccountListSummary = {
  total_count: number;
  order: string[];
};

export type GmailAccountConnectPayload = {
  user_id: string;
  provider_account_id: string;
  email_address: string;
  display_name?: string | null;
  scope: GmailReadonlyScope;
  access_token: string;
  refresh_token?: string | null;
  client_id?: string | null;
  client_secret?: string | null;
  access_token_expires_at?: string | null;
};

export type GmailMessageIngestPayload = {
  user_id: string;
  task_workspace_id: string;
};

export type GmailMessageIngestionRecord = {
  provider_message_id: string;
  artifact_relative_path: string;
  media_type: string;
};

export type GmailMessageIngestionResponse = {
  account: GmailAccountRecord;
  message: GmailMessageIngestionRecord;
  artifact: TaskArtifactRecord;
  summary: TaskArtifactChunkListSummary;
};

export type CalendarReadonlyScope = "https://www.googleapis.com/auth/calendar.readonly";

export type CalendarAccountRecord = {
  id: string;
  provider: string;
  auth_kind: string;
  provider_account_id: string;
  email_address: string;
  display_name: string | null;
  scope: CalendarReadonlyScope;
  created_at: string;
  updated_at: string;
};

export type CalendarAccountListSummary = {
  total_count: number;
  order: string[];
};

export type CalendarAccountConnectPayload = {
  user_id: string;
  provider_account_id: string;
  email_address: string;
  display_name?: string | null;
  scope: CalendarReadonlyScope;
  access_token: string;
};

export type CalendarEventIngestPayload = {
  user_id: string;
  task_workspace_id: string;
};

export type CalendarEventIngestionRecord = {
  provider_event_id: string;
  artifact_relative_path: string;
  media_type: string;
};

export type CalendarEventIngestionResponse = {
  account: CalendarAccountRecord;
  event: CalendarEventIngestionRecord;
  artifact: TaskArtifactRecord;
  summary: TaskArtifactChunkListSummary;
};

export type CalendarEventSummaryRecord = {
  provider_event_id: string;
  status: string | null;
  summary: string | null;
  start_time: string | null;
  end_time: string | null;
  html_link: string | null;
  updated_at: string | null;
};

export type CalendarEventListSummary = {
  total_count: number;
  limit: number;
  order: string[];
  time_min: string | null;
  time_max: string | null;
};

export type CalendarEventListResponse = {
  account: CalendarAccountRecord;
  items: CalendarEventSummaryRecord[];
  summary: CalendarEventListSummary;
};

export type CalendarEventListQuery = {
  limit?: number;
  timeMin?: string;
  timeMax?: string;
};

export type TaskWorkspaceStatus = "active";

export type TaskWorkspaceRecord = {
  id: string;
  task_id: string;
  status: TaskWorkspaceStatus;
  local_path: string;
  created_at: string;
  updated_at: string;
};

export type TaskWorkspaceListSummary = {
  total_count: number;
  order: string[];
};

export type TaskArtifactStatus = "registered";
export type TaskArtifactIngestionStatus = "pending" | "ingested";

export type TaskArtifactRecord = {
  id: string;
  task_id: string;
  task_workspace_id: string;
  status: TaskArtifactStatus;
  ingestion_status: TaskArtifactIngestionStatus;
  relative_path: string;
  media_type_hint: string | null;
  created_at: string;
  updated_at: string;
};

export type TaskArtifactListSummary = {
  total_count: number;
  order: string[];
};

export type TaskArtifactChunkRecord = {
  id: string;
  task_artifact_id: string;
  sequence_no: number;
  char_start: number;
  char_end_exclusive: number;
  text: string;
  created_at: string;
  updated_at: string;
};

export type TaskArtifactChunkListSummary = {
  total_count: number;
  total_characters: number;
  media_type: string;
  chunking_rule: string;
  order: string[];
};

export type MemoryReviewLabelPayload = {
  user_id: string;
  label: MemoryReviewLabelValue;
  note?: string | null;
};

export type MemoryAdmitPayload = {
  user_id: string;
  memory_key: string;
  value: unknown | null;
  source_event_ids: string[];
  delete_requested?: boolean;
  open_loop?: {
    title: string;
    due_at?: string | null;
  };
};

export type ExplicitCommitmentPattern =
  | "remind_me_to"
  | "i_need_to"
  | "dont_let_me_forget_to"
  | "remember_to";

export type ExplicitCommitmentOpenLoopDecision =
  | "CREATED"
  | "NOOP_ACTIVE_EXISTS"
  | "NOOP_MEMORY_NOT_PERSISTED";

export type ExplicitPreferencePattern =
  | "i_like"
  | "i_dont_like"
  | "i_prefer"
  | "remember_that_i_like"
  | "remember_that_i_dont_like"
  | "remember_that_i_prefer";

export type ExtractExplicitSignalsPayload = {
  user_id: string;
  source_event_id: string;
};

export type ExtractExplicitCommitmentsPayload = {
  user_id: string;
  source_event_id: string;
};

export type ExtractedPreferenceCandidateRecord = {
  memory_key: string;
  value: unknown;
  source_event_ids: string[];
  delete_requested: boolean;
  pattern: ExplicitPreferencePattern;
  subject_text: string;
};

export type ExplicitPreferenceAdmissionRecord = {
  decision: "NOOP" | "ADD" | "UPDATE" | "DELETE";
  reason: string;
  memory: PersistedMemoryRecord | null;
  revision: PersistedMemoryRevisionRecord | null;
};

export type ExplicitPreferenceExtractionResponse = {
  candidates: ExtractedPreferenceCandidateRecord[];
  admissions: ExplicitPreferenceAdmissionRecord[];
  summary: {
    source_event_id: string;
    source_event_kind: string;
    candidate_count: number;
    admission_count: number;
    persisted_change_count: number;
    noop_count: number;
  };
};

export type ExtractedCommitmentCandidateRecord = {
  memory_key: string;
  value: unknown;
  source_event_ids: string[];
  delete_requested: boolean;
  pattern: ExplicitCommitmentPattern;
  commitment_text: string;
  open_loop_title: string;
};

export type ExplicitCommitmentAdmissionRecord = {
  decision: "NOOP" | "ADD" | "UPDATE" | "DELETE";
  reason: string;
  memory: PersistedMemoryRecord | null;
  revision: PersistedMemoryRevisionRecord | null;
  open_loop: {
    decision: ExplicitCommitmentOpenLoopDecision;
    reason: string;
    open_loop: OpenLoopRecord | null;
  };
};

export type ExplicitCommitmentExtractionResponse = {
  candidates: ExtractedCommitmentCandidateRecord[];
  admissions: ExplicitCommitmentAdmissionRecord[];
  summary: {
    source_event_id: string;
    source_event_kind: string;
    candidate_count: number;
    admission_count: number;
    persisted_change_count: number;
    noop_count: number;
    open_loop_created_count: number;
    open_loop_noop_count: number;
  };
};

export type ExplicitSignalCaptureResponse = {
  preferences: ExplicitPreferenceExtractionResponse;
  commitments: ExplicitCommitmentExtractionResponse;
  summary: {
    source_event_id: string;
    source_event_kind: string;
    candidate_count: number;
    admission_count: number;
    persisted_change_count: number;
    noop_count: number;
    open_loop_created_count: number;
    open_loop_noop_count: number;
    preference_candidate_count: number;
    preference_admission_count: number;
    commitment_candidate_count: number;
    commitment_admission_count: number;
  };
};

export type ContinuityCaptureExplicitSignal =
  | "remember_this"
  | "task"
  | "decision"
  | "commitment"
  | "waiting_for"
  | "blocker"
  | "next_action"
  | "note";

export type ContinuityCaptureAdmissionPosture = "DERIVED" | "TRIAGE";

export type ContinuityObjectType =
  | "Note"
  | "MemoryFact"
  | "Decision"
  | "Commitment"
  | "WaitingFor"
  | "Blocker"
  | "NextAction";

export type ContinuityCaptureEventRecord = {
  id: string;
  raw_content: string;
  explicit_signal: ContinuityCaptureExplicitSignal | null;
  admission_posture: ContinuityCaptureAdmissionPosture;
  admission_reason: string;
  created_at: string;
};

export type ContinuityObjectRecord = {
  id: string;
  capture_event_id: string;
  object_type: ContinuityObjectType;
  status: "active" | "completed" | "cancelled" | "superseded" | "stale";
  title: string;
  body: JsonObject;
  provenance: JsonObject;
  confidence: number;
  created_at: string;
  updated_at: string;
};

export type ContinuityReviewStatusFilter =
  | "correction_ready"
  | "active"
  | "stale"
  | "superseded"
  | "deleted"
  | "all";

export type ContinuityCorrectionAction = "confirm" | "edit" | "delete" | "supersede" | "mark_stale";

export type ContinuityReviewObject = {
  id: string;
  capture_event_id: string;
  object_type: ContinuityObjectType;
  status: string;
  title: string;
  body: JsonObject;
  provenance: JsonObject;
  confidence: number;
  last_confirmed_at: string | null;
  supersedes_object_id: string | null;
  superseded_by_object_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ContinuityCorrectionEvent = {
  id: string;
  continuity_object_id: string;
  action: ContinuityCorrectionAction;
  reason: string | null;
  before_snapshot: JsonObject;
  after_snapshot: JsonObject;
  payload: JsonObject;
  created_at: string;
};

export type ContinuityReviewQueueSummary = {
  status: ContinuityReviewStatusFilter;
  limit: number;
  returned_count: number;
  total_count: number;
  order: string[];
};

export type ContinuityReviewDetail = {
  continuity_object: ContinuityReviewObject;
  correction_events: ContinuityCorrectionEvent[];
  supersession_chain: {
    supersedes: ContinuityReviewObject | null;
    superseded_by: ContinuityReviewObject | null;
  };
};

export type ContinuityCorrectionPayload = {
  user_id: string;
  action: ContinuityCorrectionAction;
  reason?: string | null;
  title?: string | null;
  body?: JsonObject | null;
  provenance?: JsonObject | null;
  confidence?: number | null;
  replacement_title?: string | null;
  replacement_body?: JsonObject | null;
  replacement_provenance?: JsonObject | null;
  replacement_confidence?: number | null;
};

export type ContinuityCaptureInboxItem = {
  capture_event: ContinuityCaptureEventRecord;
  derived_object: ContinuityObjectRecord | null;
};

export type ContinuityCaptureInboxSummary = {
  limit: number;
  returned_count: number;
  total_count: number;
  derived_count: number;
  triage_count: number;
  order: string[];
};

export type ContinuityCaptureCreatePayload = {
  user_id: string;
  raw_content: string;
  explicit_signal?: ContinuityCaptureExplicitSignal | null;
};

export type ContinuityRecallScopeKind = "thread" | "task" | "project" | "person";

export type ContinuityRecallScopeMatch = {
  kind: ContinuityRecallScopeKind;
  value: string;
};

export type ContinuityRecallProvenanceReference = {
  source_kind: string;
  source_id: string;
};

export type ContinuityRecallOrdering = {
  scope_match_count: number;
  query_term_match_count: number;
  confirmation_rank: number;
  posture_rank: number;
  lifecycle_rank: number;
  confidence: number;
};

export type ContinuityRecallResult = {
  id: string;
  capture_event_id: string;
  object_type: ContinuityObjectType;
  status: string;
  title: string;
  body: JsonObject;
  provenance: JsonObject;
  confirmation_status: MemoryConfirmationStatus;
  admission_posture: ContinuityCaptureAdmissionPosture;
  confidence: number;
  relevance: number;
  last_confirmed_at: string | null;
  supersedes_object_id: string | null;
  superseded_by_object_id: string | null;
  scope_matches: ContinuityRecallScopeMatch[];
  provenance_references: ContinuityRecallProvenanceReference[];
  ordering: ContinuityRecallOrdering;
  created_at: string;
  updated_at: string;
};

export type ContinuityRecallSummary = {
  query: string | null;
  filters: {
    thread_id?: string;
    task_id?: string;
    project?: string;
    person?: string;
    since: string | null;
    until: string | null;
  };
  limit: number;
  returned_count: number;
  total_count: number;
  order: string[];
};

export type ContinuityResumptionEmptyState = {
  is_empty: boolean;
  message: string;
};

export type ContinuityResumptionSingleSection = {
  item: ContinuityRecallResult | null;
  empty_state: ContinuityResumptionEmptyState;
};

export type ContinuityResumptionListSection = {
  items: ContinuityRecallResult[];
  summary: ResumptionBriefSectionSummary;
  empty_state: ContinuityResumptionEmptyState;
};

export type ContinuityResumptionBrief = {
  assembly_version: string;
  scope: ContinuityRecallSummary["filters"];
  last_decision: ContinuityResumptionSingleSection;
  open_loops: ContinuityResumptionListSection;
  recent_changes: ContinuityResumptionListSection;
  next_action: ContinuityResumptionSingleSection;
  sources: string[];
};

export type OpenLoopCreatePayload = {
  user_id: string;
  memory_id?: string | null;
  title: string;
  due_at?: string | null;
};

export type OpenLoopStatusUpdatePayload = {
  user_id: string;
  status: OpenLoopStatus;
  resolution_note?: string | null;
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

export type PersistedMemoryRecord = {
  id: string;
  user_id: string;
  memory_key: string;
  value: unknown;
  status: "active" | "deleted";
  source_event_ids: string[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type PersistedMemoryRevisionRecord = {
  id: string;
  user_id: string;
  memory_id: string;
  sequence_no: number;
  action: "NOOP" | "ADD" | "UPDATE" | "DELETE";
  memory_key: string;
  previous_value: unknown | null;
  new_value: unknown | null;
  source_event_ids: string[];
  candidate: JsonObject;
  created_at: string;
};

export type MemoryAdmissionResponse = {
  decision: "NOOP" | "ADD" | "UPDATE" | "DELETE";
  reason: string;
  memory: PersistedMemoryRecord | null;
  revision: PersistedMemoryRevisionRecord | null;
  open_loop?: OpenLoopRecord | null;
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

export function listAgentProfiles(apiBaseUrl: string) {
  return requestJson<{ items: AgentProfileItem[]; summary: AgentProfileListSummary }>(
    apiBaseUrl,
    "/v0/agent-profiles",
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

export function getThreadResumptionBrief(
  apiBaseUrl: string,
  threadId: string,
  userId: string,
  options?: {
    maxEvents?: number;
    maxOpenLoops?: number;
    maxMemories?: number;
  },
) {
  return requestJson<{ brief: ResumptionBrief }>(
    apiBaseUrl,
    `/v0/threads/${threadId}/resumption-brief`,
    undefined,
    {
      user_id: userId,
      max_events:
        typeof options?.maxEvents === "number" ? String(Math.max(0, options.maxEvents)) : undefined,
      max_open_loops:
        typeof options?.maxOpenLoops === "number"
          ? String(Math.max(0, options.maxOpenLoops))
          : undefined,
      max_memories:
        typeof options?.maxMemories === "number" ? String(Math.max(0, options.maxMemories)) : undefined,
    },
  );
}

export function queryContinuityRecall(
  apiBaseUrl: string,
  userId: string,
  options?: {
    query?: string;
    threadId?: string;
    taskId?: string;
    project?: string;
    person?: string;
    since?: string;
    until?: string;
    limit?: number;
  },
) {
  const query = options?.query?.trim();
  const threadId = options?.threadId?.trim();
  const taskId = options?.taskId?.trim();
  const project = options?.project?.trim();
  const person = options?.person?.trim();
  const since = options?.since?.trim();
  const until = options?.until?.trim();
  const limit =
    typeof options?.limit === "number" && Number.isFinite(options.limit) && options.limit > 0
      ? String(Math.trunc(options.limit))
      : undefined;

  return requestJson<{ items: ContinuityRecallResult[]; summary: ContinuityRecallSummary }>(
    apiBaseUrl,
    "/v0/continuity/recall",
    undefined,
    {
      user_id: userId,
      query: query || undefined,
      thread_id: threadId || undefined,
      task_id: taskId || undefined,
      project: project || undefined,
      person: person || undefined,
      since: since || undefined,
      until: until || undefined,
      limit,
    },
  );
}

export function getContinuityResumptionBrief(
  apiBaseUrl: string,
  userId: string,
  options?: {
    query?: string;
    threadId?: string;
    taskId?: string;
    project?: string;
    person?: string;
    since?: string;
    until?: string;
    maxRecentChanges?: number;
    maxOpenLoops?: number;
  },
) {
  const query = options?.query?.trim();
  const threadId = options?.threadId?.trim();
  const taskId = options?.taskId?.trim();
  const project = options?.project?.trim();
  const person = options?.person?.trim();
  const since = options?.since?.trim();
  const until = options?.until?.trim();
  const maxRecentChanges =
    typeof options?.maxRecentChanges === "number" &&
    Number.isFinite(options.maxRecentChanges) &&
    options.maxRecentChanges >= 0
      ? String(Math.trunc(options.maxRecentChanges))
      : undefined;
  const maxOpenLoops =
    typeof options?.maxOpenLoops === "number" &&
    Number.isFinite(options.maxOpenLoops) &&
    options.maxOpenLoops >= 0
      ? String(Math.trunc(options.maxOpenLoops))
      : undefined;

  return requestJson<{ brief: ContinuityResumptionBrief }>(
    apiBaseUrl,
    "/v0/continuity/resumption-brief",
    undefined,
    {
      user_id: userId,
      query: query || undefined,
      thread_id: threadId || undefined,
      task_id: taskId || undefined,
      project: project || undefined,
      person: person || undefined,
      since: since || undefined,
      until: until || undefined,
      max_recent_changes: maxRecentChanges,
      max_open_loops: maxOpenLoops,
    },
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

export function listTaskRuns(apiBaseUrl: string, taskId: string, userId: string) {
  return requestJson<{ items: TaskRunItem[]; summary: TaskRunListSummary }>(
    apiBaseUrl,
    `/v0/tasks/${taskId}/runs`,
    undefined,
    { user_id: userId },
  );
}

export function executeApproval(
  apiBaseUrl: string,
  approvalId: string,
  userId: string,
  taskRunId?: string | null,
) {
  const payload: { user_id: string; task_run_id?: string } = {
    user_id: userId,
  };
  if (taskRunId !== null && taskRunId !== undefined) {
    payload.task_run_id = taskRunId;
  }
  return requestJson<ApprovalExecutionResponse>(apiBaseUrl, `/v0/approvals/${approvalId}/execute`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function admitMemory(apiBaseUrl: string, payload: MemoryAdmitPayload) {
  return requestJson<MemoryAdmissionResponse>(apiBaseUrl, "/v0/memories/admit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function extractExplicitCommitments(
  apiBaseUrl: string,
  payload: ExtractExplicitCommitmentsPayload,
) {
  return requestJson<ExplicitCommitmentExtractionResponse>(
    apiBaseUrl,
    "/v0/open-loops/extract-explicit-commitments",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function captureExplicitSignals(
  apiBaseUrl: string,
  payload: ExtractExplicitSignalsPayload,
) {
  return requestJson<ExplicitSignalCaptureResponse>(
    apiBaseUrl,
    "/v0/memories/capture-explicit-signals",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function createContinuityCapture(
  apiBaseUrl: string,
  payload: ContinuityCaptureCreatePayload,
) {
  return requestJson<{ capture: ContinuityCaptureInboxItem }>(
    apiBaseUrl,
    "/v0/continuity/captures",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function listContinuityCaptures(
  apiBaseUrl: string,
  userId: string,
  options?: {
    limit?: number;
  },
) {
  return requestJson<{ items: ContinuityCaptureInboxItem[]; summary: ContinuityCaptureInboxSummary }>(
    apiBaseUrl,
    "/v0/continuity/captures",
    undefined,
    {
      user_id: userId,
      limit: options?.limit ? String(options.limit) : undefined,
    },
  );
}

export function getContinuityCaptureDetail(
  apiBaseUrl: string,
  captureEventId: string,
  userId: string,
) {
  return requestJson<{ capture: ContinuityCaptureInboxItem }>(
    apiBaseUrl,
    `/v0/continuity/captures/${captureEventId}`,
    undefined,
    {
      user_id: userId,
    },
  );
}

export function listContinuityReviewQueue(
  apiBaseUrl: string,
  userId: string,
  options?: {
    status?: ContinuityReviewStatusFilter;
    limit?: number;
  },
) {
  return requestJson<{ items: ContinuityReviewObject[]; summary: ContinuityReviewQueueSummary }>(
    apiBaseUrl,
    "/v0/continuity/review-queue",
    undefined,
    {
      user_id: userId,
      status: options?.status ?? "correction_ready",
      limit: options?.limit ? String(options.limit) : undefined,
    },
  );
}

export function getContinuityReviewDetail(
  apiBaseUrl: string,
  continuityObjectId: string,
  userId: string,
) {
  return requestJson<{ review: ContinuityReviewDetail }>(
    apiBaseUrl,
    `/v0/continuity/review-queue/${continuityObjectId}`,
    undefined,
    {
      user_id: userId,
    },
  );
}

export function applyContinuityCorrection(
  apiBaseUrl: string,
  continuityObjectId: string,
  payload: ContinuityCorrectionPayload,
) {
  return requestJson<{
    continuity_object: ContinuityReviewObject;
    correction_event: ContinuityCorrectionEvent;
    replacement_object: ContinuityReviewObject | null;
  }>(
    apiBaseUrl,
    `/v0/continuity/review-queue/${continuityObjectId}/corrections`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function listOpenLoops(
  apiBaseUrl: string,
  userId: string,
  options?: {
    status?: OpenLoopStatusFilter;
    limit?: number;
  },
) {
  return requestJson<{ items: OpenLoopRecord[]; summary: OpenLoopListSummary }>(
    apiBaseUrl,
    "/v0/open-loops",
    undefined,
    {
      user_id: userId,
      status: options?.status,
      limit: options?.limit ? String(options.limit) : undefined,
    },
  );
}

export function getOpenLoopDetail(apiBaseUrl: string, openLoopId: string, userId: string) {
  return requestJson<{ open_loop: OpenLoopRecord }>(
    apiBaseUrl,
    `/v0/open-loops/${openLoopId}`,
    undefined,
    { user_id: userId },
  );
}

export function createOpenLoop(apiBaseUrl: string, payload: OpenLoopCreatePayload) {
  return requestJson<{ open_loop: OpenLoopRecord }>(apiBaseUrl, "/v0/open-loops", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateOpenLoopStatus(
  apiBaseUrl: string,
  openLoopId: string,
  payload: OpenLoopStatusUpdatePayload,
) {
  return requestJson<{ open_loop: OpenLoopRecord }>(
    apiBaseUrl,
    `/v0/open-loops/${openLoopId}/status`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
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

export function connectGmailAccount(
  apiBaseUrl: string,
  payload: GmailAccountConnectPayload,
) {
  return requestJson<{ account: GmailAccountRecord }>(apiBaseUrl, "/v0/gmail-accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listGmailAccounts(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: GmailAccountRecord[]; summary: GmailAccountListSummary }>(
    apiBaseUrl,
    "/v0/gmail-accounts",
    undefined,
    { user_id: userId },
  );
}

export function getGmailAccountDetail(apiBaseUrl: string, gmailAccountId: string, userId: string) {
  return requestJson<{ account: GmailAccountRecord }>(
    apiBaseUrl,
    `/v0/gmail-accounts/${gmailAccountId}`,
    undefined,
    { user_id: userId },
  );
}

export function ingestGmailMessage(
  apiBaseUrl: string,
  gmailAccountId: string,
  providerMessageId: string,
  payload: GmailMessageIngestPayload,
) {
  return requestJson<GmailMessageIngestionResponse>(
    apiBaseUrl,
    `/v0/gmail-accounts/${gmailAccountId}/messages/${providerMessageId}/ingest`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function connectCalendarAccount(
  apiBaseUrl: string,
  payload: CalendarAccountConnectPayload,
) {
  return requestJson<{ account: CalendarAccountRecord }>(apiBaseUrl, "/v0/calendar-accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listCalendarAccounts(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: CalendarAccountRecord[]; summary: CalendarAccountListSummary }>(
    apiBaseUrl,
    "/v0/calendar-accounts",
    undefined,
    { user_id: userId },
  );
}

export function getCalendarAccountDetail(
  apiBaseUrl: string,
  calendarAccountId: string,
  userId: string,
) {
  return requestJson<{ account: CalendarAccountRecord }>(
    apiBaseUrl,
    `/v0/calendar-accounts/${calendarAccountId}`,
    undefined,
    { user_id: userId },
  );
}

export function listCalendarEvents(
  apiBaseUrl: string,
  calendarAccountId: string,
  userId: string,
  query?: CalendarEventListQuery,
) {
  const limitValue =
    typeof query?.limit === "number" && Number.isFinite(query.limit) && query.limit > 0
      ? String(Math.trunc(query.limit))
      : undefined;
  const timeMin = query?.timeMin?.trim() ? query.timeMin.trim() : undefined;
  const timeMax = query?.timeMax?.trim() ? query.timeMax.trim() : undefined;

  return requestJson<CalendarEventListResponse>(
    apiBaseUrl,
    `/v0/calendar-accounts/${calendarAccountId}/events`,
    undefined,
    {
      user_id: userId,
      limit: limitValue,
      time_min: timeMin,
      time_max: timeMax,
    },
  );
}

export function ingestCalendarEvent(
  apiBaseUrl: string,
  calendarAccountId: string,
  providerEventId: string,
  payload: CalendarEventIngestPayload,
) {
  return requestJson<CalendarEventIngestionResponse>(
    apiBaseUrl,
    `/v0/calendar-accounts/${calendarAccountId}/events/${providerEventId}/ingest`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function listTaskWorkspaces(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: TaskWorkspaceRecord[]; summary: TaskWorkspaceListSummary }>(
    apiBaseUrl,
    "/v0/task-workspaces",
    undefined,
    { user_id: userId },
  );
}

export function getTaskWorkspaceDetail(apiBaseUrl: string, taskWorkspaceId: string, userId: string) {
  return requestJson<{ workspace: TaskWorkspaceRecord }>(
    apiBaseUrl,
    `/v0/task-workspaces/${taskWorkspaceId}`,
    undefined,
    { user_id: userId },
  );
}

export function listTaskArtifacts(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: TaskArtifactRecord[]; summary: TaskArtifactListSummary }>(
    apiBaseUrl,
    "/v0/task-artifacts",
    undefined,
    { user_id: userId },
  );
}

export function getTaskArtifactDetail(apiBaseUrl: string, taskArtifactId: string, userId: string) {
  return requestJson<{ artifact: TaskArtifactRecord }>(
    apiBaseUrl,
    `/v0/task-artifacts/${taskArtifactId}`,
    undefined,
    { user_id: userId },
  );
}

export function listTaskArtifactChunks(apiBaseUrl: string, taskArtifactId: string, userId: string) {
  return requestJson<{ items: TaskArtifactChunkRecord[]; summary: TaskArtifactChunkListSummary }>(
    apiBaseUrl,
    `/v0/task-artifacts/${taskArtifactId}/chunks`,
    undefined,
    { user_id: userId },
  );
}

export function listEntities(apiBaseUrl: string, userId: string) {
  return requestJson<{ items: EntityRecord[]; summary: EntityListSummary }>(
    apiBaseUrl,
    "/v0/entities",
    undefined,
    { user_id: userId },
  );
}

export function getEntityDetail(apiBaseUrl: string, entityId: string, userId: string) {
  return requestJson<{ entity: EntityRecord }>(
    apiBaseUrl,
    `/v0/entities/${entityId}`,
    undefined,
    { user_id: userId },
  );
}

export function listEntityEdges(apiBaseUrl: string, entityId: string, userId: string) {
  return requestJson<{ items: EntityEdgeRecord[]; summary: EntityEdgeListSummary }>(
    apiBaseUrl,
    `/v0/entities/${entityId}/edges`,
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
