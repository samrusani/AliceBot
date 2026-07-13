import { PageHeader } from "./page-header";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type WorkspaceLoadingProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export function WorkspaceLoading({ eyebrow, title, description }: WorkspaceLoadingProps) {
  return (
    <div className="page-stack" aria-busy="true" aria-live="polite">
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        meta={<span className="subtle-chip">Loading route state</span>}
      />
      <div className="grid grid--two">
        {["Primary workspace", "Supporting context"].map((sectionTitle) => (
          <SectionCard
            key={sectionTitle}
            eyebrow="Loading"
            title={sectionTitle}
            description="The server is resolving independent data sources for this view."
            className="loading-card"
          >
            <div className="detail-stack">
              <StatusBadge status="loading" label="Loading" />
              <div className="loading-placeholder loading-placeholder--line loading-placeholder--wide" />
              <div className="loading-placeholder loading-placeholder--card" />
              <div className="loading-placeholder loading-placeholder--card" />
            </div>
          </SectionCard>
        ))}
      </div>
    </div>
  );
}
