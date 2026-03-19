import type { ApiSource, GmailMessageIngestionResponse } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type GmailIngestionSummaryProps = {
  result: GmailMessageIngestionResponse | null;
  source: ApiSource | "unavailable" | null;
  unavailableReason?: string;
};

export function GmailIngestionSummary({
  result,
  source,
  unavailableReason,
}: GmailIngestionSummaryProps) {
  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Ingestion summary"
        title="Latest ingestion unavailable"
        description="No ingestion result is available because the latest request failed."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="Result unavailable" />
          {unavailableReason ? (
            <div className="execution-summary__note execution-summary__note--danger">
              <p className="execution-summary__label">Ingestion result</p>
              <p>{unavailableReason}</p>
            </div>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  if (!result) {
    return (
      <SectionCard
        eyebrow="Ingestion summary"
        title="No message ingested yet"
        description="Run one selected-message ingestion to review artifact linkage and media metadata."
      >
        <EmptyState
          title="Summary is idle"
          description="A successful ingestion will appear here with the resulting artifact path and media type."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Ingestion summary"
      title="Selected-message ingestion result"
      description="Review the resulting artifact path, media type, and linked workspace target."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={result.artifact.ingestion_status} />
          <StatusBadge
            status={source ?? "unavailable"}
            label={
              source === "live"
                ? "Live result"
                : source === "fixture"
                  ? "Fixture result"
                  : "Result unavailable"
            }
          />
        </div>

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Provider message ID</dt>
            <dd className="mono">{result.message.provider_message_id}</dd>
          </div>
          <div>
            <dt>Account email</dt>
            <dd>{result.account.email_address}</dd>
          </div>
          <div>
            <dt>Artifact path</dt>
            <dd className="mono">{result.message.artifact_relative_path}</dd>
          </div>
          <div>
            <dt>Linked artifact target</dt>
            <dd className="mono">{result.artifact.relative_path}</dd>
          </div>
          <div>
            <dt>Task workspace ID</dt>
            <dd className="mono">{result.artifact.task_workspace_id}</dd>
          </div>
          <div>
            <dt>Media type</dt>
            <dd className="mono">{result.message.media_type}</dd>
          </div>
        </dl>
      </div>
    </SectionCard>
  );
}
