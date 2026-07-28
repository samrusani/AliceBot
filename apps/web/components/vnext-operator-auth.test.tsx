/**
 * @vitest-environment jsdom
 * @vitest-environment-options {"url":"https://alice.example.com/vnext"}
 */

import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import VNextPage from "../app/vnext/page";
import { clearVNextOperatorAgentApiKey, requestJson } from "../lib/api";
import { VNextBrainWorkspace } from "./vnext-brain-workspace";

const EMPTY_LIVE_WORKSPACE = {
  mode: "live",
  summary: {
    source_count: 0,
    candidate_memory_count: 0,
    review_memory_count: 0,
    artifact_count: 0,
    open_loop_count: 0,
    project_count: 0,
    event_count: 0,
    memory_status_counts: {},
    artifact_status_counts: {},
    open_loop_status_counts: {},
  },
  sources: [],
  review_memories: [],
  artifacts: [],
  projects: [],
  project_dashboards: [],
  open_loops: [],
  people: [],
  beliefs: [],
  tasks: [],
  recent_events: [],
  brain_charter: null,
};

describe("VNextBrainWorkspace operator authentication", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    clearVNextOperatorAgentApiKey();
    window.localStorage.clear();
    window.sessionStorage.clear();
    fetchMock.mockReset();
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
    vi.unstubAllEnvs();
  });

  it.each([
    {
      label: "success",
      response: new Response(JSON.stringify(EMPTY_LIVE_WORKSPACE), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
      expectedStatus: "Live vNext workspace loaded.",
    },
    {
      label: "failure",
      response: new Response(JSON.stringify({ detail: "Workspace offline" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
      expectedStatus: "Unable to load live workspace: Workspace offline",
    },
  ])("starts one immediate live request and reaches the $label state", async ({ response, expectedStatus }) => {
    let resolveWorkspaceRequest: ((value: Response) => void) | undefined;
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveWorkspaceRequest = resolve;
        }),
    );

    render(
      <VNextBrainWorkspace
        apiBaseUrl="http://127.0.0.1:8000"
        userId="user-1"
        initialSource="live"
      />,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Loading live vNext workspace from the trusted API.")).toBeInTheDocument();
    expect(screen.queryByText("Refreshing live vNext workspace...")).not.toBeInTheDocument();

    resolveWorkspaceRequest?.(response);
    expect((await screen.findAllByText(expectedStatus)).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("loads the remote same-origin page with the entered key without forwarding it to an evil origin", async () => {
    const agentApiKey = "alice_sk_remote_operator_secret";
    vi.stubEnv("NEXT_PUBLIC_ALICEBOT_API_BASE_URL", "https://alice.example.com");
    vi.stubEnv("NEXT_PUBLIC_ALICEBOT_USER_ID", "user-1");
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const authorization = new Headers(init?.headers).get("Authorization");
      if (url.startsWith("https://alice.example.com/") && authorization === `Bearer ${agentApiKey}`) {
        return Promise.resolve(
          new Response(JSON.stringify(EMPTY_LIVE_WORKSPACE), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: "Authentication required" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    render(await VNextPage({}));

    expect(screen.getByText("Live default")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const input = screen.getByLabelText("Unbound admin_agent API key");
    fireEvent.change(input, { target: { value: agentApiKey } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Use key for this session" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Use key for this session" }));

    await waitFor(() =>
      expect(
        screen.getAllByText("Live vNext workspace loaded with operator authentication.").length,
      ).toBeGreaterThan(0),
    );
    const [liveUrl, liveInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(liveUrl).toBe("https://alice.example.com/v0/vnext/workspace?user_id=user-1");
    expect(new Headers(liveInit.headers).get("Authorization")).toBe(`Bearer ${agentApiKey}`);

    await requestJson("https://evil.example", "/v0/vnext/workspace").catch(() => null);
    const [evilUrl, evilInit] = fetchMock.mock.calls[2] as [string, RequestInit];
    expect(evilUrl).toBe("https://evil.example/v0/vnext/workspace");
    expect(new Headers(evilInit.headers).get("Authorization")).toBeNull();
    expect(fetchMock.mock.calls.map(([url]) => String(url)).join(" ")).not.toContain(agentApiKey);
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

  it("copies a capability bookmarklet without rendering or persisting the capability", async () => {
    const capability = "alice_clip_one_time_ui_secret";
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/v0/vnext/connectors/browser-clipper/capabilities")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              status: "issued",
              capability,
              origin: "https://example.com",
              expires_at: "2026-07-21T12:02:00Z",
              one_time: true,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: "Authentication required" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    render(
      <VNextBrainWorkspace
        apiBaseUrl="http://127.0.0.1:8000"
        userId="user-1"
        initialSource="live"
      />,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    fireEvent.change(screen.getByLabelText("Connector"), {
      target: { value: "browser_clipper" },
    });
    fireEvent.change(screen.getByLabelText("Page URL"), {
      target: { value: "https://example.com/article" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Issue and copy one-time bookmarklet" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const copiedBookmarklet = String(writeText.mock.calls[0]?.[0]);
    expect(copiedBookmarklet).toContain(capability);
    expect(copiedBookmarklet).not.toContain("capture_token");
    expect(copiedBookmarklet).not.toContain("Authorization");

    const capabilityCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/v0/vnext/connectors/browser-clipper/capabilities"),
    ) as [string, RequestInit] | undefined;
    expect(capabilityCall).toBeDefined();
    expect(capabilityCall?.[0]).not.toContain(capability);
    expect(JSON.parse(String(capabilityCall?.[1].body))).toEqual({
      user_id: "user-1",
      origin: "https://example.com",
    });
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(window.location.href).not.toContain(capability);
    expect(document.documentElement.outerHTML).not.toContain(capability);
    const preparedPattern = /Prepared for https:\/\/example.com/;
    expect(screen.getByText(preparedPattern)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Selected text"), {
      target: { value: "Fact: Editing clip content does not invalidate the bound capability." },
    });
    expect(screen.getByText(preparedPattern)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Page URL"), {
      target: { value: "https://example.com/changed" },
    });
    expect(screen.queryByText(preparedPattern)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Page URL"), {
      target: { value: "https://example.com/article" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Issue and copy one-time bookmarklet" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(2));
    expect(screen.getByText(preparedPattern)).toBeInTheDocument();

    fireEvent.change(
      screen.getByLabelText("Default domain", { selector: "#vnext-connector-domain" }),
      { target: { value: "personal" } },
    );
    expect(screen.queryByText(preparedPattern)).not.toBeInTheDocument();

    fireEvent.change(
      screen.getByLabelText("Default domain", { selector: "#vnext-connector-domain" }),
      { target: { value: "professional" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Issue and copy one-time bookmarklet" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(3));
    expect(screen.getByText(preparedPattern)).toBeInTheDocument();

    fireEvent.change(
      screen.getByLabelText("Default sensitivity", {
        selector: "#vnext-connector-sensitivity",
      }),
      { target: { value: "confidential" } },
    );
    expect(screen.queryByText(preparedPattern)).not.toBeInTheDocument();
  });
});
