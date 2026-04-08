import { PageHeader } from "../../components/page-header";
import { HostedSettingsPanel } from "../../components/hosted-settings-panel";

export default function SettingsPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Phase 10 Sprint 1"
        title="Hosted Settings"
        description="Persist timezone, brief-policy inputs, quiet hours, and linked-device visibility for hosted workspace continuity."
      />
      <HostedSettingsPanel />
    </div>
  );
}
