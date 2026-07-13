import { SectionCard } from "./section-card";
import { SURFACES, type WorkspaceView } from "./vnext-workspace-model";

export function VNextSurfaceNavigation() {
  return (
    <nav className="vnext-surface-nav" aria-label="Alice vNext surfaces">
      {SURFACES.map((surface) => (
        <a
          key={surface}
          className="vnext-surface-nav__item"
          href={`#vnext-${surface.toLowerCase().replace(/\s+/g, "-")}`}
        >
          {surface}
        </a>
      ))}
    </nav>
  );
}

export function VNextHomeMetrics({ workspace }: { workspace: WorkspaceView }) {
  const metrics = [
    {
      label: "Sources",
      value: workspace.summary.source_count,
      detail: "Captured notes and imported evidence in the vNext inbox.",
    },
    {
      label: "Review items",
      value: workspace.summary.review_memory_count,
      detail: "Candidate memories awaiting accept, edit, reject, privacy, or project action.",
    },
    {
      label: "Open loops",
      value: workspace.summary.open_loop_count,
      detail: "Source-backed due, waiting, or unresolved items.",
    },
    {
      label: "Projects",
      value: workspace.summary.project_count,
      detail: "Live project dashboards and update candidates.",
    },
    {
      label: "Agents",
      value: workspace.summary.agent_count ?? workspace.agentActivity.agents.length,
      detail: "Known agent identities with policy-scoped activity.",
    },
    {
      label: "Schedules on",
      value: workspace.summary.scheduler_enabled_count ?? workspace.scheduler.enabled_count,
      detail: "Governed workflows enabled for local runs.",
    },
  ];

  return (
    <section id="vnext-home" className="metric-grid" aria-label="vNext home dashboard">
      {metrics.map((metric) => (
        <SectionCard key={metric.label} className="section-card--metric">
          <div className="metric-value">{metric.value}</div>
          <div className="metric-label">{metric.label}</div>
          <p className="metric-detail">{metric.detail}</p>
        </SectionCard>
      ))}
    </section>
  );
}
