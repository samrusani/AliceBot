import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";

export default function Loading() {
  return (
    <div className="page-stack" aria-busy="true">
      <PageHeader
        eyebrow="Memories"
        title="Memory review workspace"
        description="Loading memory evaluation summary, active list state, selected detail, revisions, and labels."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Loading route state</span>
          </div>
        }
      />

      <SectionCard
        eyebrow="Memory summary"
        title="Loading evaluation posture"
        description="Evaluation summary and review-queue state are loading from the current source."
        className="loading-card"
      >
        <div className="detail-stack">
          <StatusBadge status="loading" label="Loading" />
          <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
          <div className="loading-placeholder loading-placeholder--card" />
        </div>
      </SectionCard>

      <div className="memory-layout">
        <SectionCard
          eyebrow="Memory list"
          title="Loading memories"
          description="The active memory list is loading."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Selected memory"
          title="Loading selected memory"
          description="Value, source events, and timestamps are loading."
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

      <div className="memory-followup-grid">
        <SectionCard
          eyebrow="Revision history"
          title="Loading revisions"
          description="Ordered revision history is loading."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--card" />
            <div className="loading-placeholder loading-placeholder--card" />
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Review labels"
          title="Loading labels"
          description="Current labels and submission status are loading."
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
    </div>
  );
}
