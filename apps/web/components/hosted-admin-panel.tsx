"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { getApiConfig } from "../lib/api";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type HostedOverview = {
  window_hours: number;
  workspaces: {
    total_count: number;
    ready_count: number;
    pending_count: number;
    linked_telegram_workspace_count: number;
  };
  delivery_receipts: {
    total_count: number;
    failed_count: number;
    suppressed_count: number;
  };
  chat_telemetry: {
    total_count: number;
    failed_count: number;
    rollout_blocked_count: number;
    rate_limited_count: number;
    abuse_blocked_count: number;
  };
  incidents: {
    open_count: number;
  };
};

type HostedOverviewPayload = HostedOverview | { overview?: HostedOverview | null };

type RolloutFlag = {
  flag_key: string;
  enabled: boolean;
  source_scope: string;
  source_cohort_key?: string | null;
};

type HostedAdminPanelProps = {
  apiBaseUrl?: string;
};

function formatTimestamp(value: string | undefined) {
  if (!value) {
    return "-";
  }

  try {
    return new Date(value).toLocaleString("en");
  } catch {
    return value;
  }
}

export function HostedAdminPanel({ apiBaseUrl }: HostedAdminPanelProps) {
  const apiConfig = getApiConfig();
  const resolvedApiBaseUrl = (apiBaseUrl ?? apiConfig.apiBaseUrl).trim();
  const liveModeReady = resolvedApiBaseUrl !== "";

  const [sessionToken, setSessionToken] = useState("");
  const [isWorking, setIsWorking] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    liveModeReady
      ? "Load hosted admin datasets to inspect workspace, delivery, incidents, rollout flags, analytics, and rate-limit posture."
      : "Admin datasets are unavailable until NEXT_PUBLIC_ALICEBOT_API_BASE_URL is configured.",
  );

  const [overview, setOverview] = useState<HostedOverview | null>(null);
  const [workspacesCount, setWorkspacesCount] = useState<number | null>(null);
  const [deliveryCount, setDeliveryCount] = useState<number | null>(null);
  const [incidentCount, setIncidentCount] = useState<number | null>(null);
  const [rolloutFlags, setRolloutFlags] = useState<RolloutFlag[]>([]);
  const [analyticsTotal, setAnalyticsTotal] = useState<number | null>(null);
  const [rateLimitedTotal, setRateLimitedTotal] = useState<number | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<string | undefined>(undefined);

  async function requestAdminJson<T>(path: string, init?: RequestInit): Promise<T> {
    if (!liveModeReady) {
      throw new Error("NEXT_PUBLIC_ALICEBOT_API_BASE_URL must be configured for hosted admin controls.");
    }

    const token = sessionToken.trim();
    if (token === "") {
      throw new Error("Hosted session token is required.");
    }

    const response = await fetch(new URL(path, `${resolvedApiBaseUrl.replace(/\/$/, "")}/`).toString(), {
      cache: "no-store",
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(init?.headers ?? {}),
      },
    });

    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    if (!response.ok) {
      throw new Error(payload?.detail ?? "Request failed");
    }

    return payload as T;
  }

  async function runOperation(operation: () => Promise<void>, loadingText: string) {
    setIsWorking(true);
    setStatusTone("info");
    setStatusText(loadingText);

    try {
      await operation();
    } catch (error) {
      setStatusTone("danger");
      setStatusText(error instanceof Error ? error.message : "Request failed");
    } finally {
      setIsWorking(false);
    }
  }

  async function loadAdminDatasets() {
    await runOperation(async () => {
      const [overviewPayload, workspacesPayload, deliveryPayload, incidentsPayload, rolloutPayload, analyticsPayload, rateLimitsPayload] =
        await Promise.all([
          requestAdminJson<HostedOverviewPayload>("/v1/admin/hosted/overview"),
          requestAdminJson<{ items: unknown[] }>("/v1/admin/hosted/workspaces"),
          requestAdminJson<{ items: unknown[] }>("/v1/admin/hosted/delivery-receipts"),
          requestAdminJson<{ items: unknown[] }>("/v1/admin/hosted/incidents?status=open"),
          requestAdminJson<{ items: RolloutFlag[] }>("/v1/admin/hosted/rollout-flags"),
          requestAdminJson<{ analytics: { total_events: number } }>("/v1/admin/hosted/analytics"),
          requestAdminJson<{ items: unknown[] }>("/v1/admin/hosted/rate-limits"),
        ]);

      const resolvedOverview: HostedOverview | null =
        "workspaces" in overviewPayload ? overviewPayload : overviewPayload.overview ?? null;
      setOverview(resolvedOverview);
      setWorkspacesCount(workspacesPayload.items.length);
      setDeliveryCount(deliveryPayload.items.length);
      setIncidentCount(incidentsPayload.items.length);
      setRolloutFlags(rolloutPayload.items);
      setAnalyticsTotal(analyticsPayload.analytics.total_events);
      setRateLimitedTotal(rateLimitsPayload.items.length);
      setLastLoadedAt(new Date().toISOString());
      setStatusTone("success");
      setStatusText("Hosted admin datasets loaded.");
    }, "Loading hosted admin datasets...");
  }

  async function patchRolloutFlag(flagKey: string, enabled: boolean) {
    await runOperation(async () => {
      const currentFlag = rolloutFlags.find((flag) => flag.flag_key === flagKey);
      const payload = await requestAdminJson<{ items: RolloutFlag[] }>("/v1/admin/hosted/rollout-flags", {
        method: "PATCH",
        body: JSON.stringify({
          updates: [
            {
              flag_key: flagKey,
              enabled,
              cohort_key: currentFlag?.source_cohort_key ?? undefined,
            },
          ],
        }),
      });

      setRolloutFlags(payload.items);
      setStatusTone("success");
      setStatusText(`Rollout flag ${flagKey} set to ${enabled ? "enabled" : "disabled"}.`);
    }, `Updating ${flagKey}...`);
  }

  function handleLoadSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadAdminDatasets();
  }

  return (
    <div className="stack">
      <SectionCard
        eyebrow="P10-S5 Admin"
        title="Hosted Beta Operations"
        description="Operator-only support visibility for workspace posture, delivery receipts, incidents, rollout flags, analytics, and rate limits."
      >
        <p className="muted-copy">
          This panel is for <strong>Alice Connect hosted beta operations</strong>. Alice Core OSS runtime and
          deterministic CLI/MCP semantics remain unchanged.
        </p>
        <form className="stack" onSubmit={handleLoadSubmit}>
          <label className="field-label" htmlFor="hosted-admin-session-token">
            Hosted session token
          </label>
          <input
            id="hosted-admin-session-token"
            className="text-input"
            placeholder="Paste Bearer token"
            value={sessionToken}
            onChange={(event) => setSessionToken(event.target.value)}
          />
          <div className="button-row">
            <button type="submit" className="button button--primary" disabled={isWorking || !liveModeReady}>
              Load admin datasets
            </button>
            <button
              type="button"
              className="button button--secondary"
              disabled={isWorking || !liveModeReady}
              onClick={() => patchRolloutFlag("hosted_chat_handle_enabled", false)}
            >
              Disable chat rollout
            </button>
            <button
              type="button"
              className="button button--secondary"
              disabled={isWorking || !liveModeReady}
              onClick={() => patchRolloutFlag("hosted_chat_handle_enabled", true)}
            >
              Enable chat rollout
            </button>
          </div>
        </form>

        <div className="status-row">
          <StatusBadge status={statusTone === "danger" ? "failed" : statusTone === "success" ? "active" : "pending_approval"} />
          <p className="muted-copy" role="status">
            {statusText}
          </p>
        </div>
      </SectionCard>

      <SectionCard
        eyebrow="Overview"
        title="Launch Readiness Snapshot"
        description="Cross-workspace operational summary for launch-gate checks."
      >
        <dl className="key-value-grid">
          <div>
            <dt>Workspaces (window)</dt>
            <dd>{overview?.workspaces.total_count ?? workspacesCount ?? 0}</dd>
          </div>
          <div>
            <dt>Open incidents</dt>
            <dd>{overview?.incidents.open_count ?? incidentCount ?? 0}</dd>
          </div>
          <div>
            <dt>Delivery receipts</dt>
            <dd>{overview?.delivery_receipts.total_count ?? deliveryCount ?? 0}</dd>
          </div>
          <div>
            <dt>Telemetry events</dt>
            <dd>{overview?.chat_telemetry.total_count ?? analyticsTotal ?? 0}</dd>
          </div>
          <div>
            <dt>Rate-limit events</dt>
            <dd>{rateLimitedTotal ?? 0}</dd>
          </div>
          <div>
            <dt>Last refreshed</dt>
            <dd>{formatTimestamp(lastLoadedAt)}</dd>
          </div>
        </dl>
      </SectionCard>

      <SectionCard
        eyebrow="Rollout"
        title="Flag Posture"
        description="Current hosted rollout flags visible to the authenticated admin operator."
      >
        <ul className="bullet-list">
          {rolloutFlags.length === 0 ? <li>No rollout flags loaded yet.</li> : null}
          {rolloutFlags.map((flag) => (
            <li key={flag.flag_key}>
              <strong>{flag.flag_key}</strong>: {flag.enabled ? "enabled" : "disabled"} ({flag.source_scope})
            </li>
          ))}
        </ul>
      </SectionCard>
    </div>
  );
}
