import { HostedOnboardingPanel } from "../../components/hosted-onboarding-panel";
import { PageHeader } from "../../components/page-header";

export default function OnboardingPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Phase 10 Sprint 1"
        title="Hosted Onboarding"
        description="Bootstrap hosted identity, workspace setup, and deterministic device trust without expanding into Telegram flows."
      />
      <HostedOnboardingPanel />
    </div>
  );
}
