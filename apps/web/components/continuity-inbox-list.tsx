import Link from "next/link";

import type {
  ApiSource,
  ContinuityCaptureInboxItem,
  ContinuityCaptureInboxSummary,
} from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityInboxListProps = {
  items: ContinuityCaptureInboxItem[];
  selectedCaptureId?: string;
  summary: ContinuityCaptureInboxSummary | null;
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

function previewContent(value: string) {
  return value.length > 160 ? `${value.slice(0, 157)}...` : value;
}

export function ContinuityInboxList({
  items,
  selectedCaptureId,
  summary,
  source,
  unavailableReason,
}: ContinuityInboxListProps) {
  if (items.length === 0) {
    return (
      <SectionCard
        eyebrow="Capture inbox"
        title="No captures yet"
        description="Use fast capture to append immutable events. Ambiguous captures remain visible in triage posture."
      >
        <EmptyState
          title="Inbox is empty"
          description="Submit one capture to seed the continuity inbox and derived-object pipeline."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Capture inbox"
      title="Recent captures"
      description="Every row is an immutable capture event. Derived objects are shown only when admission is explicit or high confidence."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <div className="cluster">
            <StatusBadge
              status={source}
              label={
                source === "live"
                  ? "Live inbox"
                  : source === "fixture"
                    ? "Fixture inbox"
                    : "Inbox unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} total</span> : null}
            {summary ? <span className="meta-pill">{summary.triage_count} triage</span> : null}
          </div>
        </div>

        {unavailableReason ? <p className="responsive-note">Live inbox read failed: {unavailableReason}</p> : null}

        <div className="list-rows">
          {items.map((item) => {
            const capture = item.capture_event;
            const derived = item.derived_object;
            const href = `/continuity?capture=${encodeURIComponent(capture.id)}`;

            return (
              <Link
                key={capture.id}
                href={href}
                className={`list-row${capture.id === selectedCaptureId ? " is-selected" : ""}`}
                aria-current={capture.id === selectedCaptureId ? "page" : undefined}
              >
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{formatDate(capture.created_at)}</span>
                    <h3 className="list-row__title">{previewContent(capture.raw_content)}</h3>
                  </div>
                  <div className="cluster">
                    <StatusBadge
                      status={capture.admission_posture}
                      label={capture.admission_posture === "TRIAGE" ? "Triage" : "Derived"}
                    />
                    {capture.explicit_signal ? (
                      <span className="meta-pill mono">{capture.explicit_signal}</span>
                    ) : null}
                  </div>
                </div>

                <div className="list-row__meta">
                  <span className="meta-pill mono">{capture.id}</span>
                  {derived ? (
                    <span className="meta-pill">{derived.object_type}</span>
                  ) : (
                    <span className="meta-pill">No durable object</span>
                  )}
                  <span className="meta-pill">{capture.admission_reason}</span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </SectionCard>
  );
}
