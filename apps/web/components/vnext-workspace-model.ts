import type {
  ApiSource,
  JsonObject,
  VNextArtifactQualityEvalRecord,
  VNextArtifactRecord,
  VNextBeliefRecord,
  VNextBrainCharterRecord,
  VNextConnectorHealthRecord,
  VNextContextPack,
  VNextDogfoodingDashboard,
  VNextDoctorPayload,
  VNextEventRecord,
  VNextMemoryRecord,
  VNextOpenLoopRecord,
  VNextPersonRecord,
  VNextPolicyTelemetrySummary,
  VNextProjectDashboard,
  VNextProjectRecord,
  VNextSchedulerStatus,
  VNextSourceRecord,
  VNextSourceTracePayload,
  VNextTaskRecord,
  VNextWorkspacePayload,
} from "../lib/api";

export const VNEXT_DOMAIN_OPTIONS = [
  { value: "professional", label: "Work" },
  { value: "personal", label: "Personal" },
  { value: "family", label: "Family" },
  { value: "health", label: "Health" },
  { value: "spiritual", label: "Spiritual" },
  { value: "financial", label: "Financial" },
  { value: "legal", label: "Legal" },
  { value: "learning", label: "Learning" },
  { value: "relationship", label: "Relationship" },
  { value: "project", label: "Project" },
  { value: "agent_run", label: "Agent run" },
  { value: "system", label: "System" },
  { value: "unknown", label: "Unknown" },
] as const;

export const VNEXT_SENSITIVITY_OPTIONS = [
  { value: "public", label: "Public" },
  { value: "internal", label: "Internal" },
  { value: "private", label: "Private" },
  { value: "confidential", label: "Confidential" },
  { value: "highly_sensitive", label: "Highly sensitive" },
  { value: "sacred", label: "Sacred" },
  { value: "regulated", label: "Regulated" },
  { value: "unknown", label: "Unknown" },
] as const;

export const VNEXT_SUPPORTED_CONNECTOR_IDS = [
  "telegram",
  "browser_clipper",
  "local_folder",
  "agent_output",
  "pdf_document",
  "docx_document",
  "csv_table",
  "screenshot_ocr",
  "voice_transcription",
] as const;

export type Domain = (typeof VNEXT_DOMAIN_OPTIONS)[number]["value"];
export type Sensitivity = (typeof VNEXT_SENSITIVITY_OPTIONS)[number]["value"];

export type AskAnswer = {
  question: string;
  summary: string;
  memoriesUsed: string[];
  contradictions: string[];
  why: string[];
  sources: string[];
  domain: Domain;
  sensitivity: Sensitivity;
};

export type ConnectorSetting = {
  id: string;
  name: string;
  stage: string;
  status: string;
  defaultDomain: Domain;
  defaultSensitivity: Sensitivity;
  cursor: string;
  evidence: string;
  failureMode: string;
};

export type WorkspaceSummary = VNextWorkspacePayload["summary"];

export type WorkspaceView = {
  summary: WorkspaceSummary;
  sources: VNextSourceRecord[];
  reviewItems: VNextMemoryRecord[];
  artifacts: VNextArtifactRecord[];
  projects: VNextProjectRecord[];
  projectDashboards: VNextProjectDashboard[];
  openLoops: VNextOpenLoopRecord[];
  people: VNextPersonRecord[];
  beliefs: VNextBeliefRecord[];
  tasks: VNextTaskRecord[];
  recentEvents: VNextEventRecord[];
  qualityEvals: VNextArtifactQualityEvalRecord[];
  connectorHealth: { items: VNextConnectorHealthRecord[]; count: number; order: string[] };
  dogfooding: VNextDogfoodingDashboard;
  doctor: VNextDoctorPayload;
  traceability: { items: VNextSourceTracePayload[]; count: number; order: string[] };
  agentActivity: NonNullable<VNextWorkspacePayload["agent_activity"]>;
  policyTelemetry: VNextPolicyTelemetrySummary;
  scheduler: VNextSchedulerStatus;
  brainCharter: VNextBrainCharterRecord | null;
};

export type VNextBrainWorkspaceProps = {
  apiBaseUrl?: string;
  userId?: string;
  initialSource?: ApiSource;
};

export const SURFACES = [
  "Home",
  "Inbox",
  "Ask Alice",
  "Daily Brief",
  "Weekly Synthesis",
  "Queue",
  "Generated",
  "Model Comparison",
  "Memory Review",
  "Projects",
  "People",
  "Beliefs",
  "Open Loops",
  "Agent Activity",
  "Schedules",
  "Timeline",
  "Trace",
  "Graph",
  "Connectors",
  "Doctor",
  "Settings",
];

export function optionLabel<T extends string>(
  options: readonly { value: T; label: string }[],
  value: T,
) {
  return options.find((option) => option.value === value)?.label ?? value;
}

export function asDomain(value: unknown): Domain {
  return VNEXT_DOMAIN_OPTIONS.some((option) => option.value === value)
    ? (value as Domain)
    : "unknown";
}

export function asSensitivity(value: unknown): Sensitivity {
  return VNEXT_SENSITIVITY_OPTIONS.some((option) => option.value === value)
    ? (value as Sensitivity)
    : "unknown";
}

export function domainLabel(domain: Domain) {
  return optionLabel(VNEXT_DOMAIN_OPTIONS, domain);
}

export function sensitivityLabel(sensitivity: Sensitivity) {
  return optionLabel(VNEXT_SENSITIVITY_OPTIONS, sensitivity);
}

export function asRecord(value: unknown): JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as JsonObject)
    : {};
}

export function textValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

export function summarizeSources(sources: string[]) {
  return sources.length ? sources.join(", ") : "No source references";
}

export function memoryText(memory: VNextMemoryRecord) {
  return memory.canonical_text || textValue(memory.summary) || textValue(memory.title) || memory.memory_key;
}

export function agenticMemoryMetadata(memory: VNextMemoryRecord) {
  return asRecord(asRecord(memory.metadata_json).agentic_memory);
}

export function sourceText(source: VNextSourceRecord) {
  const metadata = asRecord(source.metadata_json);
  return textValue(metadata.raw_text) || textValue(source.title) || source.source_type;
}

export function artifactExcerpt(artifact: VNextArtifactRecord) {
  return artifact.content_markdown.replace(/\s+/g, " ").trim().slice(0, 320) || "No artifact body yet.";
}

export function eventTitle(event: VNextEventRecord) {
  const target = event.target_type && event.target_id ? ` ${event.target_type}:${event.target_id}` : "";
  return `${event.event_type}${target}`;
}

export function createSummary(view: Omit<WorkspaceView, "summary">): WorkspaceSummary {
  const memoryStatusCounts = Object.fromEntries(
    Array.from(new Set(view.reviewItems.map((item) => item.status ?? "unknown"))).map((status) => [
      status,
      view.reviewItems.filter((item) => (item.status ?? "unknown") === status).length,
    ]),
  );
  const artifactStatusCounts = Object.fromEntries(
    Array.from(new Set(view.artifacts.map((item) => item.status ?? "unknown"))).map((status) => [
      status,
      view.artifacts.filter((item) => (item.status ?? "unknown") === status).length,
    ]),
  );
  const openLoopStatusCounts = Object.fromEntries(
    Array.from(new Set(view.openLoops.map((item) => item.status ?? "unknown"))).map((status) => [
      status,
      view.openLoops.filter((item) => (item.status ?? "unknown") === status).length,
    ]),
  );

  return {
    source_count: view.sources.length,
    candidate_memory_count: view.reviewItems.filter((item) => item.status === "candidate").length,
    review_memory_count: view.reviewItems.length,
    artifact_count: view.artifacts.length,
    open_loop_count: view.openLoops.filter((item) => item.status === "open").length,
    project_count: view.projects.length,
    event_count: view.recentEvents.length,
    agent_count: view.agentActivity.agents.length,
    scheduler_enabled_count: view.scheduler.enabled_count,
    quality_eval_count: view.qualityEvals.length,
    memory_status_counts: memoryStatusCounts,
    artifact_status_counts: artifactStatusCounts,
    open_loop_status_counts: openLoopStatusCounts,
  };
}

export const EMPTY_AGENT_ACTIVITY: NonNullable<VNextWorkspacePayload["agent_activity"]> = {
  agents: [],
  recent_events: [],
  policy_blocks: [],
  generated_artifacts: [],
  pending_review_items: [],
  recent_commits: [],
  inline_confirmations: [],
};

export const EMPTY_POLICY_TELEMETRY: VNextPolicyTelemetrySummary = {
  total_agent_events: 0,
  total_policy_decisions: 0,
  policy_blocks_by_agent: [],
  policy_filters_by_agent: [],
  requires_review_by_agent: [],
  restricted_domains_requested: [],
  workflows_triggered_by_agents: [],
  memory_proposals_by_agent: [],
  artifact_generation_by_agent: [],
};

export const EMPTY_SCHEDULER: VNextSchedulerStatus = {
  mode: "local_governed",
  disabled_by_default: true,
  workflows: [],
  recent_runs: [],
  enabled_count: 0,
  paused_count: 0,
  last_failure: null,
  recent_failures: [],
  last_due_scan: null,
  next_due_workflow: null,
  currently_running_workflow: null,
  last_success_by_workflow: {},
  daemon: { configured: false, running: false },
};

export const EMPTY_CONNECTOR_HEALTH: { items: VNextConnectorHealthRecord[]; count: number; order: string[] } = {
  items: [],
  count: 0,
  order: [],
};

export const EMPTY_DOGFOODING: VNextDogfoodingDashboard = {
  captures_by_connector: [],
  captures_today: 0,
  captures_this_week: 0,
  capture_trend_by_day: [],
  capture_trend_by_week: [],
  candidate_memories_created: 0,
  memory_status_counts: {},
  candidate_memory_review_rate: 0,
  generated_artifacts_created: 0,
  artifact_status_counts: {},
  artifact_quality_average: null,
  artifact_quality_rating_count: 0,
  artifact_rating_trend: [],
  daily_brief_review_status: null,
  weekly_synthesis_review_status: null,
  connections_surfaced: 0,
  contradictions_surfaced: 0,
  open_loop_status_counts: {},
  open_loops_created: 0,
  open_loops_closed: 0,
  agent_context_packs_requested: 0,
  agent_memory_proposals: 0,
  policy_blocks_filters: 0,
  connector_failures: 0,
  top_failure_causes: [],
  scheduler_freshness: { recent_success: false, recent_failure_count: 0 },
  agent_activity_summary: { outputs_ingested: 0, context_packs_requested: 0, memory_proposals: 0 },
  policy_block_filter_summary: { count: 0, event_types: {} },
  dogfood_readiness: {
    status: "red",
    reason: "no dogfooding signal yet",
    captures_today: 0,
    scheduler_fresh: false,
    artifact_rating_count: 0,
    policy_blocks_filters: 0,
  },
  last_successful_scheduler_run: null,
  connector_health: EMPTY_CONNECTOR_HEALTH,
  insight_feedback: { count: 0, useful_yes: 0, useful_no: 0, useful_not_sure: 0, missed_something_yes: 0 },
};

export const EMPTY_DOCTOR: VNextDoctorPayload = {
  status: "unknown",
  fix_safe_applied: false,
  ci_mode: true,
  blocking_failure_count: 0,
  warning_count: 0,
  checks: [],
  recommended_fixes: [],
  migration_status: {},
  connector_health: EMPTY_CONNECTOR_HEALTH,
};

export const EMPTY_TRACEABILITY: { items: VNextSourceTracePayload[]; count: number; order: string[] } = {
  items: [],
  count: 0,
  order: [],
};

export const FIXTURE_SOURCES: VNextSourceRecord[] = [
  {
    id: "source-fixture-1",
    source_type: "manual_text",
    title: "Launch review note",
    captured_at: "2026-05-10T08:30:00Z",
    domain: "project",
    sensitivity: "private",
    metadata_json: {
      raw_text:
        "Decision: Keep the launch cohort small.\nTodo: Confirm launch checklist owner before product review.",
    },
  },
  {
    id: "source-fixture-2",
    source_type: "manual_text",
    title: "Vendor legal note",
    captured_at: "2026-05-09T16:20:00Z",
    domain: "legal",
    sensitivity: "internal",
    metadata_json: { raw_text: "Waiting on: Priya for vendor legal review ETA." },
  },
];

export const FIXTURE_REVIEW_ITEMS: VNextMemoryRecord[] = [
  {
    id: "memory-fixture-1",
    memory_key: "vnext.capture.decision.launch-owner",
    memory_type: "decision",
    status: "candidate",
    title: "Launch checklist owner should be confirmed before product review.",
    canonical_text: "Launch checklist owner should be confirmed before product review.",
    summary: "Owner is implied but not confirmed.",
    domain: "project",
    sensitivity: "private",
    value: { text: "Launch checklist owner should be confirmed before product review." },
    metadata_json: { source_id: "source-fixture-1", project_id: "project-fixture-1" },
  },
  {
    id: "memory-fixture-2",
    memory_key: "vnext.capture.open_loop.vendor-legal",
    memory_type: "open_loop",
    status: "candidate",
    title: "Vendor legal review is waiting for Priya.",
    canonical_text: "Vendor legal review is waiting for Priya.",
    summary: "Waiting-for signal from weekly synthesis.",
    domain: "legal",
    sensitivity: "internal",
    value: { text: "Vendor legal review is waiting for Priya." },
    metadata_json: { source_id: "source-fixture-2" },
  },
];

export const FIXTURE_PROJECTS: VNextProjectRecord[] = [
  {
    id: "project-fixture-1",
    name: "Product launch",
    slug: "product-launch",
    status: "active",
    current_state: "Launch ownership is unresolved.",
    description: "First preview cohort launch.",
    domain: "project",
    sensitivity: "private",
  },
  {
    id: "project-fixture-2",
    name: "Vendor onboarding",
    slug: "vendor-onboarding",
    status: "active",
    current_state: "Waiting on legal review.",
    description: "Vendor legal and operations readiness.",
    domain: "legal",
    sensitivity: "internal",
  },
];

export const FIXTURE_OPEN_LOOPS: VNextOpenLoopRecord[] = [
  {
    id: "loop-fixture-1",
    title: "Confirm launch checklist owner",
    status: "open",
    due_at: "2026-05-11T17:00:00Z",
    priority: "high",
    project_id: "project-fixture-1",
    source_id: "source-fixture-1",
    domain: "project",
    sensitivity: "private",
  },
  {
    id: "loop-fixture-2",
    title: "Ask Priya for vendor legal review ETA",
    status: "open",
    priority: "normal",
    project_id: "project-fixture-2",
    source_id: "source-fixture-2",
    domain: "legal",
    sensitivity: "internal",
  },
];

export const FIXTURE_ARTIFACTS: VNextArtifactRecord[] = [
  {
    id: "artifact-fixture-1",
    artifact_type: "daily_brief",
    title: "Daily Brief - 2026-05-10",
    content_markdown:
      "# Daily Brief - 2026-05-10\n\n## Suggested Focus\n- Confirm the launch checklist owner.\n- Clear the vendor legal waiting-for item.",
    status: "needs_review",
    domain: "project",
    sensitivity: "private",
    generated_by: "vnext_daily_brief",
    metadata_json: { workflow: "daily_brief", source_ids: ["source-fixture-1"], generation_mode: "deterministic" },
  },
  {
    id: "artifact-fixture-model-daily",
    artifact_type: "daily_brief",
    title: "Daily Brief - model-backed comparison",
    content_markdown:
      "# Daily Brief - model-backed comparison\n\n## Facts\n- Launch owner is unresolved. [source:source-fixture-1]\n\n## Inferences\n- Legal review and ownership are coupled.\n\n## Recommendations\n- Resolve the owner before expanding launch scope.\n\n## Uncertainties\n- Vendor legal timing is still unknown.\n\n## Source References\n- source:source-fixture-1\n\n## Contradictions Considered\n- No explicit contradiction candidates were supplied.\n\n## Open Questions\n- Who owns the launch checklist?",
    status: "needs_review",
    domain: "project",
    sensitivity: "private",
    generated_by: "vnext_daily_brief",
    prompt_hash: "sha256:fixture-daily-prompt",
    model_info_json: {
      provider: "deterministic_local",
      model: "alice-vnext-grounded-synthesizer-v1",
      prompt_hash: "sha256:fixture-daily-prompt",
      input_context_hash: "sha256:fixture-daily-context",
      policy_mode: "local_only_restricted_safe_default",
    },
    metadata_json: {
      workflow: "daily_brief",
      source_refs: ["source:source-fixture-1"],
      generation_mode: "model_backed",
      model_routing: { route_mode: "local_only", policy_mode: "local_only_restricted_safe_default" },
    },
  },
  {
    id: "artifact-fixture-2",
    artifact_type: "weekly_synthesis",
    title: "Weekly Synthesis - 2026-W19",
    content_markdown:
      "# Weekly Synthesis - 2026-W19\n\nLaunch pressure is concentrated around ownership and legal review.",
    status: "needs_review",
    domain: "professional",
    sensitivity: "internal",
    generated_by: "vnext_weekly_synthesis",
    metadata_json: { workflow: "weekly_synthesis", generation_mode: "deterministic" },
  },
  {
    id: "artifact-fixture-connection-deterministic",
    artifact_type: "connection_report",
    title: "Connection Report - deterministic",
    content_markdown: "# Connection Report\n\n## Candidate Connections\n- Launch owner and legal review share release risk.",
    status: "needs_review",
    domain: "project",
    sensitivity: "private",
    generated_by: "vnext_connection_finder",
    metadata_json: { workflow_type: "connection_report", generation_mode: "deterministic", source_refs: ["source:source-fixture-1"] },
  },
  {
    id: "artifact-fixture-connection-model",
    artifact_type: "connection_report",
    title: "Connection Report - model-backed",
    content_markdown:
      "# Connection Report - model-backed\n\n## Facts\n- Launch owner is unresolved. [source:source-fixture-1]\n\n## Inferences\n- The blocker pattern spans legal review and launch ownership.\n\n## Recommendations\n- Accept the candidate edge only after confirming source evidence.\n\n## Uncertainties\n- The legal owner may already be assigned elsewhere.\n\n## Source References\n- source:source-fixture-1\n\n## Contradictions Considered\n- No explicit contradiction candidates were supplied.\n\n## Open Questions\n- Is this a dependency edge or only a shared theme?",
    status: "needs_review",
    domain: "project",
    sensitivity: "private",
    generated_by: "vnext_connection_finder",
    model_info_json: {
      provider: "deterministic_local",
      model: "alice-vnext-grounded-synthesizer-v1",
      prompt_hash: "sha256:fixture-connection-prompt",
      input_context_hash: "sha256:fixture-connection-context",
      policy_mode: "local_only_restricted_safe_default",
    },
    metadata_json: { workflow_type: "connection_report", generation_mode: "model_backed", source_refs: ["source:source-fixture-1"] },
  },
  {
    id: "artifact-fixture-contradiction-deterministic",
    artifact_type: "contradiction_report",
    title: "Contradiction Report - deterministic",
    content_markdown: "# Contradiction Report\n\n## Candidate Contradictions\n- Older ownership memory conflicts with newer unresolved-owner note.",
    status: "needs_review",
    domain: "project",
    sensitivity: "private",
    generated_by: "vnext_contradiction_finder",
    metadata_json: { workflow_type: "contradiction_report", generation_mode: "deterministic", source_refs: ["source:source-fixture-1"] },
  },
  {
    id: "artifact-fixture-contradiction-model",
    artifact_type: "contradiction_report",
    title: "Contradiction Report - model-backed",
    content_markdown:
      "# Contradiction Report - model-backed\n\n## Facts\n- A newer note says ownership is unresolved. [source:source-fixture-1]\n\n## Inferences\n- The active belief may be stale rather than false.\n\n## Recommendations\n- Challenge the belief and request confirmation.\n\n## Uncertainties\n- The source may refer to a different checklist.\n\n## Source References\n- source:source-fixture-1\n\n## Contradictions Considered\n- Older ownership claim versus newer unresolved-owner note.\n\n## Open Questions\n- Which checklist does each source reference?",
    status: "needs_review",
    domain: "project",
    sensitivity: "private",
    generated_by: "vnext_contradiction_finder",
    model_info_json: {
      provider: "deterministic_local",
      model: "alice-vnext-grounded-synthesizer-v1",
      prompt_hash: "sha256:fixture-contradiction-prompt",
      input_context_hash: "sha256:fixture-contradiction-context",
      policy_mode: "local_only_restricted_safe_default",
    },
    metadata_json: { workflow_type: "contradiction_report", generation_mode: "model_backed", source_refs: ["source:source-fixture-1"] },
  },
];

export const FIXTURE_QUALITY_EVALS: VNextArtifactQualityEvalRecord[] = [
  {
    id: "quality-fixture-1",
    artifact_id: "artifact-fixture-model-daily",
    reviewer_id: "demo-reviewer",
    usefulness: 4,
    accuracy: 4,
    source_grounding: 5,
    novel_connections: 3,
    actionability: 4,
    hallucination_risk: 1,
    verbosity: "right_sized",
    comments: "Model-backed brief separates facts from recommendations.",
    created_at: "2026-05-11T09:00:00Z",
  },
];

export const FIXTURE_PEOPLE: VNextPersonRecord[] = [
  {
    id: "person-fixture-1",
    name: "Priya",
    sensitivity: "internal",
    relationship_type: "Vendor legal owner",
    notes: "Referenced by waiting-for loop and weekly synthesis.",
  },
  {
    id: "person-fixture-2",
    name: "Morgan",
    sensitivity: "private",
    relationship_type: "Possible launch checklist owner",
    notes: "Older note conflicts with newer meeting capture.",
  },
];

export const FIXTURE_BELIEFS: VNextBeliefRecord[] = [
  {
    id: "belief-fixture-1",
    memory_id: "memory-fixture-1",
    claim: "Launch readiness depends on explicit ownership.",
    status: "emerging",
    confidence: 0.62,
  },
];

export const FIXTURE_EVENTS: VNextEventRecord[] = [
  {
    id: "event-fixture-1",
    event_type: "source.captured",
    actor_type: "system",
    target_type: "source",
    target_id: "source-fixture-1",
    occurred_at: "2026-05-10T08:30:00Z",
    payload_json: { source_type: "manual_text" },
  },
  {
    id: "event-fixture-2",
    event_type: "memory.candidate_created",
    actor_type: "system",
    target_type: "memory",
    target_id: "memory-fixture-1",
    occurred_at: "2026-05-10T08:31:00Z",
    payload_json: { memory_type: "decision" },
  },
];

export const FIXTURE_AGENT_ACTIVITY: NonNullable<VNextWorkspacePayload["agent_activity"]> = {
  agents: [
    {
      id: "agent-fixture-openclaw",
      agent_id: "openclaw",
      agent_type: "coding_agent",
      permission_profile: "project_scoped_agent",
      project_scope_json: ["Alice"],
      updated_at: "2026-05-10T08:45:00Z",
    },
    {
      id: "agent-fixture-hermes",
      agent_id: "hermes",
      agent_type: "personal_assistant",
      permission_profile: "trusted_local_agent",
      project_scope_json: ["Alice"],
      updated_at: "2026-05-10T08:42:00Z",
    },
  ],
  recent_events: [
    {
      id: "agent-event-fixture-1",
      event_type: "agent.context_pack_requested",
      actor_type: "agent",
      actor_id: "openclaw",
      target_type: "context_pack",
      target_id: "context-pack-fixture",
      occurred_at: "2026-05-10T08:45:00Z",
      payload_json: { query: "Alice project status", selected_count: 3 },
    },
  ],
  policy_blocks: [
    {
      id: "agent-event-fixture-2",
      event_type: "agent.policy_filtered",
      actor_type: "agent",
      actor_id: "openclaw",
      target_type: "context_pack",
      target_id: "context-pack-fixture-filtered",
      occurred_at: "2026-05-10T08:46:00Z",
      payload_json: { reason: "restricted_domain_filtered" },
    },
  ],
  generated_artifacts: FIXTURE_ARTIFACTS,
  pending_review_items: FIXTURE_REVIEW_ITEMS,
  recent_commits: [
    {
      id: "memory-fixture-agentic-commit",
      memory_key: "agentic_memory.semantic.fixture",
      memory_type: "semantic",
      status: "active",
      title: "Launch label preference",
      canonical_text: "Use public alpha wording for the local vNext release.",
      domain: "project",
      sensitivity: "internal",
      updated_at: "2026-05-10T08:48:00Z",
      metadata_json: {
        agentic_memory: {
          write_mode: "commit",
          lifecycle_status: "auto_committed",
          agent_identity: { agent_id: "hermes", permission_profile: "trusted_local_agent" },
        },
      },
    },
  ],
  inline_confirmations: [
    {
      id: "memory-fixture-agentic-confirmation",
      memory_key: "agentic_memory.semantic.confirmation",
      memory_type: "semantic",
      status: "needs_review",
      title: "Sensitive reminder",
      canonical_text: "Confirm before storing sensitive personal preferences.",
      domain: "personal",
      sensitivity: "confidential",
      updated_at: "2026-05-10T08:49:00Z",
      metadata_json: {
        agentic_memory: {
          write_mode: "confirm_inline",
          lifecycle_status: "pending_inline_confirmation",
          confirmation: { confirmation_id: "confirm-fixture", status: "pending" },
        },
      },
    },
  ],
};

export const FIXTURE_POLICY_TELEMETRY: VNextPolicyTelemetrySummary = {
  total_agent_events: 2,
  total_policy_decisions: 2,
  policy_blocks_by_agent: [],
  policy_filters_by_agent: [{ agent_id: "openclaw", count: 1, actions: { "context_pack.request": 1 } }],
  requires_review_by_agent: [{ agent_id: "hermes", count: 1, actions: { "memory.propose": 1 } }],
  restricted_domains_requested: [{ domain: "financial", count: 1 }],
  workflows_triggered_by_agents: [{ workflow_type: "project_update_scan", count: 1, agents: { hermes: 1 } }],
  memory_proposals_by_agent: [{ agent_id: "hermes", count: 1 }],
  artifact_generation_by_agent: [{ agent_id: "hermes", count: 1 }],
};

export const FIXTURE_SCHEDULER: VNextSchedulerStatus = {
  mode: "local_governed",
  disabled_by_default: true,
  enabled_count: 0,
  paused_count: 0,
  last_failure: null,
  recent_failures: [],
  last_due_scan: null,
  next_due_workflow: null,
  currently_running_workflow: null,
  last_success_by_workflow: {},
  daemon: {
    configured: true,
    running: false,
    pid: null,
    mode: "background",
    last_due_count: 0,
  },
  workflows: [
    {
      id: "schedule-daily",
      workflow_type: "daily_brief",
      enabled: false,
      paused: false,
      schedule_json: { kind: "daily", time_of_day: "08:00", days_of_week: ["monday", "tuesday", "wednesday", "thursday", "friday"] },
      timezone: "UTC",
      next_run_at: null,
      last_result: null,
    },
    {
      id: "schedule-weekly",
      workflow_type: "weekly_synthesis",
      enabled: false,
      paused: false,
      schedule_json: { kind: "weekly", day_of_week: "monday", time_of_day: "09:00" },
      timezone: "UTC",
      next_run_at: null,
      last_result: null,
    },
  ],
  recent_runs: [],
};

export const INITIAL_CONNECTORS: ConnectorSetting[] = [
  {
    id: "telegram",
    name: "Telegram raw-update ingestion",
    stage: "On-demand input",
    status: "Caller-supplied updates",
    defaultDomain: "personal",
    defaultSensitivity: "private",
    cursor: "provider_update_id",
    evidence: "Operator-supplied raw Telegram update JSON",
    failureMode: "Rejected updates do not advance the cursor.",
  },
  {
    id: "browser_clipper",
    name: "Browser clipper",
    stage: "On-demand capture",
    status: "Local endpoint",
    defaultDomain: "professional",
    defaultSensitivity: "private",
    cursor: "captured_at or external id",
    evidence: "URL, selection, page text, and optional HTML",
    failureMode: "Bad clips stay out of memory.",
  },
  {
    id: "local_folder",
    name: "Local folder watcher",
    stage: "On-demand capture",
    status: "Caller-selected paths",
    defaultDomain: "project",
    defaultSensitivity: "private",
    cursor: "file mtime and path",
    evidence: "Markdown/text file content plus path metadata",
    failureMode: "Generated/export folders are ignored by default.",
  },
  {
    id: "agent_output",
    name: "Agent output ingestion",
    stage: "On-demand capture",
    status: "API/MCP/CLI",
    defaultDomain: "project",
    defaultSensitivity: "private",
    cursor: "agent run id or external id",
    evidence: "Hermes/OpenClaw summaries, decisions, plans, and review findings",
    failureMode: "Agent proposals remain review-only.",
  },
  {
    id: "pdf_document",
    name: "PDF text-payload ingestion",
    stage: "External extraction input",
    status: "Caller-supplied text",
    defaultDomain: "unknown",
    defaultSensitivity: "private",
    cursor: "modified time or external id",
    evidence: "Text extracted outside Alice plus PDF metadata",
    failureMode: "Invalid text payloads leave existing sources unchanged.",
  },
  {
    id: "docx_document",
    name: "DOCX text-payload ingestion",
    stage: "External extraction input",
    status: "Caller-supplied text",
    defaultDomain: "unknown",
    defaultSensitivity: "private",
    cursor: "modified time or external id",
    evidence: "Text extracted outside Alice plus DOCX metadata",
    failureMode: "Invalid text payloads leave existing sources unchanged.",
  },
  {
    id: "csv_table",
    name: "CSV row-payload ingestion",
    stage: "External extraction input",
    status: "Caller-supplied rows",
    defaultDomain: "professional",
    defaultSensitivity: "private",
    cursor: "modified time or external id",
    evidence: "Rows normalized outside Alice plus CSV metadata",
    failureMode: "Malformed row payloads do not advance the cursor.",
  },
  {
    id: "screenshot_ocr",
    name: "Screenshot text-payload ingestion",
    stage: "External extraction input",
    status: "Caller-supplied text",
    defaultDomain: "unknown",
    defaultSensitivity: "private",
    cursor: "captured_at or external id",
    evidence: "Text extracted outside Alice plus screenshot metadata",
    failureMode: "Invalid text payloads leave existing sources unchanged.",
  },
  {
    id: "voice_transcription",
    name: "Audio transcript-payload ingestion",
    stage: "External extraction input",
    status: "Caller-supplied transcript",
    defaultDomain: "personal",
    defaultSensitivity: "private",
    cursor: "recorded_at or external id",
    evidence: "Transcript text extracted outside Alice plus recording metadata",
    failureMode: "Invalid transcript payloads leave existing sources unchanged.",
  },
];

export const FIXTURE_CONNECTOR_HEALTH = {
  items: INITIAL_CONNECTORS.filter((connector) => ["telegram", "local_folder", "browser_clipper", "agent_output"].includes(connector.id)).map(
    (connector, index) => ({
      connector_name: connector.id,
      display_name: connector.name,
      enabled: index < 3,
      configured: true,
      default_domain: connector.defaultDomain,
      default_sensitivity: connector.defaultSensitivity,
      last_sync_at: `2026-05-11T0${index + 8}:00:00Z`,
      last_success_at: `2026-05-11T0${index + 8}:00:00Z`,
      last_failure_at: null,
      last_error: null,
      last_captured_item: { external_id: `${connector.id}-fixture`, source_id: `source-fixture-${index + 1}` },
      items_seen: 4 + index,
      items_captured: 3 + index,
      items_deduped: 1,
      items_failed: 0,
      cursor_state: `${index + 1}`,
      average_processing_time: 12.4 + index,
      ...(connector.id === "local_folder"
        ? { sync_mode: "watch", poll_interval_seconds: 30 }
        : { sync_mode: "on_demand" }),
    }),
  ),
  count: 4,
  order: ["telegram", "local_folder", "browser_clipper", "agent_output"],
};

export const FIXTURE_DOGFOODING: VNextDogfoodingDashboard = {
  captures_by_connector: [
    { connector_name: "telegram", count: 3 },
    { connector_name: "local_folder", count: 4 },
    { connector_name: "browser_clipper", count: 2 },
    { connector_name: "agent_output", count: 1 },
  ],
  captures_today: 10,
  captures_this_week: 24,
  capture_trend_by_day: [
    { date: "2026-05-05", count: 2 },
    { date: "2026-05-06", count: 3 },
    { date: "2026-05-07", count: 4 },
    { date: "2026-05-08", count: 3 },
    { date: "2026-05-09", count: 2 },
    { date: "2026-05-10", count: 5 },
    { date: "2026-05-11", count: 10 },
  ],
  capture_trend_by_week: [{ period: "last_7_days", count: 24 }],
  candidate_memories_created: 8,
  memory_status_counts: { candidate: 8, accepted: 3, rejected: 1 },
  candidate_memory_review_rate: 0.33,
  generated_artifacts_created: FIXTURE_ARTIFACTS.length,
  artifact_status_counts: { needs_review: FIXTURE_ARTIFACTS.length },
  artifact_quality_average: 4.3,
  artifact_quality_rating_count: FIXTURE_QUALITY_EVALS.length,
  artifact_rating_trend: [{ date: "2026-05-11", count: FIXTURE_QUALITY_EVALS.length }],
  daily_brief_review_status: "needs_review",
  weekly_synthesis_review_status: "needs_review",
  connections_surfaced: 2,
  contradictions_surfaced: 1,
  open_loop_status_counts: { open: 2, resolved: 1 },
  open_loops_created: 3,
  open_loops_closed: 1,
  agent_context_packs_requested: 5,
  agent_memory_proposals: 2,
  policy_blocks_filters: 1,
  connector_failures: 0,
  top_failure_causes: [],
  scheduler_freshness: { recent_success: true, recent_failure_count: 0 },
  agent_activity_summary: { outputs_ingested: 1, context_packs_requested: 5, memory_proposals: 2 },
  policy_block_filter_summary: { count: 1, event_types: { "agent.policy_filtered": 1 } },
  dogfood_readiness: {
    status: "green",
    reason: "fixture capture, scheduler, review, and policy loops have healthy signal",
    captures_today: 10,
    scheduler_fresh: true,
    artifact_rating_count: FIXTURE_QUALITY_EVALS.length,
    policy_blocks_filters: 1,
  },
  last_successful_scheduler_run: null,
  connector_health: FIXTURE_CONNECTOR_HEALTH,
  insight_feedback: { count: 3, useful_yes: 2, useful_no: 0, useful_not_sure: 1, missed_something_yes: 1 },
};

export const FIXTURE_DOCTOR: VNextDoctorPayload = {
  status: "pass",
  fix_safe_applied: false,
  ci_mode: true,
  blocking_failure_count: 0,
  warning_count: 0,
  checks: [
    {
      name: "migrations",
      status: "pass",
      severity: "info",
      message: "Required vNext dogfood hardening tables are present.",
      details: { status: "ok" },
    },
    {
      name: "connector_settings",
      status: "pass",
      severity: "info",
      message: "Core connector settings rows exist.",
      details: { missing: [] },
    },
    {
      name: "scheduler_daemon",
      status: "pass",
      severity: "info",
      message: "Scheduler daemon status is available.",
      details: { running: false, configured: true },
    },
  ],
  recommended_fixes: [],
  migration_status: { status: "ok", missing_tables: [] },
  connector_health: FIXTURE_CONNECTOR_HEALTH,
};

export const FIXTURE_TRACEABILITY = {
  items: FIXTURE_SOURCES.map((source) => {
    const sourceId = source.id;
    const candidateMemories = FIXTURE_REVIEW_ITEMS.filter(
      (memory) => textValue(asRecord(memory.metadata_json).source_id) === sourceId,
    );
    const artifacts = FIXTURE_ARTIFACTS.filter((artifact) => {
      const metadata = asRecord(artifact.metadata_json);
      const refs = Array.isArray(metadata.source_refs) ? metadata.source_refs : metadata.source_ids;
      return Array.isArray(refs) && refs.map(String).some((ref) => ref === sourceId || ref === `source:${sourceId}`);
    });
    const openLoops = FIXTURE_OPEN_LOOPS.filter((loop) => loop.source_id === sourceId);
    const events = FIXTURE_EVENTS.filter(
      (event) =>
        event.target_id === sourceId ||
        candidateMemories.some((memory) => memory.id === event.target_id) ||
        artifacts.some((artifact) => artifact.id === event.target_id) ||
        openLoops.some((loop) => loop.id === event.target_id),
    );
    return {
      trace_id: `source:${sourceId}`,
      trace_kind: "capture_to_brief",
      source,
      chunks: [
        {
          id: `chunk-${sourceId}`,
          source_id: sourceId,
          chunk_index: 0,
          text: sourceText(source),
          token_count: sourceText(source).split(/\s+/).filter(Boolean).length,
        },
      ],
      candidate_memories: candidateMemories,
      artifacts,
      open_loops: openLoops,
      events,
      summary: {
        source_id: sourceId,
        chunk_count: 1,
        candidate_memory_count: candidateMemories.length,
        artifact_count: artifacts.length,
        open_loop_count: openLoops.length,
        event_count: events.length,
      },
    };
  }),
  count: FIXTURE_SOURCES.length,
  order: FIXTURE_SOURCES.map((source) => `source:${source.id}`),
};

export function fixtureWorkspace(): WorkspaceView {
  const projectDashboards: VNextProjectDashboard[] = FIXTURE_PROJECTS.map((project) => {
    const openLoops = FIXTURE_OPEN_LOOPS.filter((loop) => loop.project_id === project.id);
    const memories = FIXTURE_REVIEW_ITEMS.filter(
      (memory) => asRecord(memory.metadata_json).project_id === project.id,
    );
    const artifacts = FIXTURE_ARTIFACTS.filter((artifact) => artifact.domain === project.domain);
    return {
      project,
      state: project.current_state ?? null,
      memories,
      open_loops: openLoops,
      artifacts,
      counts: {
        memories: memories.length,
        open_loops: openLoops.length,
        artifacts: artifacts.length,
      },
    };
  });
  const view = {
    sources: FIXTURE_SOURCES,
    reviewItems: FIXTURE_REVIEW_ITEMS,
    artifacts: FIXTURE_ARTIFACTS,
    projects: FIXTURE_PROJECTS,
    projectDashboards,
    openLoops: FIXTURE_OPEN_LOOPS,
    people: FIXTURE_PEOPLE,
    beliefs: FIXTURE_BELIEFS,
    tasks: [],
    recentEvents: FIXTURE_EVENTS,
    qualityEvals: FIXTURE_QUALITY_EVALS,
    connectorHealth: FIXTURE_CONNECTOR_HEALTH,
    dogfooding: FIXTURE_DOGFOODING,
    doctor: FIXTURE_DOCTOR,
    traceability: FIXTURE_TRACEABILITY,
    agentActivity: FIXTURE_AGENT_ACTIVITY,
    policyTelemetry: FIXTURE_POLICY_TELEMETRY,
    scheduler: FIXTURE_SCHEDULER,
    brainCharter: {
      id: "brain-charter-fixture",
      content_markdown: "# ALICE.md\n\nKeep generated artifacts reviewable before promotion.",
      sensitivity: "private",
    },
  };
  return { ...view, summary: createSummary(view) };
}

export function emptyWorkspace(): WorkspaceView {
  const view = {
    sources: [],
    reviewItems: [],
    artifacts: [],
    projects: [],
    projectDashboards: [],
    openLoops: [],
    people: [],
    beliefs: [],
    tasks: [],
    recentEvents: [],
    qualityEvals: [],
    connectorHealth: EMPTY_CONNECTOR_HEALTH,
    dogfooding: EMPTY_DOGFOODING,
    doctor: EMPTY_DOCTOR,
    traceability: EMPTY_TRACEABILITY,
    agentActivity: EMPTY_AGENT_ACTIVITY,
    policyTelemetry: EMPTY_POLICY_TELEMETRY,
    scheduler: EMPTY_SCHEDULER,
    brainCharter: null,
  };
  return { ...view, summary: createSummary(view) };
}

export function normalizeAgentActivity(activity: VNextWorkspacePayload["agent_activity"]): NonNullable<VNextWorkspacePayload["agent_activity"]> {
  if (!activity) {
    return EMPTY_AGENT_ACTIVITY;
  }
  return {
    agents: Array.isArray(activity.agents) ? activity.agents : [],
    recent_events: Array.isArray(activity.recent_events) ? activity.recent_events : [],
    policy_blocks: Array.isArray(activity.policy_blocks) ? activity.policy_blocks : [],
    generated_artifacts: Array.isArray(activity.generated_artifacts) ? activity.generated_artifacts : [],
    pending_review_items: Array.isArray(activity.pending_review_items) ? activity.pending_review_items : [],
    recent_commits: Array.isArray(activity.recent_commits) ? activity.recent_commits : [],
    inline_confirmations: Array.isArray(activity.inline_confirmations) ? activity.inline_confirmations : [],
  };
}

export function workspaceFromPayload(payload: VNextWorkspacePayload): WorkspaceView {
  return {
    summary: payload.summary,
    sources: payload.sources,
    reviewItems: payload.review_memories,
    artifacts: payload.artifacts,
    projects: payload.projects,
    projectDashboards: payload.project_dashboards,
    openLoops: payload.open_loops,
    people: payload.people,
    beliefs: payload.beliefs,
    tasks: payload.tasks,
    recentEvents: payload.recent_events,
    qualityEvals: payload.quality_evals ?? [],
    connectorHealth: payload.connector_health ?? EMPTY_CONNECTOR_HEALTH,
    dogfooding: payload.dogfooding ?? EMPTY_DOGFOODING,
    doctor: payload.doctor ?? EMPTY_DOCTOR,
    traceability: payload.traceability ?? EMPTY_TRACEABILITY,
    agentActivity: normalizeAgentActivity(payload.agent_activity),
    policyTelemetry: payload.policy_telemetry ?? EMPTY_POLICY_TELEMETRY,
    scheduler: payload.scheduler ?? EMPTY_SCHEDULER,
    brainCharter: payload.brain_charter,
  };
}

export function answerFromContextPack(question: string, pack: VNextContextPack): AskAnswer {
  const memories = pack.relevant_memories ?? [];
  const sources = pack.sources ?? [];
  const evidence = pack.supporting_evidence ?? [];
  const interpretation = asRecord(pack.query_interpretation);
  const filters = asRecord(asRecord(pack.trace).filters);
  const summary =
    memories.length > 0
      ? `Alice found ${memories.length} relevant memory item${memories.length === 1 ? "" : "s"} for "${question}". ${memoryText(memories[0])}`
      : sources.length > 0
        ? `Alice found source evidence for "${question}", but no reviewed memory was selected yet.`
        : `Alice could not find matching reviewed memory or source evidence for "${question}".`;
  const sourceIds = [
    ...sources.map((source) => `source:${source.id}`),
    ...evidence.map((item) => {
      const sourceId = item.source_id;
      return typeof sourceId === "string" ? `source:${sourceId}` : "";
    }),
  ].filter(Boolean);

  return {
    question,
    summary,
    memoriesUsed: memories.map(memoryText),
    contradictions:
      pack.contradicting_evidence.length > 0
        ? pack.contradicting_evidence.map((item) => JSON.stringify(item))
        : ["No contradicting evidence selected by this context pack."],
    why: [
      `Query type: ${textValue(interpretation.query_type) || "strategic_synthesis"}.`,
      `Trace: ${textValue(pack.trace_id)} selected evidence from ${String(asRecord(pack.trace).selected_count ?? 0)} candidates.`,
      `Sensitivity allowed: ${Array.isArray(filters.sensitivity_allowed) ? filters.sensitivity_allowed.join(", ") : "default"}.`,
      ...(pack.warnings.length ? pack.warnings.map((warning) => `Warning: ${warning}.`) : []),
    ],
    sources: sourceIds.length ? Array.from(new Set(sourceIds)) : ["No source evidence selected"],
    domain: asDomain(Array.isArray(filters.domains) ? filters.domains[0] : "unknown"),
    sensitivity: "private",
  };
}

export function getVNextWorkspaceFixtureContract() {
  const fixture = fixtureWorkspace();
  return {
    domains: [
      ...fixture.reviewItems.map((item) => asDomain(item.domain)),
      ...fixture.openLoops.map((loop) => asDomain(loop.domain)),
      ...fixture.artifacts.map((artifact) => asDomain(artifact.domain)),
      ...fixture.projects.map((project) => asDomain(project.domain)),
      ...INITIAL_CONNECTORS.map((connector) => connector.defaultDomain),
    ],
    sensitivities: [
      ...fixture.reviewItems.map((item) => asSensitivity(item.sensitivity)),
      ...fixture.openLoops.map((loop) => asSensitivity(loop.sensitivity)),
      ...fixture.artifacts.map((artifact) => asSensitivity(artifact.sensitivity)),
      ...fixture.projects.map((project) => asSensitivity(project.sensitivity)),
      ...fixture.people.map((person) => asSensitivity(person.sensitivity)),
      ...INITIAL_CONNECTORS.map((connector) => connector.defaultSensitivity),
    ],
    connectorIds: INITIAL_CONNECTORS.map((connector) => connector.id),
  };
}

export function pushBoundedLog(message: string, previous: string[]) {
  return [message, ...previous].slice(0, 6);
}

export function latestArtifact(artifacts: VNextArtifactRecord[], artifactType: string) {
  return artifacts.find((artifact) => artifact.artifact_type === artifactType) ?? null;
}

export function artifactGenerationMode(artifact: VNextArtifactRecord) {
  const metadata = asRecord(artifact.metadata_json);
  return textValue(metadata.generation_mode) || "deterministic";
}

export function artifactModelLabel(artifact: VNextArtifactRecord) {
  const modelInfo = asRecord(artifact.model_info_json);
  const provider = textValue(modelInfo.provider) || textValue(asRecord(artifact.metadata_json).model_provider);
  const model = textValue(modelInfo.model) || textValue(asRecord(artifact.metadata_json).model);
  return provider || model ? `${provider || "provider"} / ${model || "model"}` : "No model metadata";
}

export function latestArtifactByMode(artifacts: VNextArtifactRecord[], artifactType: string, generationMode: string) {
  return (
    artifacts.find(
      (artifact) => artifact.artifact_type === artifactType && artifactGenerationMode(artifact) === generationMode,
    ) ?? null
  );
}

export function connectorHealth(workspace: WorkspaceView, connectorId: string) {
  return workspace.connectorHealth.items.find((item) => item.connector_name === connectorId) ?? null;
}

export const COMPARISON_ARTIFACT_TYPES = [
  { artifactType: "daily_brief", label: "Daily Brief" },
  { artifactType: "connection_report", label: "Connection Report" },
  { artifactType: "contradiction_report", label: "Contradiction Report" },
];

export const BROWSER_CLIPPER_BOOKMARKLET =
  'javascript:(async()=>{try{const endpoint=prompt("Alice API endpoint","http://127.0.0.1:8000/v0/vnext/connectors/browser-clipper/capture");if(!endpoint)return;const user_id=prompt("Alice user id","00000000-0000-0000-0000-000000000001");if(!user_id)return;const capture_token=prompt("Optional Alice clipper token","");const user_note=prompt("Optional note","");const s=window.getSelection().toString();const body={user_id,url:location.href,title:document.title,selected_text:s||null,page_text:s?null:document.body.innerText.slice(0,20000),user_note:user_note||null,domain:"professional",sensitivity:"private"};if(capture_token)body.capture_token=capture_token;const r=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});alert(r.ok?"Alice clip saved":"Alice clip failed: "+r.status)}catch(e){alert("Alice clip failed")}})();';

export function scheduleValue(workflow: VNextSchedulerStatus["workflows"][number], key: string, fallback: string) {
  const schedule = asRecord(workflow.schedule_json);
  const value = schedule[key];
  return typeof value === "string" ? value : fallback;
}

export function scheduleSummary(workflow: VNextSchedulerStatus["workflows"][number]) {
  const schedule = asRecord(workflow.schedule_json);
  const kind = textValue(schedule.kind) || "manual";
  if (kind === "daily") {
    const days = Array.isArray(schedule.days_of_week) ? schedule.days_of_week.join(", ") : "configured days";
    return `Daily at ${scheduleValue(workflow, "time_of_day", "08:00")} ${workflow.timezone} on ${days}`;
  }
  if (kind === "weekly") {
    return `Weekly on ${scheduleValue(workflow, "day_of_week", "monday")} at ${scheduleValue(workflow, "time_of_day", "09:00")} ${workflow.timezone}`;
  }
  return "Manual only";
}

export function agentDisplayName(agentId: string) {
  if (agentId.toLowerCase() === "openclaw") {
    return "OpenClaw";
  }
  if (agentId.toLowerCase() === "hermes") {
    return "Hermes";
  }
  return agentId;
}
