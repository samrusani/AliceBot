import { PageHeader } from "../../components/page-header";
import { HostedSettingsPanel } from "../../components/hosted-settings-panel";

export default function SettingsPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Phase 10 Sprint 4"
        title="Hosted Settings"
        description="Manage Telegram link/unlink, notification preferences, daily brief delivery, open-loop prompts, and scheduler posture."
      />
      <HostedSettingsPanel />
    </div>
  );
}
