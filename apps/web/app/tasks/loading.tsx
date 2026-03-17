import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";

export default function Loading() {
  return (
    <div className="page-stack" aria-busy="true">
      <PageHeader
        eyebrow="Tasks"
        title="Task lifecycle inspection"
        description="Loading live task records and the selected task-step timeline."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Loading route state</span>
          </div>
        }
      />

      <div className="dashboard-grid dashboard-grid--detail">
        <SectionCard
          eyebrow="Task list"
          title="Loading tasks"
          description="The governed task list is being read from the current backing source."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>

        <div className="stack">
          <SectionCard
            eyebrow="Selected task"
            title="Loading selected task"
            description="Task summary state appears here as soon as the selected task detail resolves."
            className="loading-card"
          >
            <div className="detail-stack">
              <StatusBadge status="loading" label="Loading" />
              <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
              <div className="loading-placeholder loading-placeholder--line" />
              <div className="loading-placeholder loading-placeholder--button" />
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Task steps"
            title="Loading task timeline"
            description="Ordered task-step detail is loading from the selected task."
            className="loading-card"
          >
            <div className="detail-stack">
              <StatusBadge status="loading" label="Loading" />
              <div className="loading-placeholder loading-placeholder--card" />
              <div className="loading-placeholder loading-placeholder--card" />
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
