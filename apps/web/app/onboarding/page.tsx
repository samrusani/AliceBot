import { HostedOnboardingPanel } from "../../components/hosted-onboarding-panel";
import { PageHeader } from "../../components/page-header";

export default function OnboardingPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Hosted Setup Preview"
        title="Hosted Onboarding Guide"
        description="Read the hosted identity and workspace setup sequence. This instruction-only page does not execute onboarding operations."
      />
      <HostedOnboardingPanel />
    </div>
  );
}
