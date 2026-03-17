import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";
import { TaskList, type TaskItem } from "../../components/task-list";
import { TaskStepList, type TaskStepItem } from "../../components/task-step-list";

const taskFixtures: TaskItem[] = [
  {
    id: "task-201",
    thread_id: "thread-magnesium",
    tool_id: "tool-purchase",
    status: "pending_approval",
    request: {
      thread_id: "thread-magnesium",
      tool_id: "tool-purchase",
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Thorne",
        item: "Magnesium Bisglycinate",
      },
    },
    tool: {
      id: "tool-purchase",
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
    },
    latest_approval_id: "approval-101",
    latest_execution_id: null,
    created_at: "2026-03-17T06:49:00Z",
    updated_at: "2026-03-17T06:50:00Z",
  },
  {
    id: "task-182",
    thread_id: "thread-vitamin-d",
    tool_id: "tool-purchase",
    status: "approved",
    request: {
      thread_id: "thread-vitamin-d",
      tool_id: "tool-purchase",
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: {
        merchant: "Fullscript",
        item: "Vitamin D3 + K2",
      },
    },
    tool: {
      id: "tool-purchase",
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
      created_at: "2026-03-14T09:15:00Z",
    },
    latest_approval_id: "approval-100",
    latest_execution_id: null,
    created_at: "2026-03-16T14:00:00Z",
    updated_at: "2026-03-16T14:22:00Z",
  },
];

const stepFixtures: Record<string, TaskStepItem[]> = {
  "task-201": [
    {
      id: "step-20",
      task_id: "task-201",
      sequence_no: 1,
      kind: "governed_request",
      status: "created",
      request: {
        thread_id: "thread-magnesium",
        tool_id: "tool-purchase",
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
        approval_id: "approval-101",
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
        trace_id: "trace-step-20",
        trace_kind: "approval_request",
      },
      created_at: "2026-03-17T06:49:00Z",
      updated_at: "2026-03-17T06:50:00Z",
    },
  ],
  "task-182": [
    {
      id: "step-14",
      task_id: "task-182",
      sequence_no: 1,
      kind: "governed_request",
      status: "approved",
      request: {
        thread_id: "thread-vitamin-d",
        tool_id: "tool-purchase",
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
        approval_id: "approval-100",
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
        trace_id: "trace-step-14",
        trace_kind: "approval_resolution",
      },
      created_at: "2026-03-16T14:00:00Z",
      updated_at: "2026-03-16T14:22:00Z",
    },
  ],
};

function getApiConfig() {
  return {
    apiBaseUrl:
      process.env.NEXT_PUBLIC_ALICEBOT_API_BASE_URL ?? process.env.ALICEBOT_API_BASE_URL ?? "",
    userId: process.env.NEXT_PUBLIC_ALICEBOT_USER_ID ?? process.env.ALICEBOT_USER_ID ?? "",
  };
}

async function loadTasks(): Promise<{ items: TaskItem[]; source: "live" | "fixture" }> {
  const { apiBaseUrl, userId } = getApiConfig();
  if (!apiBaseUrl || !userId) {
    return { items: taskFixtures, source: "fixture" };
  }

  try {
    const response = await fetch(
      `${apiBaseUrl.replace(/\/$/, "")}/v0/tasks?user_id=${encodeURIComponent(userId)}`,
      { cache: "no-store" },
    );

    if (!response.ok) {
      throw new Error("task list request failed");
    }

    const payload = (await response.json()) as { items?: TaskItem[] };
    return {
      items: payload.items ?? taskFixtures,
      source: "live",
    };
  } catch {
    return { items: taskFixtures, source: "fixture" };
  }
}

async function loadTaskSteps(
  taskId: string,
  source: "live" | "fixture",
): Promise<{ items: TaskStepItem[]; source: "live" | "fixture" }> {
  if (source === "fixture") {
    return { items: stepFixtures[taskId] ?? [], source: "fixture" };
  }

  const { apiBaseUrl, userId } = getApiConfig();
  try {
    const response = await fetch(
      `${apiBaseUrl.replace(/\/$/, "")}/v0/tasks/${taskId}/steps?user_id=${encodeURIComponent(userId)}`,
      { cache: "no-store" },
    );

    if (!response.ok) {
      throw new Error("task step request failed");
    }

    const payload = (await response.json()) as { items?: TaskStepItem[] };
    return {
      items: payload.items ?? stepFixtures[taskId] ?? [],
      source: "live",
    };
  } catch {
    return { items: stepFixtures[taskId] ?? [], source: "fixture" };
  }
}

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function TasksPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const requestedTaskId = typeof params.task === "string" ? params.task : undefined;
  const { items, source } = await loadTasks();
  const selectedTask = items.find((item) => item.id === requestedTaskId) ?? items[0] ?? null;
  const { items: steps, source: stepSource } = selectedTask
    ? await loadTaskSteps(selectedTask.id, source)
    : { items: [], source };

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Tasks"
        title="Task lifecycle inspection"
        description="Tasks and task steps stay legible in a split review layout so state, provenance, and next action remain visible without overflow or guesswork."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{source === "live" ? "Live API" : "Fixture-backed"}</span>
            <span className="subtle-chip">{items.length} tasks</span>
          </div>
        }
      />

      <div className="dashboard-grid dashboard-grid--detail">
        <TaskList tasks={items} selectedId={selectedTask?.id} />

        <div className="stack">
          <SectionCard
            eyebrow="Selected task"
            title={selectedTask ? selectedTask.tool.name : "No task selected"}
            description={
              selectedTask
                ? "Latest task state, governing request context, and related identifiers stay grouped in one bounded summary."
                : "Choose a task to inspect its current state and ordered steps."
            }
          >
            {selectedTask ? (
              <div className="detail-stack">
                <div className="detail-summary">
                  <StatusBadge status={selectedTask.status} />
                  <span className="detail-summary__label">
                    {selectedTask.request.action} / {selectedTask.request.scope}
                  </span>
                </div>
                <dl className="key-value-grid">
                  <div>
                    <dt>Thread</dt>
                    <dd className="mono">{selectedTask.thread_id}</dd>
                  </div>
                  <div>
                    <dt>Latest approval</dt>
                    <dd className="mono">{selectedTask.latest_approval_id ?? "Not linked"}</dd>
                  </div>
                  <div>
                    <dt>Latest execution</dt>
                    <dd className="mono">{selectedTask.latest_execution_id ?? "Not executed"}</dd>
                  </div>
                  <div>
                    <dt>Data source</dt>
                    <dd>{stepSource === "live" ? "Live task-step API" : "Local fixture steps"}</dd>
                  </div>
                </dl>
              </div>
            ) : (
              <p className="muted-copy">
                No task records are available in the current mode.
              </p>
            )}
          </SectionCard>

          <TaskStepList steps={steps} />
        </div>
      </div>
    </div>
  );
}
