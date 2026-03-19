"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { useRouter } from "next/navigation";

import { connectCalendarAccount } from "../lib/api";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type CalendarAccountConnectFormProps = {
  apiBaseUrl?: string;
  userId?: string;
};

const CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly" as const;

export function CalendarAccountConnectForm({
  apiBaseUrl,
  userId,
}: CalendarAccountConnectFormProps) {
  const router = useRouter();
  const liveModeReady = Boolean(apiBaseUrl && userId);

  const [providerAccountId, setProviderAccountId] = useState("");
  const [emailAddress, setEmailAddress] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [accessToken, setAccessToken] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    liveModeReady
      ? "Enter one account at a time, including the secret-bearing access token, then connect."
      : "Calendar connect is unavailable until live API configuration is present.",
  );

  const canSubmit = liveModeReady && !isSubmitting;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!apiBaseUrl || !userId) {
      setStatusTone("info");
      setStatusText("Calendar connect is unavailable until live API configuration is present.");
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Connecting Calendar account...");

    try {
      const payload = await connectCalendarAccount(apiBaseUrl, {
        user_id: userId,
        provider_account_id: providerAccountId.trim(),
        email_address: emailAddress.trim(),
        display_name: displayName.trim() ? displayName.trim() : null,
        scope: CALENDAR_READONLY_SCOPE,
        access_token: accessToken.trim(),
      });

      setStatusTone("success");
      setStatusText(`Connected ${payload.account.email_address}.`);
      setAccessToken("");
      router.push(`/calendar?account=${encodeURIComponent(payload.account.id)}`);
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
      title="Add Calendar account"
      description="Connection is explicit and bounded to the shipped read-only scope with one secret-bearing credential field."
    >
      <form className="detail-stack" onSubmit={handleSubmit}>
        <div className="form-field-group form-field-group--two-up">
          <div className="form-field">
            <label htmlFor="calendar-provider-account-id">Provider account ID</label>
            <input
              id="calendar-provider-account-id"
              name="calendar-provider-account-id"
              value={providerAccountId}
              onChange={(event) => setProviderAccountId(event.target.value)}
              placeholder="acct-owner-001"
              required
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
          <div className="form-field">
            <label htmlFor="calendar-email-address">Email address</label>
            <input
              id="calendar-email-address"
              name="calendar-email-address"
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
            <label htmlFor="calendar-display-name">Display name (optional)</label>
            <input
              id="calendar-display-name"
              name="calendar-display-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Owner"
              disabled={!liveModeReady || isSubmitting}
            />
          </div>
          <div className="form-field">
            <label htmlFor="calendar-scope">Scope</label>
            <input
              id="calendar-scope"
              name="calendar-scope"
              value={CALENDAR_READONLY_SCOPE}
              readOnly
              className="mono"
              disabled
            />
          </div>
        </div>

        <div className="governance-banner">
          <strong>Credential handling</strong>
          <span>
            The access token is submitted only through the shipped connect endpoint and is not
            surfaced in account metadata reads.
          </span>
        </div>

        <div className="form-field">
          <label htmlFor="calendar-access-token">Access token</label>
          <input
            id="calendar-access-token"
            name="calendar-access-token"
            type="password"
            value={accessToken}
            onChange={(event) => setAccessToken(event.target.value)}
            placeholder="Enter Google Calendar OAuth access token"
            autoComplete="off"
            required
            disabled={!liveModeReady || isSubmitting}
          />
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
                  ? "Submitting"
                  : statusTone === "success"
                    ? "Connected"
                    : statusTone === "danger"
                      ? "Error"
                      : liveModeReady
                        ? "Ready"
                        : "Unavailable"
              }
            />
            <span>{statusText}</span>
          </div>

          <button type="submit" className="button" disabled={!canSubmit}>
            Connect Calendar account
          </button>
        </div>
      </form>
    </SectionCard>
  );
}
