"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { getApiConfig } from "../lib/api";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

const settingItems = [
  {
    title: "Telegram Link Start",
    detail: "Issue a deterministic link challenge bound to the active hosted workspace.",
  },
  {
    title: "Telegram Link Confirm",
    detail: "Confirm linkage only after webhook-observed link code proof from the Telegram chat identity.",
  },
  {
    title: "Telegram Status + Unlink",
    detail: "Inspect current transport readiness and remove Telegram linkage without local tooling.",
  },
  {
    title: "Messages, Threads, Receipts",
    detail: "Expose normalized inbound traffic, deterministic routing state, and outbound delivery posture.",
  },
];

type TelegramLinkChallenge = {
  challenge_token?: string;
  link_code: string;
  status: string;
  expires_at: string;
};

type TelegramIdentity = {
  id: string;
  workspace_id: string;
  external_chat_id: string;
  external_username: string | null;
  status: string;
};

type TelegramStatusPayload = {
  workspace_id: string;
  linked: boolean;
  identity: TelegramIdentity | null;
  latest_challenge: {
    link_code: string;
    status: string;
    expires_at: string;
  } | null;
  recent_transport: {
    message_id: string;
    direction: string;
    route_status: string;
    observed_at: string;
  } | null;
};

type TelegramMessage = {
  id: string;
  direction: string;
  route_status: string;
  message_text: string | null;
  provider_update_id: string | null;
  created_at: string;
};

type TelegramThread = {
  id: string;
  external_thread_key: string;
  last_message_at: string | null;
  updated_at: string;
};

type TelegramReceipt = {
  id: string;
  status: string;
  channel_message_id: string;
  recorded_at: string;
  failure_code: string | null;
};

type HostedSettingsPanelProps = {
  apiBaseUrl?: string;
};

function formatOptionalDate(value: string | null | undefined) {
  if (!value) {
    return "-";
  }

  try {
    return new Date(value).toLocaleString("en");
  } catch {
    return value;
  }
}

function trimOrNull(value: string) {
  const normalized = value.trim();
  return normalized === "" ? null : normalized;
}

export function HostedSettingsPanel({ apiBaseUrl }: HostedSettingsPanelProps) {
  const apiConfig = getApiConfig();
  const resolvedApiBaseUrl = (apiBaseUrl ?? apiConfig.apiBaseUrl).trim();
  const liveModeReady = resolvedApiBaseUrl !== "";

  const [sessionToken, setSessionToken] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [challengeToken, setChallengeToken] = useState("");

  const [isWorking, setIsWorking] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    liveModeReady
      ? "Provide a hosted session token, then run Telegram link start/confirm and status controls."
      : "Telegram controls are unavailable until NEXT_PUBLIC_ALICEBOT_API_BASE_URL is configured.",
  );

  const [latestChallenge, setLatestChallenge] = useState<TelegramLinkChallenge | null>(null);
  const [latestIdentity, setLatestIdentity] = useState<TelegramIdentity | null>(null);
  const [latestStatus, setLatestStatus] = useState<TelegramStatusPayload | null>(null);
  const [messages, setMessages] = useState<TelegramMessage[]>([]);
  const [threads, setThreads] = useState<TelegramThread[]>([]);
  const [receipts, setReceipts] = useState<TelegramReceipt[]>([]);

  async function requestTelegramJson<T>(
    path: string,
    init?: RequestInit,
    query?: Record<string, string | undefined>,
  ): Promise<T> {
    if (!liveModeReady) {
      throw new Error("NEXT_PUBLIC_ALICEBOT_API_BASE_URL must be configured for live Telegram controls.");
    }

    const token = sessionToken.trim();
    if (token === "") {
      throw new Error("Hosted session token is required.");
    }

    const url = new URL(path, `${resolvedApiBaseUrl.replace(/\/$/, "")}/`);
    for (const [key, value] of Object.entries(query ?? {})) {
      if (value) {
        url.searchParams.set(key, value);
      }
    }

    const response = await fetch(url.toString(), {
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

  async function handleStartLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await runOperation(async () => {
      const payload = await requestTelegramJson<{
        challenge: TelegramLinkChallenge;
        instructions: {
          bot_username: string;
          command: string;
        };
      }>("/v1/channels/telegram/link/start", {
        method: "POST",
        body: JSON.stringify({ workspace_id: trimOrNull(workspaceId) }),
      });

      setLatestChallenge(payload.challenge);
      if (payload.challenge.challenge_token) {
        setChallengeToken(payload.challenge.challenge_token);
      }
      setStatusTone("success");
      setStatusText(
        `Link challenge issued. Send ${payload.instructions.command} to @${payload.instructions.bot_username}, then confirm.`,
      );
    }, "Issuing Telegram link challenge...");
  }

  async function handleConfirmLink() {
    await runOperation(async () => {
      const token = challengeToken.trim();
      if (token === "") {
        throw new Error("Challenge token is required for link confirm.");
      }

      const payload = await requestTelegramJson<{
        identity: TelegramIdentity;
        challenge: TelegramLinkChallenge;
      }>("/v1/channels/telegram/link/confirm", {
        method: "POST",
        body: JSON.stringify({ challenge_token: token }),
      });

      setLatestIdentity(payload.identity);
      setLatestChallenge(payload.challenge);
      setStatusTone("success");
      setStatusText("Telegram link confirmed for the current hosted workspace.");
    }, "Confirming Telegram link challenge...");
  }

  async function handleLoadStatus() {
    await runOperation(async () => {
      const payload = await requestTelegramJson<TelegramStatusPayload>(
        "/v1/channels/telegram/status",
        undefined,
        { workspace_id: trimOrNull(workspaceId) ?? undefined },
      );

      setLatestStatus(payload);
      setLatestIdentity(payload.identity);
      setStatusTone("success");
      setStatusText(
        payload.linked
          ? "Telegram is linked and ready for transport operations."
          : "Telegram is not linked for the selected workspace.",
      );
    }, "Loading Telegram status...");
  }

  async function handleUnlink() {
    await runOperation(async () => {
      const payload = await requestTelegramJson<{ identity: TelegramIdentity }>(
        "/v1/channels/telegram/unlink",
        {
          method: "POST",
          body: JSON.stringify({ workspace_id: trimOrNull(workspaceId) }),
        },
      );

      setLatestIdentity(payload.identity);
      setStatusTone("success");
      setStatusText("Telegram identity unlinked for the selected workspace.");
    }, "Unlinking Telegram identity...");
  }

  async function handleRefreshTransportRecords() {
    await runOperation(async () => {
      const [messagePayload, threadPayload, receiptPayload] = await Promise.all([
        requestTelegramJson<{ items: TelegramMessage[] }>("/v1/channels/telegram/messages"),
        requestTelegramJson<{ items: TelegramThread[] }>("/v1/channels/telegram/threads"),
        requestTelegramJson<{ items: TelegramReceipt[] }>("/v1/channels/telegram/delivery-receipts"),
      ]);

      setMessages(messagePayload.items);
      setThreads(threadPayload.items);
      setReceipts(receiptPayload.items);
      setStatusTone("success");
      setStatusText("Loaded latest Telegram messages, threads, and delivery receipts.");
    }, "Loading Telegram transport records...");
  }

  return (
    <div className="stack">
      <SectionCard
        eyebrow="Hosted Settings"
        title="Telegram Channel Settings"
        description="Hosted controls cover link start/confirm, operational status, and deterministic transport records for Telegram."
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
        eyebrow="Hosted Controls"
        title="Session + Workspace Context"
        description="Provide a hosted session token and optional workspace UUID before issuing Telegram channel operations."
      >
        <div className="detail-stack">
          <div className="form-field">
            <label htmlFor="telegram-session-token">Hosted session token</label>
            <input
              id="telegram-session-token"
              name="telegram-session-token"
              type="password"
              value={sessionToken}
              onChange={(event) => setSessionToken(event.target.value)}
              placeholder="Paste Bearer token"
              disabled={isWorking || !liveModeReady}
            />
          </div>

          <div className="form-field">
            <label htmlFor="telegram-workspace-id">Workspace ID (optional)</label>
            <input
              id="telegram-workspace-id"
              name="telegram-workspace-id"
              value={workspaceId}
              onChange={(event) => setWorkspaceId(event.target.value)}
              placeholder="Use current session workspace when empty"
              disabled={isWorking || !liveModeReady}
            />
          </div>

          <div className="composer-status" aria-live="polite">
            <StatusBadge
              status={
                isWorking
                  ? "submitting"
                  : statusTone === "success"
                    ? "success"
                    : statusTone === "danger"
                      ? "error"
                      : liveModeReady
                        ? "ready"
                        : "unavailable"
              }
              label={
                isWorking
                  ? "Working"
                  : statusTone === "success"
                    ? "Ready"
                    : statusTone === "danger"
                      ? "Attention"
                      : liveModeReady
                        ? "Configured"
                        : "Unavailable"
              }
            />
            <span>{statusText}</span>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        eyebrow="Telegram Link"
        title="Link Start + Confirm"
        description="Start a deterministic link challenge, send the code in Telegram, then confirm from hosted settings."
      >
        <div className="detail-stack">
          <form onSubmit={handleStartLink}>
            <button
              type="submit"
              className="button"
              disabled={isWorking || !liveModeReady || sessionToken.trim() === ""}
            >
              {isWorking ? "Working..." : "Start Telegram link"}
            </button>
          </form>

          <div className="form-field">
            <label htmlFor="telegram-challenge-token">Challenge token</label>
            <input
              id="telegram-challenge-token"
              name="telegram-challenge-token"
              value={challengeToken}
              onChange={(event) => setChallengeToken(event.target.value)}
              placeholder="Challenge token returned by link start"
              disabled={isWorking || !liveModeReady}
            />
            <p className="field-hint">Use this token to confirm after Telegram webhook link proof is observed.</p>
          </div>

          <button
            type="button"
            className="button-secondary"
            onClick={handleConfirmLink}
            disabled={isWorking || !liveModeReady || sessionToken.trim() === "" || challengeToken.trim() === ""}
          >
            {isWorking ? "Working..." : "Confirm Telegram link"}
          </button>

          {latestChallenge ? (
            <div className="detail-stack">
              <p>
                <strong>Latest link code:</strong> <span className="mono">{latestChallenge.link_code}</span>
              </p>
              <p>
                <strong>Challenge status:</strong> {latestChallenge.status}
              </p>
              <p>
                <strong>Expires:</strong> {formatOptionalDate(latestChallenge.expires_at)}
              </p>
              <p>
                <strong>Telegram command:</strong> <span className="mono">/link {latestChallenge.link_code}</span>
              </p>
            </div>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard
        eyebrow="Transport Readiness"
        title="Status + Unlink"
        description="Inspect Telegram linkage state and remove channel identity binding for the selected workspace."
      >
        <div className="composer-actions">
          <button
            type="button"
            className="button"
            onClick={handleLoadStatus}
            disabled={isWorking || !liveModeReady || sessionToken.trim() === ""}
          >
            {isWorking ? "Working..." : "Load Telegram status"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={handleUnlink}
            disabled={isWorking || !liveModeReady || sessionToken.trim() === ""}
          >
            {isWorking ? "Working..." : "Unlink Telegram"}
          </button>
        </div>

        {latestStatus ? (
          <div className="detail-stack">
            <p>
              <strong>Workspace:</strong> <span className="mono">{latestStatus.workspace_id}</span>
            </p>
            <p>
              <strong>Linked:</strong> {latestStatus.linked ? "yes" : "no"}
            </p>
            <p>
              <strong>Recent route status:</strong> {latestStatus.recent_transport?.route_status ?? "-"}
            </p>
            <p>
              <strong>Recent transport observed:</strong>{" "}
              {formatOptionalDate(latestStatus.recent_transport?.observed_at)}
            </p>
          </div>
        ) : null}

        {latestIdentity ? (
          <div className="detail-stack">
            <p>
              <strong>Identity status:</strong> {latestIdentity.status}
            </p>
            <p>
              <strong>External chat:</strong> <span className="mono">{latestIdentity.external_chat_id}</span>
            </p>
            <p>
              <strong>External username:</strong> {latestIdentity.external_username ?? "-"}
            </p>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard
        eyebrow="Transport Records"
        title="Messages, Threads, Receipts"
        description="Load deterministic inbound routing artifacts and outbound delivery posture for Telegram transport."
      >
        <div className="detail-stack">
          <button
            type="button"
            className="button"
            onClick={handleRefreshTransportRecords}
            disabled={isWorking || !liveModeReady || sessionToken.trim() === ""}
          >
            {isWorking ? "Working..." : "Refresh transport records"}
          </button>

          <p>
            <strong>Messages:</strong> {messages.length}
          </p>
          <ul className="bullet-list">
            {messages.slice(0, 5).map((message) => (
              <li key={message.id}>
                <span className="mono">{message.id}</span> · {message.direction} · {message.route_status} ·{" "}
                {message.message_text ?? "(no text)"}
              </li>
            ))}
          </ul>

          <p>
            <strong>Threads:</strong> {threads.length}
          </p>
          <ul className="bullet-list">
            {threads.slice(0, 5).map((thread) => (
              <li key={thread.id}>
                <span className="mono">{thread.external_thread_key}</span> · updated {formatOptionalDate(thread.updated_at)}
              </li>
            ))}
          </ul>

          <p>
            <strong>Delivery receipts:</strong> {receipts.length}
          </p>
          <ul className="bullet-list">
            {receipts.slice(0, 5).map((receipt) => (
              <li key={receipt.id}>
                <span className="mono">{receipt.channel_message_id}</span> · {receipt.status}
                {receipt.failure_code ? ` · ${receipt.failure_code}` : ""}
              </li>
            ))}
          </ul>
        </div>
      </SectionCard>

      <SectionCard
        eyebrow="Control Truth"
        title="P10-S2 Boundaries"
        description="Telegram transport is operational, but chat-native continuity behavior is still out of scope."
      >
        <p className="muted-copy">
          This surface does not claim Telegram continuity capture, recall, resume, correction, approval
          resolution, or scheduler execution. It is transport and control-plane readiness only.
        </p>
      </SectionCard>
    </div>
  );
}
