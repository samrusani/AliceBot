import type { ApiSource, CalendarAccountRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type CalendarAccountDetailProps = {
  account: CalendarAccountRecord | null;
  source: ApiSource | "unavailable" | null;
  unavailableReason?: string;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function CalendarAccountDetail({
  account,
  source,
  unavailableReason,
}: CalendarAccountDetailProps) {
  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Selected account"
        title="Account detail unavailable"
        description="The account list loaded, but selected account detail is currently unavailable."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="Detail unavailable" />
          {unavailableReason ? (
            <div className="execution-summary__note execution-summary__note--danger">
              <p className="execution-summary__label">Account detail read</p>
              <p>{unavailableReason}</p>
            </div>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  if (!account) {
    return (
      <SectionCard
        eyebrow="Selected account"
        title="No account selected"
        description="Select one connected Calendar account to inspect metadata and scope summary."
      >
        <EmptyState
          title="Account detail is idle"
          description="Choose one account from the list to open the bounded detail panel."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Selected account"
      title={account.email_address}
      description="Account detail stays bounded to connector metadata and scope without expanding into event browsing or scheduling actions."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={account.provider} />
          <StatusBadge status={account.auth_kind} />
          <StatusBadge
            status={source ?? "unavailable"}
            label={
              source === "live"
                ? "Live detail"
                : source === "fixture"
                  ? "Fixture detail"
                  : "Detail unavailable"
            }
          />
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live account detail read failed: {unavailableReason}</p>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Account ID</dt>
            <dd className="mono">{account.id}</dd>
          </div>
          <div>
            <dt>Provider account ID</dt>
            <dd className="mono">{account.provider_account_id}</dd>
          </div>
          <div>
            <dt>Email address</dt>
            <dd>{account.email_address}</dd>
          </div>
          <div>
            <dt>Display name</dt>
            <dd>{account.display_name ?? "None"}</dd>
          </div>
          <div>
            <dt>Scope</dt>
            <dd className="mono">{account.scope}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDate(account.updated_at)}</dd>
          </div>
        </dl>

        <div className="detail-group detail-group--muted">
          <h3>Scope summary</h3>
          <p className="muted-copy">
            This route uses the shipped read-only Calendar account seam and explicit single-event
            ingestion seam only. It does not expand into event listing, search, sync, recurrence,
            or write actions.
          </p>
        </div>
      </div>
    </SectionCard>
  );
}
