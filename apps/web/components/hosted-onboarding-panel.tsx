import { SectionCard } from "./section-card";

const readinessChecklist = [
  "Use a supported API client to request magic-link sign-in and verify the challenge token.",
  "Create one hosted workspace, select it, and run workspace bootstrap through the hosted API.",
  "Confirm bootstrap readiness before opening the shipped Telegram controls in Settings.",
  "Set timezone, daily-brief, and quiet-hour preferences from the Settings view.",
  "Escalate onboarding failures through hosted admin incident visibility instead of direct database inspection.",
];

export function HostedOnboardingPanel() {
  return (
    <div className="stack">
      <SectionCard
        eyebrow="Hosted Entry Guide"
        title="Magic-link Setup Checklist"
        description="Instruction-only preview of the hosted setup sequence."
      >
        <p className="muted-copy">
          This page is guidance only. It does not submit magic-link requests, create or bootstrap a
          workspace, or save preferences. Use a supported API client for setup, then use Settings
          and Admin for the live controls exposed by this web shell.
        </p>
        <ul className="bullet-list">
          {readinessChecklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </SectionCard>

      <SectionCard
        eyebrow="Settings Handoff"
        title="Telegram Readiness"
        description="Bootstrap readiness is a prerequisite, not an action performed by this guide."
      >
        <p className="muted-copy">
          After completing hosted identity and workspace bootstrap through the API, open Settings to
          link Telegram and manage workspace-scoped notification and scheduling preferences.
        </p>
      </SectionCard>

      <SectionCard
        eyebrow="Support Posture"
        title="Onboarding Failure Visibility"
        description="P10-S5 keeps onboarding failures visible for support without reopening bootstrap semantics."
      >
        <p className="muted-copy">
          When onboarding fails, operators should inspect hosted admin incidents and workspace support
          posture before retrying. This keeps support workflows explicit and deterministic.
        </p>
      </SectionCard>
    </div>
  );
}
