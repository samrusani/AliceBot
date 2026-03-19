"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { useRouter } from "next/navigation";

import { connectGmailAccount } from "../lib/api";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type GmailAccountConnectFormProps = {
  apiBaseUrl?: string;
  userId?: string;
};

const GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly" as const;

export function GmailAccountConnectForm({ apiBaseUrl, userId }: GmailAccountConnectFormProps) {
  const router = useRouter();
  const liveModeReady = Boolean(apiBaseUrl && userId);

  const [providerAccountId, setProviderAccountId] = useState("");
  const [emailAddress, setEmailAddress] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [accessTokenExpiresAt, setAccessTokenExpiresAt] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    liveModeReady
      ? "Enter one account at a time, including secret-bearing credentials, then connect."
      : "Gmail connect is unavailable until live API configuration is present.",
  );

  const canSubmit = liveModeReady && !isSubmitting;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!apiBaseUrl || !userId) {
      setStatusTone("info");
      setStatusText("Gmail connect is unavailable until live API configuration is present.");
      return;
    }

    const normalizedRefreshToken = refreshToken.trim();
    const normalizedClientId = clientId.trim();
    const normalizedClientSecret = clientSecret.trim();
    const normalizedExpiresAt = accessTokenExpiresAt.trim();
    const refreshFields = [
      normalizedRefreshToken,
      normalizedClientId,
      normalizedClientSecret,
      normalizedExpiresAt,
    ];
    const hasAnyRefreshField = refreshFields.some(Boolean);
    const hasFullRefreshBundle = refreshFields.every(Boolean);

    if (hasAnyRefreshField && !hasFullRefreshBundle) {
      setStatusTone("danger");
      setStatusText(
        "Refresh credentials must include refresh token, client id, client secret, and access-token expiry.",
      );
      return;
    }

    const expiresTimestamp = hasFullRefreshBundle ? Date.parse(normalizedExpiresAt) : null;
    if (hasFullRefreshBundle && Number.isNaN(expiresTimestamp)) {
      setStatusTone("danger");
      setStatusText("Access-token expiry must be a valid date and time.");
      return;
    }
    const normalizedExpiresAtIso =
      hasFullRefreshBundle && expiresTimestamp !== null
        ? new Date(expiresTimestamp).toISOString()
        : null;

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Connecting Gmail account...");

    try {
      const payload = await connectGmailAccount(apiBaseUrl, {
        user_id: userId,
        provider_account_id: providerAccountId.trim(),
        email_address: emailAddress.trim(),
        display_name: displayName.trim() ? displayName.trim() : null,
        scope: GMAIL_READONLY_SCOPE,
        access_token: accessToken.trim(),
        refresh_token: hasFullRefreshBundle ? normalizedRefreshToken : null,
        client_id: hasFullRefreshBundle ? normalizedClientId : null,
        client_secret: hasFullRefreshBundle ? normalizedClientSecret : null,
        access_token_expires_at: hasFullRefreshBundle ? normalizedExpiresAtIso : null,
      });

      setStatusTone("success");
      setStatusText(`Connected ${payload.account.email_address}.`);
      setAccessToken("");
      setRefreshToken("");
      setClientSecret("");
      setAccessTokenExpiresAt("");
      router.push(`/gmail?account=${encodeURIComponent(payload.account.id)}`);
      router.refresh();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Connection failed";
      setStatusTone("danger");
      setStatusText(`Unable to connect account: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <SectionCard
      eyebrow="Connect account"
      title="Add Gmail account"
      description="Connection is explicit and bounded to the shipped read-only scope with secret-bearing credential fields."
    >
      <form className="detail-stack" onSubmit={handleSubmit}>
        <div className="form-field-group form-field-group--two-up">
          <div className="form-field">
            <label htmlFor="gmail-provider-account-id">Provider account ID</label>
            <input
              id="gmail-provider-account-id"
              name="gmail-provider-account-id"
              value={providerAccountId}
              onChange={(event) => setProviderAccountId(event.target.value)}
              placeholder="acct-owner-001"
              required
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
          <div className="form-field">
            <label htmlFor="gmail-email-address">Email address</label>
            <input
              id="gmail-email-address"
              name="gmail-email-address"
              value={emailAddress}
              onChange={(event) => setEmailAddress(event.target.value)}
              placeholder="owner@gmail.example"
              required
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
        </div>

        <div className="form-field-group form-field-group--two-up">
          <div className="form-field">
            <label htmlFor="gmail-display-name">Display name (optional)</label>
            <input
              id="gmail-display-name"
              name="gmail-display-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Owner"
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
          <div className="form-field">
            <label htmlFor="gmail-scope">Scope</label>
            <input
              id="gmail-scope"
              name="gmail-scope"
              value={GMAIL_READONLY_SCOPE}
              readOnly
              className="mono"
              disabled
            />
          </div>
        </div>

        <div className="governance-banner">
          <strong>Credential handling</strong>
          <span>
            Secret-bearing fields are submitted only through the shipped connect endpoint and are not
            surfaced in account metadata reads.
          </span>
        </div>

        <div className="form-field">
          <label htmlFor="gmail-access-token">Access token</label>
          <input
            id="gmail-access-token"
            name="gmail-access-token"
            type="password"
            value={accessToken}
            onChange={(event) => setAccessToken(event.target.value)}
            placeholder="Enter Gmail OAuth access token"
            autoComplete="off"
            required
            disabled={!liveModeReady || isSubmitting}
          />
        </div>

        <div className="form-field-group form-field-group--two-up">
          <div className="form-field">
            <label htmlFor="gmail-refresh-token">Refresh token (optional bundle)</label>
            <input
              id="gmail-refresh-token"
              name="gmail-refresh-token"
              type="password"
              value={refreshToken}
              onChange={(event) => setRefreshToken(event.target.value)}
              placeholder="Required only when supplying full refresh bundle"
              autoComplete="off"
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
          <div className="form-field">
            <label htmlFor="gmail-access-token-expires-at">Access token expires at</label>
            <input
              id="gmail-access-token-expires-at"
              name="gmail-access-token-expires-at"
              type="datetime-local"
              value={accessTokenExpiresAt}
              onChange={(event) => setAccessTokenExpiresAt(event.target.value)}
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
        </div>

        <div className="form-field-group form-field-group--two-up">
          <div className="form-field">
            <label htmlFor="gmail-client-id">Client ID (optional bundle)</label>
            <input
              id="gmail-client-id"
              name="gmail-client-id"
              value={clientId}
              onChange={(event) => setClientId(event.target.value)}
              autoComplete="off"
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
          <div className="form-field">
            <label htmlFor="gmail-client-secret">Client secret (optional bundle)</label>
            <input
              id="gmail-client-secret"
              name="gmail-client-secret"
              type="password"
              value={clientSecret}
              onChange={(event) => setClientSecret(event.target.value)}
              autoComplete="off"
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
        </div>

        <div className="composer-actions">
          <div className="composer-status" aria-live="polite">
            <StatusBadge
              status={
                isSubmitting
                  ? "submitting"
                  : statusTone === "success"
                    ? "success"
                    : statusTone === "danger"
                      ? "error"
                      : liveModeReady
                        ? "info"
                        : "unavailable"
              }
              label={
                isSubmitting
                  ? "Connecting"
                  : statusTone === "success"
                    ? "Connected"
                    : statusTone === "danger"
                      ? "Attention"
                      : liveModeReady
                        ? "Ready"
                        : "Unavailable"
              }
            />
            <span>{statusText}</span>
          </div>
          <button type="submit" className="button" disabled={!canSubmit}>
            {isSubmitting ? "Connecting..." : "Connect Gmail account"}
          </button>
        </div>
      </form>
    </SectionCard>
  );
}
