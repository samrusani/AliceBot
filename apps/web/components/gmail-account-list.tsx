import Link from "next/link";

import type { ApiSource, GmailAccountListSummary, GmailAccountRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type GmailAccountListProps = {
  accounts: GmailAccountRecord[];
  selectedAccountId?: string;
  summary: GmailAccountListSummary | null;
  source: ApiSource | "unavailable";
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

function gmailAccountHref(gmailAccountId: string) {
  return `/gmail?account=${encodeURIComponent(gmailAccountId)}`;
}

export function GmailAccountList({
  accounts,
  selectedAccountId,
  summary,
  source,
  unavailableReason,
}: GmailAccountListProps) {
  if (source === "unavailable" && accounts.length === 0) {
    return (
      <SectionCard
        eyebrow="Account list"
        title="Gmail account list unavailable"
        description="Connected Gmail accounts could not be loaded in the current workspace state."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="List unavailable" />
          {unavailableReason ? (
            <p className="responsive-note">Gmail account list read failed: {unavailableReason}</p>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  if (accounts.length === 0) {
    return (
      <SectionCard
        eyebrow="Account list"
        title="No Gmail accounts connected"
        description="Connect one Gmail account to enable bounded account review and selected-message ingestion."
      >
        <EmptyState
          title="No connected accounts"
          description="Use the connect form to add one Gmail account through the shipped read-only connector seam."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Account list"
      title="Connected Gmail accounts"
      description="Select one account to inspect metadata, scope, and bounded ingestion controls."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <div className="cluster">
            <StatusBadge
              status={source}
              label={
                source === "live"
                  ? "Live list"
                  : source === "fixture"
                    ? "Fixture list"
                    : "List unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} total</span> : null}
          </div>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live account list read failed: {unavailableReason}</p>
        ) : null}

        <div className="list-rows">
          {accounts.map((account) => (
            <Link
              key={account.id}
              href={gmailAccountHref(account.id)}
              className={`list-row${account.id === selectedAccountId ? " is-selected" : ""}`}
              aria-current={account.id === selectedAccountId ? "page" : undefined}
            >
              <div className="list-row__topline">
                <div className="detail-stack">
                  <span className="list-row__eyebrow">{formatDate(account.updated_at)}</span>
                  <h3 className="list-row__title">{account.email_address}</h3>
                </div>
                <StatusBadge status={account.provider} />
              </div>

              <div className="list-row__meta">
                <span className="meta-pill mono">{account.id}</span>
                <span className="meta-pill mono">{account.provider_account_id}</span>
                <span className="meta-pill">{account.display_name ?? "No display name"}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
