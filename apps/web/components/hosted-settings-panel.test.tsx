import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HostedSettingsPanel } from "./hosted-settings-panel";

describe("HostedSettingsPanel", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows telegram link, status, and receipt controls without continuity claims", () => {
    render(<HostedSettingsPanel />);

    expect(screen.getByText("Telegram Channel Settings")).toBeInTheDocument();
    expect(screen.getByText(/Telegram Link Start/i)).toBeInTheDocument();
    expect(screen.getByText(/Daily Brief \+ Notification Preferences/i)).toBeInTheDocument();
    expect(screen.getByText(/Open-Loop Prompts \+ Scheduler/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Messages, Threads, Receipts/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/does not claim beta admin dashboards/i)).toBeInTheDocument();
  });

  it("rejects insecure non-loopback hosted API configuration", () => {
    render(<HostedSettingsPanel apiBaseUrl="http://api.example.com" />);

    expect(screen.getByRole("button", { name: "Start Telegram link" })).toBeDisabled();
    expect(screen.getByText(/require HTTPS for remote APIs/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("starts telegram link challenge from hosted controls", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          challenge: {
            challenge_token: "telegram-test-challenge-token",
            link_code: "CODE2026",
            status: "pending",
            expires_at: "2026-04-08T18:45:00Z",
          },
          instructions: {
            bot_username: "alicebot",
            command: "/link CODE2026",
          },
        }),
      ),
    );

    render(
      <HostedSettingsPanel apiBaseUrl="https://api.example.com?token=secret#fragment" />,
    );

    fireEvent.change(screen.getByLabelText(/Hosted session token/i), {
      target: { value: "session-token-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start Telegram link" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/v1/channels/telegram/link/start");
    expect(url).not.toContain("token=secret");
    expect(url).not.toContain("#fragment");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer session-token-123");
    expect(screen.getAllByText(/\/link CODE2026/).length).toBeGreaterThan(0);
  });

  it("threads the entered workspace through every hosted settings read", async () => {
    const notificationPreferences = {
      notifications_enabled: true,
      daily_brief_enabled: true,
      daily_brief_window_start: "07:00",
      open_loop_prompts_enabled: true,
      waiting_for_prompts_enabled: true,
      stale_prompts_enabled: true,
      timezone: "UTC",
      quiet_hours: { enabled: false, start: "22:00", end: "07:00" },
    };
    fetchMock.mockImplementation(async (input: string | URL | Request) => {
      const pathname = new URL(input instanceof Request ? input.url : input.toString()).pathname;
      if (pathname.endsWith("/notification-preferences")) {
        return new Response(JSON.stringify({ notification_preferences: notificationPreferences }));
      }
      if (pathname.endsWith("/daily-brief")) {
        return new Response(
          JSON.stringify({
            preview_message_text: "Daily brief",
            delivery_policy: { allowed: true, suppression_status: null, reason: "allowed" },
            brief: {
              assembly_version: "v1",
              waiting_for_highlights: { summary: { total_count: 0 } },
              blocker_highlights: { summary: { total_count: 0 } },
              stale_items: { summary: { total_count: 0 } },
            },
          }),
        );
      }
      return new Response(JSON.stringify({ items: [] }));
    });

    render(<HostedSettingsPanel apiBaseUrl="https://api.example.com" />);
    fireEvent.change(screen.getByLabelText(/Hosted session token/i), {
      target: { value: "session-token-reads" },
    });
    fireEvent.change(screen.getByLabelText(/Workspace ID/i), {
      target: { value: "11111111-1111-4111-8111-111111111111" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Refresh transport records" }));
    expect(await screen.findByText("Loaded latest Telegram messages, threads, and delivery receipts.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load notification posture" }));
    expect(await screen.findByText("Loaded Telegram notification preference posture.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview daily brief" }));
    expect(await screen.findByText("Loaded current daily brief preview and delivery policy.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load open-loop prompts" }));
    expect(await screen.findByText("Loaded scheduled waiting-for and stale open-loop prompts.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load scheduler jobs" }));
    expect(await screen.findByText("Loaded Telegram scheduler job posture.")).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledTimes(7);
    for (const [input] of fetchMock.mock.calls as [[string | URL | Request]][]) {
      const url = new URL(input instanceof Request ? input.url : input.toString());
      expect(url.searchParams.get("workspace_id")).toBe("11111111-1111-4111-8111-111111111111");
    }
  });

  it("threads the entered workspace through notification and delivery mutations", async () => {
    const workspaceId = "22222222-2222-4222-8222-222222222222";
    const notificationPreferences = {
      notifications_enabled: true,
      daily_brief_enabled: true,
      daily_brief_window_start: "07:00",
      open_loop_prompts_enabled: true,
      waiting_for_prompts_enabled: true,
      stale_prompts_enabled: true,
      timezone: "UTC",
      quiet_hours: { enabled: false, start: "22:00", end: "07:00" },
    };
    let promptListReads = 0;
    fetchMock.mockImplementation(async (input: string | URL | Request, init?: RequestInit) => {
      const url = new URL(input instanceof Request ? input.url : input.toString());
      const method = init?.method ?? "GET";
      if (url.pathname.endsWith("/notification-preferences") && method === "PATCH") {
        return new Response(JSON.stringify({ notification_preferences: notificationPreferences }));
      }
      if (url.pathname.endsWith("/daily-brief/deliver")) {
        return new Response(JSON.stringify({ job: { id: "job-1" }, idempotent_replay: false }));
      }
      if (url.pathname.endsWith("/scheduler/jobs")) {
        return new Response(JSON.stringify({ items: [] }));
      }
      if (url.pathname.endsWith("/open-loop-prompts")) {
        promptListReads += 1;
        return new Response(
          JSON.stringify({
            items: promptListReads === 1
              ? [{
                  prompt_id: "prompt-1",
                  prompt_kind: "stale",
                  title: "Follow up",
                  latest_job_status: null,
                  already_delivered_today: false,
                }]
              : [],
          }),
        );
      }
      if (url.pathname.endsWith("/open-loop-prompts/prompt-1/deliver")) {
        return new Response(JSON.stringify({ idempotent_replay: false }));
      }
      throw new Error(`Unexpected request: ${method} ${url.pathname}`);
    });

    render(<HostedSettingsPanel apiBaseUrl="https://api.example.com" />);
    fireEvent.change(screen.getByLabelText(/Hosted session token/i), {
      target: { value: "session-token-mutations" },
    });
    fireEvent.change(screen.getByLabelText(/Workspace ID/i), { target: { value: workspaceId } });

    fireEvent.click(screen.getByRole("button", { name: "Enable daily loop" }));
    expect(await screen.findByText("Enabled daily brief + open-loop prompt delivery for Telegram.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Deliver daily brief" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Deliver daily brief" })).not.toBeDisabled());
    fireEvent.click(screen.getByRole("button", { name: "Load open-loop prompts" }));
    expect(await screen.findByText(/Follow up/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Deliver" }));
    await waitFor(() => expect(screen.getByText("Prompt delivery job recorded for Telegram.")).toBeInTheDocument());

    const mutationCalls = (fetchMock.mock.calls as [string | URL | Request, RequestInit | undefined][])
      .filter(([, init]) => (init?.method ?? "GET") !== "GET");
    expect(mutationCalls).toHaveLength(3);
    for (const [input] of mutationCalls) {
      const url = new URL(input instanceof Request ? input.url : input.toString());
      expect(url.searchParams.get("workspace_id")).toBe(workspaceId);
    }
  });
});
