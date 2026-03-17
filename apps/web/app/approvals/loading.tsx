import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";

export default function Loading() {
  return (
    <div className="page-stack" aria-busy="true">
      <PageHeader
        eyebrow="Approvals"
        title="Approval inbox and review"
        description="Loading live approval records and the currently selected review detail."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">Loading route state</span>
          </div>
        }
      />

      <div className="split-layout">
        <SectionCard
          eyebrow="Approval inbox"
          title="Loading approvals"
          description="The approval queue is being read from the current backing source."
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
          eyebrow="Approval detail"
          title="Loading selected approval"
          description="The inspector waits for the selected approval detail before actions become available."
          className="loading-card"
        >
          <div className="detail-stack">
            <StatusBadge status="loading" label="Loading" />
            <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
            <div className="loading-placeholder loading-placeholder--line" />
            <div className="loading-placeholder loading-placeholder--line" />
            <div className="loading-placeholder loading-placeholder--button" />
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
