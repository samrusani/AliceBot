import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";

export default function Loading() {
  return (
    <div className="page-stack" aria-busy="true">
      <PageHeader
        eyebrow="Artifacts"
        title="Artifact review workspace"
        description="Loading artifact list, selected detail, linked workspace summary, and ordered chunk review."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Loading route state</span>
          </div>
        }
      />

      <div className="artifact-layout">
        <SectionCard
          eyebrow="Artifact list"
          title="Loading persisted artifacts"
          description="Artifact rows are loading from the current source."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Selected artifact"
          title="Loading selected artifact"
          description="Metadata, ingestion status, and rooted path context are loading."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
            <div className="loading-placeholder loading-placeholder--line" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>
      </div>

      <div className="artifact-review-grid">
        <SectionCard
          eyebrow="Linked workspace"
          title="Loading workspace summary"
          description="Task workspace linkage and rooted path context are loading."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Chunk review"
          title="Loading persisted chunks"
          description="Ordered chunk rows and evidence text are loading."
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
  );
}
