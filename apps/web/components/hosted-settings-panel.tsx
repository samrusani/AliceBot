import { SectionCard } from "./section-card";

const settingItems = [
  {
    title: "Timezone",
    detail: "Persist IANA timezone for future scheduled brief orchestration.",
  },
  {
    title: "Brief Preferences",
    detail: "Capture daily brief posture inputs only; no scheduler execution in this sprint.",
  },
  {
    title: "Quiet Hours",
    detail: "Store quiet-hour boundaries for later policy-driven delivery logic.",
  },
  {
    title: "Device Visibility",
    detail: "List and revoke linked devices deterministically.",
  },
];

export function HostedSettingsPanel() {
  return (
    <div className="stack">
      <SectionCard
        eyebrow="Hosted Settings"
        title="Preference Foundations"
        description="Settings are persisted foundations for future brief scheduling and channel delivery."
      >
        <ul className="bullet-list">
          {settingItems.map((item) => (
            <li key={item.title}>
              <strong>{item.title}:</strong> {item.detail}
            </li>
          ))}
        </ul>
      </SectionCard>

      <SectionCard
        eyebrow="Control Truth"
        title="P10-S1 Boundaries"
        description="Scope stays on identity/workspace/bootstrap/device/preferences only."
      >
        <p className="muted-copy">
          Hosted settings expose readiness inputs and device state, but do not claim Telegram linkage,
          scheduler execution, or brief delivery in Phase 10 Sprint 1.
        </p>
      </SectionCard>
    </div>
  );
}
