import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearVNextOperatorAgentApiKey, requestJson } from "../lib/api";
import { VNextBrainWorkspace } from "./vnext-brain-workspace";

describe("VNextBrainWorkspace operator authentication", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    clearVNextOperatorAgentApiKey();
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: "Authentication required" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  afterEach(() => {
    cleanup();
    clearVNextOperatorAgentApiKey();
    vi.unstubAllGlobals();
  });

  it("holds an admin key only for the mounted local console session", async () => {
    const agentApiKey = "alice_sk_operator_ui_secret";
    const { unmount } = render(
      <VNextBrainWorkspace
        apiBaseUrl="http://127.0.0.1:8000"
        userId="user-1"
        initialSource="live"
      />,
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    const input = screen.getByLabelText("Unbound admin_agent API key");
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autocomplete", "off");

    fireEvent.change(input, { target: { value: agentApiKey } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Use key for this session" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Use key for this session" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [, authenticatedInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(new Headers(authenticatedInit.headers).get("Authorization")).toBe(
      `Bearer ${agentApiKey}`,
    );
    expect(input).toHaveValue("");
    expect(screen.getByText("Key held in memory")).toBeInTheDocument();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(window.location.href).not.toContain(agentApiKey);
    expect(document.documentElement.outerHTML).not.toContain(agentApiKey);

    fireEvent.click(screen.getByRole("button", { name: "Clear session key" }));
    expect(input).toHaveValue("");
    expect(screen.getByText("No session key")).toBeInTheDocument();

    await requestJson("http://127.0.0.1:8000", "/v0/vnext/workspace").catch(() => null);
    const [, clearedInit] = fetchMock.mock.calls[2] as [string, RequestInit];
    expect(new Headers(clearedInit.headers).get("Authorization")).toBeNull();

    fireEvent.change(input, { target: { value: agentApiKey } });
    fireEvent.click(screen.getByRole("button", { name: "Use key for this session" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    unmount();

    await requestJson("http://127.0.0.1:8000", "/v0/vnext/workspace").catch(() => null);
    const [, unmountedInit] = fetchMock.mock.calls[4] as [string, RequestInit];
    expect(new Headers(unmountedInit.headers).get("Authorization")).toBeNull();
  });
});
