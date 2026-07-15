import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearVNextOperatorAgentApiKey } from "../lib/api";
import { VNextBrainWorkspace } from "./vnext-brain-workspace";

describe("VNextBrainWorkspace Telegram boundary", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    clearVNextOperatorAgentApiKey();
    fetchMock.mockReset();
    fetchMock.mockImplementation((_url: string, init?: RequestInit) => {
      if (init?.method === "PATCH") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              connector_name: "telegram",
              enabled: true,
              configured: true,
              default_domain: "personal",
              default_sensitivity: "private",
              sync_mode: "on_demand",
              config_json: { allowed_chat_ids: ["999001"] },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: "Fixture-free test response" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    cleanup();
    clearVNextOperatorAgentApiKey();
    vi.unstubAllGlobals();
  });

  it("saves only the Telegram allowlist and exposes no secret or polling action", async () => {
    render(
      <VNextBrainWorkspace
        apiBaseUrl="http://127.0.0.1:8000"
        userId="user-1"
        initialSource="live"
      />,
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByRole("button", { name: "Save connector settings" })).toBeEnabled());

    expect(screen.getByLabelText("Connector")).toHaveValue("telegram");
    expect(screen.queryByLabelText("Secret ref")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Run sync now" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Allowed chat IDs"), {
      target: { value: "999001, 999002" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save connector settings" }));

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([, init]) => (init as RequestInit | undefined)?.method === "PATCH"),
      ).toBe(true),
    );
    const [, patchInit] = fetchMock.mock.calls.find(
      ([, init]) => (init as RequestInit | undefined)?.method === "PATCH",
    ) as [string, RequestInit];
    const body = JSON.parse(String(patchInit.body));
    expect(body).toEqual({
      user_id: "user-1",
      enabled: false,
      default_domain: "personal",
      default_sensitivity: "private",
      config_json: { allowed_chat_ids: ["999001", "999002"] },
    });
    expect(body).not.toHaveProperty("secret_ref");
    expect(body).not.toHaveProperty("sync_mode");
    expect(body).not.toHaveProperty("poll_interval_seconds");
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/connectors/telegram/sync")),
    ).toHaveLength(0);
  });
});
