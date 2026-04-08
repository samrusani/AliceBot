import { PageHeader } from "../../components/page-header";
import { HostedSettingsPanel } from "../../components/hosted-settings-panel";

export default function SettingsPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Phase 10 Sprint 2"
        title="Hosted Settings"
        description="Manage Telegram link/unlink lifecycle, transport status, normalized message visibility, and deterministic delivery receipts."
      />
      <HostedSettingsPanel />
    </div>
  );
}
