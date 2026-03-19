import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";

export default function Loading() {
  return (
    <div className="page-stack" aria-busy="true">
      <PageHeader
        eyebrow="Calendar"
        title="Calendar account review workspace"
        description="Loading connected account list, selected account detail, discovery controls, and single-event ingestion controls."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Loading route state</span>
          </div>
        }
      />

      <div className="calendar-layout">
        <SectionCard
          eyebrow="Account list"
          title="Loading connected accounts"
          description="Calendar account rows are loading from the current source."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Selected account"
          title="Loading selected account"
          description="Account metadata and scope summary are loading."
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

      <div className="calendar-action-grid">
        <SectionCard
          eyebrow="Connect account"
          title="Loading connect controls"
          description="Bounded connect-account fields are loading."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Event discovery"
          title="Loading discovery controls"
          description="Bounded event list filters and selected-event rows are loading."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
            <div className="loading-placeholder loading-placeholder--line" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>
      </div>

      <SectionCard
        eyebrow="Ingest event"
        title="Loading ingestion controls"
        description="Selected-event and task-workspace ingestion controls are loading."
        className="loading-card"
      >
        <div className="detail-stack">
          <StatusBadge status="loading" label="Loading" />
          <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
          <div className="loading-placeholder loading-placeholder--line" />
          <div className="loading-placeholder loading-placeholder--button" />
        </div>
      </SectionCard>
    </div>
  );
}
