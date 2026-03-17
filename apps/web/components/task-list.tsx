import Link from "next/link";

import type { TaskItem } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TaskList({
  tasks,
  selectedId,
}: {
  tasks: TaskItem[];
  selectedId?: string;
}) {
  if (tasks.length === 0) {
    return (
      <SectionCard
        eyebrow="Tasks"
        title="No task records"
        description="Tasks appear here when governed work is persisted in the backend."
      >
        <EmptyState
          title="Task list is empty"
          description="No task lifecycle records are available in the current mode."
          actionHref="/chat"
          actionLabel="Open requests"
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Task list"
      title="Current governed work"
      description="Task rows keep lifecycle state and operator context visible without crowding the primary detail column."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <p>{tasks.length} tasks in scope</p>
        </div>
        <div className="list-rows">
          {tasks.map((task) => (
            <Link
              key={task.id}
              href={`/tasks?task=${task.id}`}
              className={`list-row${task.id === selectedId ? " is-selected" : ""}`}
            >
              <div className="list-row__topline">
                <div className="detail-stack">
                  <span className="list-row__eyebrow">{formatDate(task.updated_at)}</span>
                  <h3 className="list-row__title">{task.tool.name}</h3>
                </div>
                <StatusBadge status={task.status} />
              </div>
              <p>
                {task.request.action} / {task.request.scope}
              </p>
              <div className="list-row__meta">
                <span className="meta-pill">Task {task.id}</span>
                {task.latest_approval_id ? <span className="meta-pill">Approval linked</span> : null}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
