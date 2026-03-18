import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";

export default function Loading() {
  return (
    <div className="page-stack" aria-busy="true">
      <PageHeader
        eyebrow="Entities"
        title="Entity review workspace"
        description="Loading entity list, selected detail, and related edge review state."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Loading route state</span>
          </div>
        }
      />

      <div className="entity-layout">
        <SectionCard
          eyebrow="Entity list"
          title="Loading tracked entities"
          description="Entity records are loading from the current source."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Selected entity"
          title="Loading selected entity"
          description="Type, source memories, and timestamps are loading."
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

      <SectionCard
        eyebrow="Related edges"
        title="Loading edge review"
        description="Ordered relationship edges are loading for the selected entity."
        className="loading-card"
      >
        <div className="detail-stack">
          <StatusBadge status="loading" label="Loading" />
          <div className="loading-placeholder loading-placeholder--card" />
          <div className="loading-placeholder loading-placeholder--card" />
        </div>
      </SectionCard>
    </div>
  );
}
