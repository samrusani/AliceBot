import { SectionCard } from "./section-card";

const readinessChecklist = [
  "Request magic-link sign-in and verify the challenge token.",
  "Create one hosted workspace and pin it as current.",
  "Run workspace bootstrap and confirm readiness for next-phase Telegram linkage.",
  "Set timezone and brief/quiet-hour preference scaffolding for future scheduling.",
];

export function HostedOnboardingPanel() {
  return (
    <div className="stack">
      <SectionCard
        eyebrow="Hosted Entry"
        title="Magic-link Identity"
        description="Use magic-link only for Phase 10 Sprint 1 hosted entry."
      >
        <ul className="bullet-list">
          {readinessChecklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </SectionCard>

      <SectionCard
        eyebrow="Scope Guard"
        title="Telegram State"
        description="Bootstrap indicates readiness only. Telegram linking is intentionally deferred."
      >
        <p className="muted-copy">
          Telegram channel linkage is <strong>not available in P10-S1</strong>. This screen only
          confirms that hosted identity, workspace bootstrap, devices, and preferences are ready for
          a later Telegram sprint.
        </p>
      </SectionCard>
    </div>
  );
}
