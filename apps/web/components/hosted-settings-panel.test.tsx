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

    render(<HostedSettingsPanel apiBaseUrl="https://api.example.com" />);

    fireEvent.change(screen.getByLabelText(/Hosted session token/i), {
      target: { value: "session-token-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start Telegram link" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/v1/channels/telegram/link/start");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer session-token-123");
    expect(screen.getAllByText(/\/link CODE2026/).length).toBeGreaterThan(0);
  });
});
