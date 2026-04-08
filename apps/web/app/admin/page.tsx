import { HostedAdminPanel } from "../../components/hosted-admin-panel";
import { PageHeader } from "../../components/page-header";

export default function HostedAdminPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Phase 10 Sprint 5"
        title="Hosted Admin"
        description="Inspect hosted workspace posture, delivery receipts, incidents, rollout flags, analytics, and rate-limit evidence for beta support."
      />
      <HostedAdminPanel />
    </div>
  );
}
