import type { ApiSource, TaskItem, TaskRunItem } from "../lib/api";
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

function checkpointSummary(checkpoint: Record<string, unknown>) {
  const cursor = typeof checkpoint.cursor === "number" ? checkpoint.cursor : 0;
  const targetSteps = typeof checkpoint.target_steps === "number" ? checkpoint.target_steps : 0;
  const waitForSignal = checkpoint.wait_for_signal === true;

  return {
    cursor,
    targetSteps,
    waitForSignal,
  };
}

export function TaskRunList({
  task,
  runs,
  source,
  unavailableMessage,
}: {
  task: TaskItem | null;
  runs: TaskRunItem[];
  source: ApiSource | "unavailable";
  unavailableMessage?: string | null;
}) {
  if (!task) {
    return (
      <SectionCard
        eyebrow="Task runs"
        title="No task selected"
        description="Select a task to review durable run checkpoints and counter state."
      >
        <EmptyState
          title="Run review is idle"
          description="Task-run records are shown when a task is selected."
        />
      </SectionCard>
    );
  }

  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Task runs"
        title="Run review unavailable"
        description="Task-run lifecycle detail could not be loaded from the configured backend."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="Unavailable" />
          <p className="muted-copy">
            {unavailableMessage ?? "Task-run records were not available from the current backend response."}
          </p>
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Task runs"
      title="Durable run review"
      description="Run checkpoints, tick counters, and explicit stop reasons stay visible for deterministic replay and continuation."
      className="task-step-list"
    >
      <div className="cluster">
        <span className="meta-pill">{runs.length} runs</span>
        <span className="meta-pill">{source === "live" ? "Live run state" : "Fixture run state"}</span>
      </div>

      {runs.length === 0 ? (
        <EmptyState
          title="No task runs available"
          description="No durable task-run records are available for the selected task in the current source mode."
        />
      ) : (
        <div className="timeline-list">
          {runs.map((run) => {
            const checkpoint = checkpointSummary(run.checkpoint);
            return (
              <article key={run.id} className="timeline-item">
                <div className="timeline-item__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{formatDate(run.updated_at)}</span>
                    <h3 className="list-row__title">Run {run.id}</h3>
                  </div>
                  <StatusBadge status={run.status} />
                </div>
                <div className="timeline-item__meta">
                  <span className="meta-pill">Tick {run.tick_count} / {run.max_ticks}</span>
                  <span className="meta-pill">Steps {run.step_count}</span>
                  {run.stop_reason ? <span className="meta-pill">Stop: {run.stop_reason}</span> : null}
                </div>
                <div className="key-value-grid">
                  <div>
                    <dt>Checkpoint cursor</dt>
                    <dd>
                      {checkpoint.cursor} / {checkpoint.targetSteps}
                    </dd>
                  </div>
                  <div>
                    <dt>Wait flag</dt>
                    <dd>{checkpoint.waitForSignal ? "true" : "false"}</dd>
                  </div>
                  <div>
                    <dt>Task</dt>
                    <dd className="mono">{run.task_id}</dd>
                  </div>
                  <div>
                    <dt>Source</dt>
                    <dd>{source === "live" ? "Live backend" : "Fixture fallback"}</dd>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}
