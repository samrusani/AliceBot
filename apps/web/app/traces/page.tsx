import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { TraceList, type TraceItem } from "../../components/trace-list";

const traceFixtures: TraceItem[] = [
  {
    id: "trace-ctx-401",
    kind: "context_compile",
    status: "completed",
    title: "Context compile for magnesium reorder guidance",
    summary: "Compiled prior task state, admitted memories, and recent thread continuity before assistant response assembly.",
    eventCount: 9,
    createdAt: "2026-03-17T08:45:00Z",
    source: "Context compiler",
    scope: "thread-magnesium",
    related: {
      threadId: "thread-magnesium",
      taskId: "task-201",
    },
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
      },
      {
        id: "event-2",
        kind: "memory.retrieve",
        title: "Memory evidence attached",
        detail: "Preference and purchase-history memories were ranked into the response context pack.",
      },
      {
        id: "event-3",
        kind: "task.retrieve",
        title: "Task lifecycle linked",
        detail: "Open task and step state were included so the answer could acknowledge the approval dependency.",
      },
    ],
  },
  {
    id: "trace-approval-101",
    kind: "approval_request",
    status: "requires_review",
    title: "Approval request for supplement purchase",
    summary: "Routing required user approval before the merchant proxy could execute the purchase request.",
    eventCount: 6,
    createdAt: "2026-03-17T06:50:00Z",
    source: "Approval workflow",
    scope: "supplements",
    related: {
      threadId: "thread-magnesium",
      taskId: "task-201",
      approvalId: "approval-101",
    },
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
      },
      {
        id: "event-5",
        kind: "approval.state",
        title: "Approval opened",
        detail: "Approval record persisted with pending resolution state and task-step linkage.",
      },
      {
        id: "event-6",
        kind: "task.lifecycle",
        title: "Task updated",
        detail: "Task lifecycle moved into a pending approval state while retaining request provenance.",
      },
    ],
  },
  {
    id: "trace-exec-311",
    kind: "proxy_execution",
    status: "completed",
    title: "Governed execution for vitamin reorder",
    summary: "Approved supplement purchase request executed through the proxy handler with task and trace linkage preserved.",
    eventCount: 7,
    createdAt: "2026-03-16T14:24:00Z",
    source: "Proxy execution",
    scope: "supplements",
    related: {
      threadId: "thread-vitamin-d",
      taskId: "task-182",
      approvalId: "approval-100",
      executionId: "execution-311",
    },
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
      },
      {
        id: "event-8",
        kind: "budget.check",
        title: "Budget check passed",
        detail: "Execution budget constraints did not block the governed action.",
      },
      {
        id: "event-9",
        kind: "execution.result",
        title: "Handler completed",
        detail: "Proxy output was recorded for the approved supplement reorder with a linked execution trace and task-step status update.",
      },
    ],
  },
];

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function TracesPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const selectedId = typeof params.trace === "string" ? params.trace : undefined;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Explainability"
        title="Trace and explain-why review"
        description="Trace review keeps evidence readable and bounded. Context compilation and governed actions share one visual language instead of splintering into debug-only panels."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Fixture-backed detail view</span>
            <span className="subtle-chip">Existing backend concepts only</span>
          </div>
        }
      />

      <TraceList traces={traceFixtures} selectedId={selectedId} />

      <SectionCard
        eyebrow="Review guidance"
        title="What operators should verify"
        description="The trace view is designed for explanation before action."
      >
        <ul className="bullet-list">
          <li>Which evidence types contributed to the outcome and whether they were appropriate.</li>
          <li>How the lifecycle moved from request to approval or execution without losing provenance.</li>
          <li>Whether the current trace surface needs deeper live-event wiring in a future sprint.</li>
        </ul>
      </SectionCard>
    </div>
  );
}
