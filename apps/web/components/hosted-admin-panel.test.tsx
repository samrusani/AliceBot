import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HostedAdminPanel } from "./hosted-admin-panel";

describe("HostedAdminPanel", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders hosted admin scope and OSS-versus-hosted boundary copy", () => {
    render(<HostedAdminPanel />);

    expect(screen.getByText("Hosted Beta Operations")).toBeInTheDocument();
    expect(screen.getByText(/alice connect hosted beta operations/i)).toBeInTheDocument();
    expect(screen.getByText(/alice core oss runtime/i)).toBeInTheDocument();
    expect(screen.getByText("Flag Posture")).toBeInTheDocument();
  });

  it("rejects insecure non-loopback hosted API configuration", () => {
    render(<HostedAdminPanel apiBaseUrl="http://api.example.com" />);

    expect(screen.getByRole("button", { name: "Load admin datasets" })).toBeDisabled();
    expect(screen.getByText(/require HTTPS for remote APIs/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects and does not render credential-bearing hosted API configuration", () => {
    const { container } = render(
      <HostedAdminPanel apiBaseUrl="https://user:secret@api.example.com?token=secret#trace" />,
    );

    expect(screen.getByRole("button", { name: "Load admin datasets" })).toBeDisabled();
    expect(container.textContent).not.toContain("user:secret");
    expect(container.textContent).not.toContain("token=secret");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("loads hosted admin datasets with bearer auth", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ window_hours: 24, workspaces: { total_count: 1, ready_count: 1, pending_count: 0, linked_telegram_workspace_count: 1 }, delivery_receipts: { total_count: 2, failed_count: 0, suppressed_count: 0 }, chat_telemetry: { total_count: 3, failed_count: 0, rollout_blocked_count: 0, rate_limited_count: 0, abuse_blocked_count: 0 }, incidents: { open_count: 0 } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{}] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{}, {}] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{ flag_key: "hosted_chat_handle_enabled", enabled: true, source_scope: "cohort" }] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ analytics: { total_events: 3 } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ summary: {}, items: [] })));

    render(<HostedAdminPanel apiBaseUrl="https://api.example.com" />);

    fireEvent.change(screen.getByLabelText(/Hosted session token/i), {
      target: { value: "admin-session-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load admin datasets" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(7);
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/v1/admin/hosted/overview");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer admin-session-token");
    expect(await screen.findByText("Hosted admin datasets loaded.")).toBeInTheDocument();
    expect(await screen.findByText("hosted_chat_handle_enabled")).toBeInTheDocument();
  });

  it("shows the exact overview rate-limit count instead of the bounded mixed event list", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ window_hours: 24, workspaces: { total_count: 1, ready_count: 1, pending_count: 0, linked_telegram_workspace_count: 1 }, delivery_receipts: { total_count: 2, failed_count: 0, suppressed_count: 0 }, chat_telemetry: { total_count: 12, failed_count: 0, rollout_blocked_count: 0, rate_limited_count: 7, abuse_blocked_count: 4 }, incidents: { open_count: 0 } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{}] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{}, {}] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ analytics: { total_events: 12 } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ summary: { chat_handle: { rate_limited: 7, abuse_blocked: 4 } }, items: [{ status: "abuse_blocked" }] })));

    render(<HostedAdminPanel apiBaseUrl="https://api.example.com" />);
    fireEvent.change(screen.getByLabelText(/Hosted session token/i), {
      target: { value: "admin-session-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load admin datasets" }));

    await screen.findByText("Hosted admin datasets loaded.");
    expect(screen.getByText("Rate-limit events").nextElementSibling).toHaveTextContent("7");
  });

  it("sums only rate-limited events from the fallback summary", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ overview: null })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{}] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ analytics: { total_events: 8 } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ summary: { chat_handle: { rate_limited: 2, abuse_blocked: 6 }, scheduler: { rate_limited: 3 } }, items: [{}, {}, {}, {}, {}, {}, {}, {}] })));

    render(<HostedAdminPanel apiBaseUrl="https://api.example.com" />);
    fireEvent.change(screen.getByLabelText(/Hosted session token/i), {
      target: { value: "admin-session-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load admin datasets" }));

    await screen.findByText("Hosted admin datasets loaded.");
    expect(screen.getByText("Rate-limit events").nextElementSibling).toHaveTextContent("5");
  });
});
