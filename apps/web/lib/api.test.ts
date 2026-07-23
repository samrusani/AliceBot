import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  admitMemory,
  ApiError,
  buildApiUrl,
  combinePageModes,
  connectCalendarAccount,
  connectGmailAccount,
  createContinuityCapture,
  captureVNextBrowserClip,
  confirmVNextMemory,
  applyContinuityCorrection,
  createVNextContextPack,
  createVNextOpenLoop,
  createVNextProject,
  createVNextSource,
  createOpenLoop,
  generateVNextDailyBrief,
  generateVNextProjectUpdate,
  generateVNextWeeklySynthesis,
  getCalendarAccountDetail,
  getApiConfig,
  getGmailAccountDetail,
  getOpenLoopDetail,
  getTaskArtifactDetail,
  getEntityDetail,
  getContinuityCaptureDetail,
  getContinuityReviewDetail,
  getContinuityOpenLoopDashboard,
  getContinuityDailyBrief,
  getContinuityWeeklyReview,
  getMemoryDetail,
  getMemoryEvaluationSummary,
  getMemoryTrustDashboard,
  getMemoryRevisions,
  getTaskSteps,
  getVNextBrainCharter,
  getVNextConnectorsHealth,
  getVNextDogfoodingDashboard,
  getVNextArtifactTrace,
  getVNextPolicyTelemetry,
  getVNextQualityEvals,
  getVNextSchedulerFailures,
  getVNextSourceTrace,
  getVNextWorkspace,
  getContinuityResumptionBrief,
  clearVNextOperatorAgentApiKey,
  executeApproval,
  ingestCalendarEvent,
  ingestGmailMessage,
  listCalendarAccounts,
  listCalendarEvents,
  listContinuityCaptures,
  listContinuityReviewQueue,
  listEntities,
  listEntityEdges,
  listGmailAccounts,
  listOpenLoops,
  listTaskArtifactChunks,
  listTaskArtifacts,
  listTaskWorkspaces,
  listMemories,
  listMemoryLabels,
  listMemoryReviewQueue,
  listTaskRuns,
  getToolExecution,
  getTraceDetail,
  getTraceEvents,
  listTraces,
  queryContinuityRecall,
  getContinuityRetrievalEvaluation,
  hasLiveApiConfig,
  isLocalApiBaseUrl,
  issueVNextBrowserClipCapability,
  requestJson,
  sanitizeApiBaseUrl,
  sanitizePublicErrorText,
  setVNextOperatorAgentApiKey,
  pageModeLabel,
  rateVNextArtifactQuality,
  recordVNextArtifactInsightFeedback,
  resolveApproval,
  reviewVNextArtifact,
  reviewVNextMemory,
  reviewVNextOpenLoop,
  reviewVNextSource,
  runVNextDoctor,
  runVNextSchedulerDue,
  runVNextSchedulerWorkflowNow,
  extractExplicitCommitments,
  applyContinuityOpenLoopReviewAction,
  submitMemoryLabel,
  syncVNextTelegramConnector,
  updateOpenLoopStatus,
  updateVNextConnectorConfig,
  updateVNextTelegramConnectorConfig,
  upsertVNextBrainCharter,
} from "./api";

describe("api helpers", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    clearVNextOperatorAgentApiKey();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("combines live and fixture sources into a mixed page mode", () => {
    expect(combinePageModes("live", "fixture")).toBe("mixed");
    expect(pageModeLabel("mixed")).toBe("Mixed fallback");
  });

  it("allows live console reads only on loopback or the exact browser HTTPS origin", () => {
    expect(isLocalApiBaseUrl("http://127.0.0.1:8000")).toBe(true);
    expect(isLocalApiBaseUrl("https://[::1]:8443")).toBe(true);
    expect(isLocalApiBaseUrl("ftp://localhost:8000")).toBe(false);
    expect(isLocalApiBaseUrl("https://api.example.com")).toBe(false);
    expect(
      hasLiveApiConfig({
        apiBaseUrl: "http://localhost:8000",
        userId: "user-1",
      }),
    ).toBe(true);

    vi.stubGlobal("window", { location: { origin: "https://alice.example.com" } });
    expect(
      hasLiveApiConfig({
        apiBaseUrl: "https://alice.example.com",
        userId: "user-1",
      }),
    ).toBe(true);
    expect(
      hasLiveApiConfig({
        apiBaseUrl: "https://evil.example",
        userId: "user-1",
      }),
    ).toBe(false);
    expect(
      hasLiveApiConfig({
        apiBaseUrl: "http://alice.example.com",
        userId: "user-1",
      }),
    ).toBe(false);
    expect(
      hasLiveApiConfig({
        apiBaseUrl: "https://alice.example.com/api",
        userId: "user-1",
      }),
    ).toBe(false);
    expect(
      hasLiveApiConfig({
        apiBaseUrl: "https://user:secret@alice.example.com",
        userId: "user-1",
      }),
    ).toBe(false);
  });

  it("uses the exact PUBLIC_ORIGIN for server-rendered live mode", () => {
    vi.stubGlobal("window", undefined);
    vi.stubEnv("PUBLIC_ORIGIN", "https://alice.example.com");

    expect(
      hasLiveApiConfig({
        apiBaseUrl: "https://alice.example.com",
        userId: "user-1",
      }),
    ).toBe(true);
    expect(
      hasLiveApiConfig({
        apiBaseUrl: "https://evil.example",
        userId: "user-1",
      }),
    ).toBe(false);
  });

  it("keeps Telegram configuration on-demand and strips the retired secret and polling contract", async () => {
    fetchMock.mockResolvedValue(
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

    await updateVNextTelegramConnectorConfig("https://api.example.com", {
      user_id: "user-1",
      enabled: true,
      default_domain: "personal",
      default_sensitivity: "private",
      config_json: { allowed_chat_ids: ["999001"] },
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(String(init.body));
    expect(url).toBe("https://api.example.com/v0/vnext/connectors/telegram/config");
    expect(init.method).toBe("PATCH");
    expect(body).toEqual({
      user_id: "user-1",
      enabled: true,
      default_domain: "personal",
      default_sensitivity: "private",
      config_json: { allowed_chat_ids: ["999001"] },
    });
    expect(body).not.toHaveProperty("secret_ref");
    expect(body).not.toHaveProperty("sync_mode");
    expect(body).not.toHaveProperty("poll_interval_seconds");
    expect(() =>
      updateVNextConnectorConfig("https://api.example.com", "telegram", {
        user_id: "user-1",
        secret_ref: "retired.telegram.token",
        sync_mode: "polling",
        poll_interval_seconds: 60,
      }),
    ).toThrow(/on-demand/);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fetchMock.mockClear();
    expect(() =>
      updateVNextTelegramConnectorConfig("https://api.example.com", {
        user_id: "user-1",
        config_json: { allowed_chat_ids: [] },
      }),
    ).toThrow(/explicit chat allowlist/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends Telegram ingestion only with caller-supplied updates and an explicit allowlist", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const update = { update_id: 17, message: { chat: { id: 999001 }, text: "Release note" } };

    await syncVNextTelegramConnector("https://api.example.com", {
      user_id: "user-1",
      updates: [update],
      allowed_chat_ids: ["999001"],
      default_domain: "project",
      default_sensitivity: "private",
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://api.example.com/v0/vnext/connectors/telegram/sync");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      user_id: "user-1",
      updates: [update],
      allowed_chat_ids: ["999001"],
      default_domain: "project",
      default_sensitivity: "private",
    });

    fetchMock.mockClear();
    expect(() =>
      syncVNextTelegramConnector("https://api.example.com", {
        user_id: "user-1",
        updates: [],
        allowed_chat_ids: [],
      } as never),
    ).toThrow(/supplied updates and an explicit chat allowlist/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sanitizes configured API URLs and public error text", () => {
    expect(sanitizeApiBaseUrl("https://api.example.com/root?token=secret#fragment")).toBe(
      "https://api.example.com/root",
    );
    expect(sanitizeApiBaseUrl("https://user:secret@api.example.com/root?token=secret")).toBe("");
    expect(
      sanitizePublicErrorText(
        "Failed at https://user:secret@api.example.com/root?token=secret#fragment",
      ),
    ).toBe("Failed at https://api.example.com/root");
  });

  it("sanitizes the configured API base URL before returning browser config", () => {
    vi.stubEnv(
      "NEXT_PUBLIC_ALICEBOT_API_BASE_URL",
      "https://api.example.com/root?token=secret#fragment",
    );
    expect(getApiConfig().apiBaseUrl).toBe("https://api.example.com/root");

    vi.stubEnv(
      "NEXT_PUBLIC_ALICEBOT_API_BASE_URL",
      "https://user:secret@api.example.com/root?token=secret#fragment",
    );
    expect(getApiConfig().apiBaseUrl).toBe("");
  });

  it("preserves configured API base paths when joining logical API routes", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await requestJson(
      "https://api.example.com/root?token=discarded#fragment",
      "/v0/threads",
      undefined,
      { user_id: "user-1" },
    );
    await requestJson("https://api.example.com/root/", "/v0/threads");
    await requestJson("https://api.example.com", "/v0/threads");

    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      "https://api.example.com/root/v0/threads?user_id=user-1",
      "https://api.example.com/root/v0/threads",
      "https://api.example.com/v0/threads",
    ]);
    expect(
      buildApiUrl(
        "https://api.example.com/root",
        "/v0/vnext/connectors/browser-clipper/capture",
      ),
    ).toBe(
      "https://api.example.com/root/v0/vnext/connectors/browser-clipper/capture",
    );
  });

  it("issues browser-clip capabilities through the trusted vNext client without URL leakage", async () => {
    const response = {
      status: "issued" as const,
      capability: "alice_clip_one_time_secret",
      origin: "https://example.com",
      expires_at: "2026-07-21T12:02:00Z",
      one_time: true as const,
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      issueVNextBrowserClipCapability("http://127.0.0.1:8000", {
        user_id: "user-1",
        origin: "https://example.com",
      }),
    ).resolves.toEqual(response);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://127.0.0.1:8000/v0/vnext/connectors/browser-clipper/capabilities");
    expect(url).not.toContain(response.capability);
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      user_id: "user-1",
      origin: "https://example.com",
    });
  });

  it("attaches the in-memory operator key only to trusted vNext routes", async () => {
    const agentApiKey = "alice_sk_operator_session_secret";
    vi.stubGlobal("window", { location: { origin: "https://alice.example.com" } });
    setVNextOperatorAgentApiKey(agentApiKey);
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await requestJson("http://127.0.0.1:8000", "/v0/vnext");
    await requestJson("https://localhost:8443", "/v0/vnext/workspace");
    await requestJson("https://alice.example.com", "/v0/vnext/workspace");
    await requestJson("https://evil.example", "/v0/vnext/workspace");
    await requestJson("http://alice.example.com", "/v0/vnext/workspace");
    await requestJson("https://alice.example.com/api", "/v0/vnext/workspace");
    await requestJson("http://127.0.0.1:8000", "/v0/threads");
    await requestJson("http://127.0.0.1:8000", "/v1/providers");
    await requestJson("http://127.0.0.1:8000", "/v0/vnextish/workspace");
    await requestJson("http://127.0.0.1:8000/alice", "/v0/vnext/workspace");

    const authorizationHeaders = fetchMock.mock.calls.map(([, init]) =>
      new Headers((init as RequestInit).headers).get("Authorization"),
    );
    expect(authorizationHeaders).toEqual([
      `Bearer ${agentApiKey}`,
      `Bearer ${agentApiKey}`,
      `Bearer ${agentApiKey}`,
      null,
      null,
      null,
      null,
      null,
      null,
      `Bearer ${agentApiKey}`,
    ]);
    expect(fetchMock.mock.calls.at(-1)?.[0]).toBe(
      "http://127.0.0.1:8000/alice/v0/vnext/workspace",
    );
    expect(fetchMock.mock.calls.map(([url]) => String(url)).join(" ")).not.toContain(agentApiKey);
  });

  it("keeps explicit Authorization headers authoritative over the in-memory operator key", async () => {
    vi.stubGlobal("window", { location: { origin: "https://alice.example.com" } });
    setVNextOperatorAgentApiKey("alice_sk_operator_session_secret");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await requestJson("https://alice.example.com", "/v0/vnext/workspace", {
      headers: { Authorization: "Bearer explicit-session-token" },
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("Authorization")).toBe(
      "Bearer explicit-session-token",
    );
  });

  it("redacts an active operator key if a backend echoes it in an error envelope", async () => {
    const agentApiKey = "alice_sk_operator_session_secret";
    setVNextOperatorAgentApiKey(agentApiKey);
    fetchMock.mockImplementation(() => {
      clearVNextOperatorAgentApiKey();
      return Promise.resolve(
        new Response(
          JSON.stringify({
            detail: {
              message: `Rejected credential ${agentApiKey}`,
              code: agentApiKey,
              echoed_fields: {
                [agentApiKey]: "secret-named field",
                "[redacted agent key]": "pre-existing redacted field",
              },
            },
          }),
          { status: 401, headers: { "Content-Type": "application/json" } },
        ),
      );
    });

    const error = await requestJson("http://127.0.0.1:8000", "/v0/vnext/workspace").catch(
      (value) => value,
    );
    expect(error).toBeInstanceOf(ApiError);
    if (!(error instanceof ApiError)) {
      throw new Error("Expected requestJson to reject with ApiError");
    }
    const serialized = JSON.stringify({
      message: error.message,
      code: error.code,
      detail: error.detail,
    });

    expect(error).toEqual(
      expect.objectContaining({
        message: "Rejected credential [redacted agent key]",
        code: "request_failed",
        detail: expect.objectContaining({
          echoed_fields: {
            "[redacted agent key]": "secret-named field",
            "[redacted agent key]#2": "pre-existing redacted field",
          },
        }),
      }),
    );
    expect(serialized).not.toContain(agentApiKey);
  });

  it("throws ApiError when approval resolution returns a backend error envelope", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "approval conflict" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      resolveApproval("https://api.example.com", "approval-1", "approve", "user-1"),
    ).rejects.toEqual(expect.objectContaining({ message: "approval conflict", status: 409 }));

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/approvals/approval-1/approve",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("preserves structured validation details in ApiError", async () => {
    const detail = [
      { loc: ["body", "title"], msg: "Field required", type: "missing" },
      { loc: ["body", "domain"], msg: "Invalid domain", type: "value_error" },
    ];
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail, code: "validation_failed" }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(listMemories("https://api.example.com", "user-1")).rejects.toEqual(
      expect.objectContaining({
        message: "Field required; Invalid domain",
        status: 422,
        code: "validation_failed",
        detail,
      }),
    );
  });

  it("normalizes object errors, sanitizes URLs, and preserves Retry-After", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "upstream_unavailable",
            message:
              "Upstream failed at https://user:secret@api.example.com/v0/run?token=secret#trace",
            diagnostic_url:
              "https://user:secret@api.example.com/debug?token=secret#trace",
          },
        }),
        {
          status: 429,
          headers: { "Content-Type": "application/json", "Retry-After": "7" },
        },
      ),
    );

    const error = await listMemories("https://api.example.com", "user-1").catch((value) => value);

    expect(error).toEqual(
      expect.objectContaining({
        message: "Upstream failed at https://api.example.com/v0/run",
        status: 429,
        code: "upstream_unavailable",
        retryAfterSeconds: 7,
        detail: {
          code: "upstream_unavailable",
          message: "Upstream failed at https://api.example.com/v0/run",
          diagnostic_url: "https://api.example.com/debug",
        },
      }),
    );
    const serialized = JSON.stringify({ message: error.message, detail: error.detail });
    expect(serialized).not.toContain("user:secret");
    expect(serialized).not.toContain("token=secret");
    expect(serialized).not.toContain("#trace");
  });

  it("normalizes transport failures without serializing their URL", async () => {
    fetchMock.mockRejectedValue(
      new TypeError(
        "fetch failed for https://user:secret@api.example.com/v0/run?token=secret#trace",
      ),
    );

    const error = await listMemories("https://api.example.com", "user-1").catch((value) => value);

    expect(error).toEqual(
      expect.objectContaining({
        message: "Unable to reach the configured API",
        status: 0,
        code: "transport_error",
      }),
    );
    expect(JSON.stringify({ message: error.message, detail: error.detail })).not.toContain("secret");
  });

  it("rejects credential-bearing base URLs without exposing them", async () => {
    const error = await listMemories(
      "https://user:secret@api.example.com?token=secret#trace",
      "user-1",
    ).catch((value) => value);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(error).toEqual(
      expect.objectContaining({
        message: "The configured API base URL is invalid",
        code: "invalid_api_base_url",
      }),
    );
    expect(JSON.stringify({ message: error.message, detail: error.detail })).not.toContain("secret");
  });

  it("aborts stalled API requests after the bounded timeout", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );

    const request = listMemories("https://api.example.com", "user-1");
    const rejection = expect(request).rejects.toEqual(
      expect.objectContaining({
        message: "Request timed out after 15 seconds",
        status: 0,
        code: "request_timeout",
      }),
    );
    await vi.advanceTimersByTimeAsync(15_000);
    await rejection;
  });

  it("uses an endpoint-specific deadline for long-running mutations", async () => {
    vi.useFakeTimers();
    const abortSpy = vi.fn();
    fetchMock.mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            abortSpy();
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );

    const request = ingestGmailMessage(
      "https://api.example.com",
      "gmail-1",
      "message-1",
      {
        user_id: "user-1",
        task_workspace_id: "workspace-1",
      },
    );
    const rejection = expect(request).rejects.toEqual(
      expect.objectContaining({
        message: "Request timed out after 120 seconds",
        code: "request_timeout",
      }),
    );
    await vi.advanceTimersByTimeAsync(30_000);
    expect(abortSpy).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(90_000);
    await rejection;
    expect(abortSpy).toHaveBeenCalledTimes(1);
  });

  it("honors a bounded custom mutation deadline", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );

    const request = requestJson("https://api.example.com", "/v0/test", {
      method: "POST",
      timeoutMs: 25,
    });
    const rejection = expect(request).rejects.toEqual(
      expect.objectContaining({ message: "Request timed out after 0.025 seconds" }),
    );
    await vi.advanceTimersByTimeAsync(25);
    await rejection;
  });

  it("executes approved requests and reads execution detail from the shipped endpoints", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          request: {
            approval_id: "approval-1",
            task_step_id: "step-1",
          },
          approval: {
            id: "approval-1",
            thread_id: "thread-1",
            task_step_id: "step-1",
            status: "approved",
            request: {
              thread_id: "thread-1",
              tool_id: "tool-1",
              action: "place_order",
              scope: "supplements",
              domain_hint: "ecommerce",
              risk_hint: "purchase",
              attributes: { quantity: "1" },
            },
            tool: {
              id: "tool-1",
              tool_key: "merchant_proxy",
              name: "Merchant Proxy",
              description: "Proxy",
              version: "0.1.0",
              metadata_version: "tool_metadata_v0",
              active: true,
              tags: [],
              action_hints: [],
              scope_hints: [],
              domain_hints: [],
              risk_hints: [],
              metadata: {},
              created_at: "2026-03-17T00:00:00Z",
            },
            routing: {
              decision: "require_approval",
              reasons: [],
              trace: {
                trace_id: "trace-1",
                trace_event_count: 3,
              },
            },
            created_at: "2026-03-17T00:00:00Z",
            resolution: {
              resolved_at: "2026-03-17T00:02:00Z",
              resolved_by_user_id: "user-1",
            },
          },
          tool: {
            id: "tool-1",
            tool_key: "merchant_proxy",
            name: "Merchant Proxy",
            description: "Proxy",
            version: "0.1.0",
            metadata_version: "tool_metadata_v0",
            active: true,
            tags: [],
            action_hints: [],
            scope_hints: [],
            domain_hints: [],
            risk_hints: [],
            metadata: {},
            created_at: "2026-03-17T00:00:00Z",
          },
          result: {
            handler_key: "proxy.echo",
            status: "completed",
            output: { ok: true },
            reason: null,
          },
          events: {
            request_event_id: "event-1",
            request_sequence_no: 1,
            result_event_id: "event-2",
            result_sequence_no: 2,
          },
          trace: {
            trace_id: "trace-2",
            trace_event_count: 9,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          execution: {
            id: "execution-1",
            approval_id: "approval-1",
            task_step_id: "step-1",
            thread_id: "thread-1",
            tool_id: "tool-1",
            trace_id: "trace-2",
            request_event_id: "event-1",
            result_event_id: "event-2",
            status: "completed",
            handler_key: "proxy.echo",
            request: {
              thread_id: "thread-1",
              tool_id: "tool-1",
              action: "place_order",
              scope: "supplements",
              domain_hint: "ecommerce",
              risk_hint: "purchase",
              attributes: { quantity: "1" },
            },
            tool: {
              id: "tool-1",
              tool_key: "merchant_proxy",
              name: "Merchant Proxy",
              description: "Proxy",
              version: "0.1.0",
              metadata_version: "tool_metadata_v0",
              active: true,
              tags: [],
              action_hints: [],
              scope_hints: [],
              domain_hints: [],
              risk_hints: [],
              metadata: {},
              created_at: "2026-03-17T00:00:00Z",
            },
            result: {
              handler_key: "proxy.echo",
              status: "completed",
              output: { ok: true },
              reason: null,
            },
            executed_at: "2026-03-17T00:03:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await executeApproval("https://api.example.com", "approval-1", "user-1");
    await getToolExecution("https://api.example.com", "execution-1", "user-1");

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/approvals/approval-1/execute",
        expect.objectContaining({
          method: "POST",
        }),
      ],
      [
        "https://api.example.com/v0/tool-executions/execution-1?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
    });
  });

  it("reads task-step timelines from the shipped endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "step-1",
              task_id: "task-1",
              sequence_no: 1,
              kind: "governed_request",
              status: "created",
              request: {
                thread_id: "thread-1",
                tool_id: "tool-1",
                action: "place_order",
                scope: "supplements",
                domain_hint: "ecommerce",
                risk_hint: "purchase",
                attributes: {},
              },
              outcome: {
                routing_decision: "require_approval",
                approval_id: "approval-1",
                approval_status: "pending",
                execution_id: null,
                execution_status: null,
                blocked_reason: null,
              },
              lineage: {
                parent_step_id: null,
                source_approval_id: null,
                source_execution_id: null,
              },
              trace: {
                trace_id: "trace-1",
                trace_kind: "approval_request",
              },
              created_at: "2026-03-17T00:00:00Z",
              updated_at: "2026-03-17T00:00:00Z",
            },
          ],
          summary: {
            task_id: "task-1",
            total_count: 1,
            latest_sequence_no: 1,
            latest_status: "created",
            next_sequence_no: 2,
            append_allowed: false,
            order: ["step-1"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await getTaskSteps("https://api.example.com", "task-1", "user-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/tasks/task-1/steps?user_id=user-1",
      expect.objectContaining({
        cache: "no-store",
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("reads the shipped trace review endpoints with user-scoped query params", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "trace-1",
              thread_id: "thread-1",
              kind: "context.compile",
              compiler_version: "continuity_v0",
              status: "completed",
              created_at: "2026-03-17T00:00:00Z",
              trace_event_count: 2,
            },
          ],
          summary: {
            total_count: 1,
            order: ["created_at_desc", "id_desc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          trace: {
            id: "trace-1",
            thread_id: "thread-1",
            kind: "context.compile",
            compiler_version: "continuity_v0",
            status: "completed",
            created_at: "2026-03-17T00:00:00Z",
            trace_event_count: 2,
            limits: {
              max_sessions: 3,
              max_events: 8,
            },
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "event-1",
              trace_id: "trace-1",
              sequence_no: 1,
              kind: "context.summary",
              payload: {
                thread_id: "thread-1",
              },
              created_at: "2026-03-17T00:00:01Z",
            },
          ],
          summary: {
            trace_id: "trace-1",
            total_count: 1,
            order: ["sequence_no_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await listTraces("https://api.example.com", "user-1");
    await getTraceDetail("https://api.example.com", "trace-1", "user-1");
    await getTraceEvents("https://api.example.com", "trace-1", "user-1");

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/traces?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        }),
      ],
      [
        "https://api.example.com/v0/traces/trace-1?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/traces/trace-1/events?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
    ]);
  });

  it("reads entity review list, detail, and edge endpoints with user-scoped query params", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "entity-1",
              entity_type: "person",
              name: "Alice",
              source_memory_ids: ["memory-1"],
              created_at: "2026-03-18T00:00:00Z",
            },
          ],
          summary: {
            total_count: 1,
            order: ["created_at_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          entity: {
            id: "entity-1",
            entity_type: "person",
            name: "Alice",
            source_memory_ids: ["memory-1"],
            created_at: "2026-03-18T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "edge-1",
              from_entity_id: "entity-1",
              to_entity_id: "entity-2",
              relationship_type: "prefers_merchant",
              valid_from: "2026-03-18T00:00:00Z",
              valid_to: null,
              source_memory_ids: ["memory-1"],
              created_at: "2026-03-18T00:01:00Z",
            },
          ],
          summary: {
            entity_id: "entity-1",
            total_count: 1,
            order: ["created_at_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await listEntities("https://api.example.com", "user-1");
    await getEntityDetail("https://api.example.com", "entity-1", "user-1");
    await listEntityEdges("https://api.example.com", "entity-1", "user-1");

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/entities?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/entities/entity-1?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/entities/entity-1/edges?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
    ]);
  });

  it("reads and writes Gmail account and selected-message ingestion endpoints", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account: {
            id: "gmail-account-1",
            provider: "gmail",
            auth_kind: "oauth_access_token",
            provider_account_id: "acct-owner-001",
            email_address: "owner@gmail.example",
            display_name: "Owner",
            scope: "https://www.googleapis.com/auth/gmail.readonly",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "gmail-account-1",
              provider: "gmail",
              auth_kind: "oauth_access_token",
              provider_account_id: "acct-owner-001",
              email_address: "owner@gmail.example",
              display_name: "Owner",
              scope: "https://www.googleapis.com/auth/gmail.readonly",
              created_at: "2026-03-18T00:00:00Z",
              updated_at: "2026-03-18T00:00:00Z",
            },
          ],
          summary: {
            total_count: 1,
            order: ["created_at_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account: {
            id: "gmail-account-1",
            provider: "gmail",
            auth_kind: "oauth_access_token",
            provider_account_id: "acct-owner-001",
            email_address: "owner@gmail.example",
            display_name: "Owner",
            scope: "https://www.googleapis.com/auth/gmail.readonly",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account: {
            id: "gmail-account-1",
            provider: "gmail",
            auth_kind: "oauth_access_token",
            provider_account_id: "acct-owner-001",
            email_address: "owner@gmail.example",
            display_name: "Owner",
            scope: "https://www.googleapis.com/auth/gmail.readonly",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
          message: {
            provider_message_id: "msg-001",
            artifact_relative_path: "gmail/acct-owner-001/msg-001.eml",
            media_type: "message/rfc822",
          },
          artifact: {
            id: "artifact-1",
            task_id: "task-1",
            task_workspace_id: "workspace-1",
            status: "registered",
            ingestion_status: "ingested",
            relative_path: "gmail/acct-owner-001/msg-001.eml",
            media_type_hint: "message/rfc822",
            created_at: "2026-03-18T00:05:00Z",
            updated_at: "2026-03-18T00:06:00Z",
          },
          summary: {
            total_count: 1,
            total_characters: 240,
            media_type: "message/rfc822",
            chunking_rule: "normalized_utf8_text_fixed_window_1000_chars_v1",
            order: ["sequence_no_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await connectGmailAccount("https://api.example.com", {
      user_id: "user-1",
      provider_account_id: "acct-owner-001",
      email_address: "owner@gmail.example",
      display_name: "Owner",
      scope: "https://www.googleapis.com/auth/gmail.readonly",
      access_token: "access-token-1",
    });
    await listGmailAccounts("https://api.example.com", "user-1");
    await getGmailAccountDetail("https://api.example.com", "gmail-account-1", "user-1");
    await ingestGmailMessage(
      "https://api.example.com",
      "gmail-account-1",
      "msg-001",
      {
        user_id: "user-1",
        task_workspace_id: "workspace-1",
      },
    );

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/gmail-accounts",
        expect.objectContaining({
          method: "POST",
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/gmail-accounts?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/gmail-accounts/gmail-account-1?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/gmail-accounts/gmail-account-1/messages/msg-001/ingest",
        expect.objectContaining({
          method: "POST",
          cache: "no-store",
        }),
      ],
    ]);

    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      provider_account_id: "acct-owner-001",
      email_address: "owner@gmail.example",
      display_name: "Owner",
      scope: "https://www.googleapis.com/auth/gmail.readonly",
      access_token: "access-token-1",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[3]?.[1]?.body))).toEqual({
      user_id: "user-1",
      task_workspace_id: "workspace-1",
    });
  });

  it("reads Calendar discovery and writes selected-event ingestion endpoints", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account: {
            id: "calendar-account-1",
            provider: "google_calendar",
            auth_kind: "oauth_access_token",
            provider_account_id: "acct-owner-001",
            email_address: "owner@gmail.example",
            display_name: "Owner",
            scope: "https://www.googleapis.com/auth/calendar.readonly",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
          items: [
            {
              provider_event_id: "evt-001",
              status: "confirmed",
              summary: "Sprint planning review",
              start_time: "2026-03-20T09:00:00+00:00",
              end_time: "2026-03-20T09:30:00+00:00",
              html_link: "https://calendar.google.com/event?eid=evt-001",
              updated_at: "2026-03-19T10:00:00+00:00",
            },
          ],
          summary: {
            total_count: 1,
            limit: 20,
            order: ["start_time_asc", "provider_event_id_asc"],
            time_min: "2026-03-20T00:00:00Z",
            time_max: "2026-03-21T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account: {
            id: "calendar-account-1",
            provider: "google_calendar",
            auth_kind: "oauth_access_token",
            provider_account_id: "acct-owner-001",
            email_address: "owner@gmail.example",
            display_name: "Owner",
            scope: "https://www.googleapis.com/auth/calendar.readonly",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "calendar-account-1",
              provider: "google_calendar",
              auth_kind: "oauth_access_token",
              provider_account_id: "acct-owner-001",
              email_address: "owner@gmail.example",
              display_name: "Owner",
              scope: "https://www.googleapis.com/auth/calendar.readonly",
              created_at: "2026-03-18T00:00:00Z",
              updated_at: "2026-03-18T00:00:00Z",
            },
          ],
          summary: {
            total_count: 1,
            order: ["created_at_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account: {
            id: "calendar-account-1",
            provider: "google_calendar",
            auth_kind: "oauth_access_token",
            provider_account_id: "acct-owner-001",
            email_address: "owner@gmail.example",
            display_name: "Owner",
            scope: "https://www.googleapis.com/auth/calendar.readonly",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account: {
            id: "calendar-account-1",
            provider: "google_calendar",
            auth_kind: "oauth_access_token",
            provider_account_id: "acct-owner-001",
            email_address: "owner@gmail.example",
            display_name: "Owner",
            scope: "https://www.googleapis.com/auth/calendar.readonly",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
          },
          event: {
            provider_event_id: "evt-001",
            artifact_relative_path: "calendar/acct-owner-001/evt-001.txt",
            media_type: "text/plain",
          },
          artifact: {
            id: "artifact-1",
            task_id: "task-1",
            task_workspace_id: "workspace-1",
            status: "registered",
            ingestion_status: "ingested",
            relative_path: "calendar/acct-owner-001/evt-001.txt",
            media_type_hint: "text/plain",
            created_at: "2026-03-18T00:05:00Z",
            updated_at: "2026-03-18T00:06:00Z",
          },
          summary: {
            total_count: 1,
            total_characters: 240,
            media_type: "text/plain",
            chunking_rule: "normalized_utf8_text_fixed_window_1000_chars_v1",
            order: ["sequence_no_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await connectCalendarAccount("https://api.example.com", {
      user_id: "user-1",
      provider_account_id: "acct-owner-001",
      email_address: "owner@gmail.example",
      display_name: "Owner",
      scope: "https://www.googleapis.com/auth/calendar.readonly",
      access_token: "access-token-1",
    });
    await listCalendarAccounts("https://api.example.com", "user-1");
    await getCalendarAccountDetail("https://api.example.com", "calendar-account-1", "user-1");
    await listCalendarEvents("https://api.example.com", "calendar-account-1", "user-1", {
      limit: 20,
      timeMin: "2026-03-20T00:00:00Z",
      timeMax: "2026-03-21T00:00:00Z",
    });
    await ingestCalendarEvent(
      "https://api.example.com",
      "calendar-account-1",
      "evt-001",
      {
        user_id: "user-1",
        task_workspace_id: "workspace-1",
      },
    );

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/calendar-accounts",
        expect.objectContaining({
          method: "POST",
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/calendar-accounts?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/calendar-accounts/calendar-account-1?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/calendar-accounts/calendar-account-1/events?user_id=user-1&limit=20&time_min=2026-03-20T00%3A00%3A00Z&time_max=2026-03-21T00%3A00%3A00Z",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/calendar-accounts/calendar-account-1/events/evt-001/ingest",
        expect.objectContaining({
          method: "POST",
          cache: "no-store",
        }),
      ],
    ]);

    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      provider_account_id: "acct-owner-001",
      email_address: "owner@gmail.example",
      display_name: "Owner",
      scope: "https://www.googleapis.com/auth/calendar.readonly",
      access_token: "access-token-1",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[4]?.[1]?.body))).toEqual({
      user_id: "user-1",
      task_workspace_id: "workspace-1",
    });
  });

  it("reads task workspace and artifact review endpoints with user-scoped query params", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "workspace-1",
              task_id: "task-1",
              status: "active",
              local_path: "/tmp/workspace/task-1",
              created_at: "2026-03-18T00:00:00Z",
              updated_at: "2026-03-18T00:00:00Z",
            },
          ],
          summary: {
            total_count: 1,
            order: ["created_at_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "artifact-1",
              task_id: "task-1",
              task_workspace_id: "workspace-1",
              status: "registered",
              ingestion_status: "ingested",
              relative_path: "notes/review.md",
              media_type_hint: "text/markdown",
              created_at: "2026-03-18T00:00:00Z",
              updated_at: "2026-03-18T00:01:00Z",
            },
          ],
          summary: {
            total_count: 1,
            order: ["created_at_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          artifact: {
            id: "artifact-1",
            task_id: "task-1",
            task_workspace_id: "workspace-1",
            status: "registered",
            ingestion_status: "ingested",
            relative_path: "notes/review.md",
            media_type_hint: "text/markdown",
            created_at: "2026-03-18T00:00:00Z",
            updated_at: "2026-03-18T00:01:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "chunk-1",
              task_artifact_id: "artifact-1",
              sequence_no: 1,
              char_start: 0,
              char_end_exclusive: 12,
              text: "hello world",
              created_at: "2026-03-18T00:02:00Z",
              updated_at: "2026-03-18T00:02:00Z",
            },
          ],
          summary: {
            total_count: 1,
            total_characters: 12,
            media_type: "text/markdown",
            chunking_rule: "artifact_ingestion_v0",
            order: ["sequence_no_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await listTaskWorkspaces("https://api.example.com", "user-1");
    await listTaskArtifacts("https://api.example.com", "user-1");
    await getTaskArtifactDetail("https://api.example.com", "artifact-1", "user-1");
    await listTaskArtifactChunks("https://api.example.com", "artifact-1", "user-1");

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/task-workspaces?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/task-artifacts?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/task-artifacts/artifact-1?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/task-artifacts/artifact-1/chunks?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
    ]);
  });

  it("reads memory review list, queue, summary, detail, revisions, and labels from shipped endpoints", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [],
          summary: {
            status: "active",
            limit: 5,
            returned_count: 0,
            total_count: 0,
            has_more: false,
            order: ["updated_at_desc", "created_at_desc", "id_desc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [],
          summary: {
            memory_status: "active",
            review_state: "unlabeled",
            limit: 3,
            returned_count: 0,
            total_count: 0,
            has_more: false,
            order: ["updated_at_desc", "created_at_desc", "id_desc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          summary: {
            total_memory_count: 3,
            active_memory_count: 3,
            deleted_memory_count: 0,
            labeled_memory_count: 1,
            unlabeled_memory_count: 2,
            total_label_row_count: 2,
            label_row_counts_by_value: {
              correct: 1,
              incorrect: 0,
              outdated: 1,
              insufficient_evidence: 0,
            },
            label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          summary: {
            status: "needs_review",
            precision: 0.8,
            precision_target: 0.8,
            adjudicated_sample_count: 10,
            minimum_adjudicated_sample: 10,
            remaining_to_minimum_sample: 0,
            unlabeled_memory_count: 1,
            high_risk_memory_count: 1,
            stale_truth_count: 0,
            superseded_active_conflict_count: 0,
            counts: {
              active_memory_count: 3,
              labeled_active_memory_count: 2,
              adjudicated_correct_count: 8,
              adjudicated_incorrect_count: 2,
              outdated_label_count: 0,
              insufficient_evidence_label_count: 0,
            },
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          memory: {
            id: "memory-1",
            memory_key: "user.preference.merchant",
            value: { merchant: "Thorne" },
            status: "active",
            source_event_ids: ["event-1"],
            created_at: "2026-03-17T00:00:00Z",
            updated_at: "2026-03-18T00:00:00Z",
            deleted_at: null,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [],
          summary: {
            memory_id: "memory-1",
            limit: 10,
            returned_count: 0,
            total_count: 0,
            has_more: false,
            order: ["sequence_no_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [],
          summary: {
            memory_id: "memory-1",
            total_count: 0,
            counts_by_label: {
              correct: 0,
              incorrect: 0,
              outdated: 0,
              insufficient_evidence: 0,
            },
            order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await listMemories("https://api.example.com", "user-1", { status: "active", limit: 5 });
    await listMemoryReviewQueue("https://api.example.com", "user-1", {
      limit: 3,
      priorityMode: "high_risk_first",
    });
    await getMemoryEvaluationSummary("https://api.example.com", "user-1");
    await getMemoryDetail("https://api.example.com", "memory-1", "user-1");
    await getMemoryRevisions("https://api.example.com", "memory-1", "user-1", 10);
    await listMemoryLabels("https://api.example.com", "memory-1", "user-1");

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/memories?user_id=user-1&status=active&limit=5",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/memories/review-queue?user_id=user-1&limit=3&priority_mode=high_risk_first",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/memories/evaluation-summary?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/memories/quality-gate?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/memories/memory-1?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/memories/memory-1/revisions?user_id=user-1&limit=10",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
      [
        "https://api.example.com/v0/memories/memory-1/labels?user_id=user-1",
        expect.objectContaining({
          cache: "no-store",
        }),
      ],
    ]);
  });

  it("combines memory evaluation summary with canonical quality-gate payload", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          summary: {
            total_memory_count: 2,
            active_memory_count: 2,
            deleted_memory_count: 0,
            labeled_memory_count: 2,
            unlabeled_memory_count: 0,
            total_label_row_count: 2,
            label_row_counts_by_value: {
              correct: 2,
              incorrect: 0,
              outdated: 0,
              insufficient_evidence: 0,
            },
            label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          summary: {
            status: "healthy",
            precision: 1,
            precision_target: 0.8,
            adjudicated_sample_count: 10,
            minimum_adjudicated_sample: 10,
            remaining_to_minimum_sample: 0,
            unlabeled_memory_count: 0,
            high_risk_memory_count: 0,
            stale_truth_count: 0,
            superseded_active_conflict_count: 0,
            counts: {
              active_memory_count: 2,
              labeled_active_memory_count: 2,
              adjudicated_correct_count: 10,
              adjudicated_incorrect_count: 0,
              outdated_label_count: 0,
              insufficient_evidence_label_count: 0,
            },
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const payload = await getMemoryEvaluationSummary("https://api.example.com", "user-1");

    expect(payload.summary.quality_gate?.status).toBe("healthy");
    expect(payload.summary.quality_gate?.precision_target).toBe(0.8);
  });

  it("reads canonical memory trust dashboard payload", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          dashboard: {
            quality_gate: {
              status: "needs_review",
              precision: 0.9,
              precision_target: 0.8,
              adjudicated_sample_count: 10,
              minimum_adjudicated_sample: 10,
              remaining_to_minimum_sample: 0,
              unlabeled_memory_count: 2,
              high_risk_memory_count: 1,
              stale_truth_count: 1,
              superseded_active_conflict_count: 0,
              counts: {
                active_memory_count: 12,
                labeled_active_memory_count: 10,
                adjudicated_correct_count: 9,
                adjudicated_incorrect_count: 1,
                outdated_label_count: 0,
                insufficient_evidence_label_count: 0,
              },
            },
            queue_posture: {
              priority_mode: "recent_first",
              total_count: 2,
              high_risk_count: 1,
              stale_truth_count: 1,
              priority_reason_counts: {
                recent_first: 2,
              },
              order: ["updated_at_desc", "created_at_desc", "id_desc"],
              aging: {
                anchor_updated_at: "2026-03-29T12:00:00Z",
                newest_updated_at: "2026-03-29T12:00:00Z",
                oldest_updated_at: "2026-03-27T12:00:00Z",
                backlog_span_hours: 48,
                fresh_within_24h_count: 1,
                aging_24h_to_72h_count: 1,
                stale_over_72h_count: 0,
              },
            },
            retrieval_quality: {
              fixture_count: 3,
              evaluated_fixture_count: 3,
              passing_fixture_count: 3,
              precision_at_k_mean: 1,
              precision_at_1_mean: 1,
              precision_target: 0.8,
              status: "pass",
              fixture_order: ["fixture_id_asc"],
              result_order: ["precision_at_k_desc", "fixture_id_asc"],
            },
            correction_freshness: {
              total_open_loop_count: 4,
              stale_open_loop_count: 1,
              correction_recurrence_count: 1,
              freshness_drift_count: 1,
            },
            recommended_review: {
              priority_mode: "high_risk_first",
              action: "review_high_risk_queue",
              reason: "High-risk unlabeled memories are present; triage those first.",
            },
            sources: [
              "memories",
              "memory_review_labels",
              "continuity_recall",
              "continuity_correction_events",
              "retrieval_evaluation_fixtures",
            ],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const payload = await getMemoryTrustDashboard("https://api.example.com", "user-1");

    expect(payload.dashboard.recommended_review.action).toBe("review_high_risk_queue");
    expect(payload.dashboard.queue_posture.total_count).toBe(2);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/memories/trust-dashboard?user_id=user-1",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

  it("reads and mutates open-loop endpoints with user-scoped routing", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "loop-1",
              memory_id: "memory-1",
              title: "Confirm reorder details",
              status: "open",
              opened_at: "2026-03-23T09:00:00Z",
              due_at: "2026-03-25T09:00:00Z",
              resolved_at: null,
              resolution_note: null,
              created_at: "2026-03-23T09:00:00Z",
              updated_at: "2026-03-23T09:00:00Z",
            },
          ],
          summary: {
            status: "open",
            limit: 5,
            returned_count: 1,
            total_count: 1,
            has_more: false,
            order: ["opened_at_desc", "created_at_desc", "id_desc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          open_loop: {
            id: "loop-1",
            memory_id: "memory-1",
            title: "Confirm reorder details",
            status: "open",
            opened_at: "2026-03-23T09:00:00Z",
            due_at: "2026-03-25T09:00:00Z",
            resolved_at: null,
            resolution_note: null,
            created_at: "2026-03-23T09:00:00Z",
            updated_at: "2026-03-23T09:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          open_loop: {
            id: "loop-2",
            memory_id: "memory-1",
            title: "Follow up on confidence",
            status: "open",
            opened_at: "2026-03-24T09:00:00Z",
            due_at: null,
            resolved_at: null,
            resolution_note: null,
            created_at: "2026-03-24T09:00:00Z",
            updated_at: "2026-03-24T09:00:00Z",
          },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          open_loop: {
            id: "loop-1",
            memory_id: "memory-1",
            title: "Confirm reorder details",
            status: "resolved",
            opened_at: "2026-03-23T09:00:00Z",
            due_at: "2026-03-25T09:00:00Z",
            resolved_at: "2026-03-24T10:00:00Z",
            resolution_note: "Resolved",
            created_at: "2026-03-23T09:00:00Z",
            updated_at: "2026-03-24T10:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await listOpenLoops("https://api.example.com", "user-1", { status: "open", limit: 5 });
    await getOpenLoopDetail("https://api.example.com", "loop-1", "user-1");
    await createOpenLoop("https://api.example.com", {
      user_id: "user-1",
      memory_id: "memory-1",
      title: "Follow up on confidence",
    });
    await updateOpenLoopStatus("https://api.example.com", "loop-1", {
      user_id: "user-1",
      status: "resolved",
      resolution_note: "Resolved",
    });

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/open-loops?user_id=user-1&status=open&limit=5",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/open-loops/loop-1?user_id=user-1",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/open-loops",
        expect.objectContaining({ method: "POST" }),
      ],
      [
        "https://api.example.com/v0/open-loops/loop-1/status",
        expect.objectContaining({ method: "POST" }),
      ],
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[2]?.[1]?.body))).toEqual({
      user_id: "user-1",
      memory_id: "memory-1",
      title: "Follow up on confidence",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[3]?.[1]?.body))).toEqual({
      user_id: "user-1",
      status: "resolved",
      resolution_note: "Resolved",
    });
  });

  it("posts explicit memory admissions to the shipped endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          decision: "ADD",
          reason: "memory_created",
          memory: {
            id: "memory-1",
            user_id: "user-1",
            memory_key: "user.preference.supplement.magnesium",
            value: {
              merchant: "Thorne",
            },
            status: "active",
            source_event_ids: ["event-2", "event-1"],
            created_at: "2026-03-19T00:00:00Z",
            updated_at: "2026-03-19T00:00:00Z",
            deleted_at: null,
          },
          revision: {
            id: "revision-1",
            user_id: "user-1",
            memory_id: "memory-1",
            sequence_no: 1,
            action: "ADD",
            memory_key: "user.preference.supplement.magnesium",
            previous_value: null,
            new_value: {
              merchant: "Thorne",
            },
            source_event_ids: ["event-2", "event-1"],
            candidate: {
              memory_key: "user.preference.supplement.magnesium",
              value: {
                merchant: "Thorne",
              },
              source_event_ids: ["event-2", "event-1"],
              delete_requested: false,
            },
            created_at: "2026-03-19T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await admitMemory("https://api.example.com", {
      user_id: "user-1",
      memory_key: "user.preference.supplement.magnesium",
      value: {
        merchant: "Thorne",
      },
      source_event_ids: ["event-2", "event-1"],
      delete_requested: false,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/memories/admit",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      memory_key: "user.preference.supplement.magnesium",
      value: {
        merchant: "Thorne",
      },
      source_event_ids: ["event-2", "event-1"],
      delete_requested: false,
    });
  });

  it("posts explicit commitment extraction requests to the shipped endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          candidates: [
            {
              memory_key: "user.commitment.submit_tax_forms",
              value: {
                kind: "explicit_commitment",
                text: "submit tax forms",
              },
              source_event_ids: ["event-1"],
              delete_requested: false,
              pattern: "remind_me_to",
              commitment_text: "submit tax forms",
              open_loop_title: "Remember to submit tax forms",
            },
          ],
          admissions: [
            {
              decision: "ADD",
              reason: "source_backed_add",
              memory: {
                id: "memory-1",
                user_id: "user-1",
                memory_key: "user.commitment.submit_tax_forms",
                value: {
                  kind: "explicit_commitment",
                  text: "submit tax forms",
                },
                status: "active",
                source_event_ids: ["event-1"],
                created_at: "2026-03-23T09:00:00Z",
                updated_at: "2026-03-23T09:00:00Z",
                deleted_at: null,
              },
              revision: null,
              open_loop: {
                decision: "CREATED",
                reason: "created_open_loop_for_memory",
                open_loop: {
                  id: "loop-1",
                  memory_id: "memory-1",
                  title: "Remember to submit tax forms",
                  status: "open",
                  opened_at: "2026-03-23T09:00:00Z",
                  due_at: null,
                  resolved_at: null,
                  resolution_note: null,
                  created_at: "2026-03-23T09:00:00Z",
                  updated_at: "2026-03-23T09:00:00Z",
                },
              },
            },
          ],
          summary: {
            source_event_id: "event-1",
            source_event_kind: "message.user",
            candidate_count: 1,
            admission_count: 1,
            persisted_change_count: 1,
            noop_count: 0,
            open_loop_created_count: 1,
            open_loop_noop_count: 0,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await extractExplicitCommitments("https://api.example.com", {
      user_id: "user-1",
      source_event_id: "event-1",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/open-loops/extract-explicit-commitments",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      source_event_id: "event-1",
    });
  });

  it("posts and reads continuity capture inbox endpoints", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          capture: {
            capture_event: {
              id: "capture-1",
              raw_content: "Finalize launch checklist",
              explicit_signal: "task",
              admission_posture: "DERIVED",
              admission_reason: "explicit_signal_task",
              created_at: "2026-03-29T09:00:00Z",
            },
            derived_object: {
              id: "object-1",
              capture_event_id: "capture-1",
              object_type: "NextAction",
              status: "active",
              title: "Next Action: Finalize launch checklist",
              body: {
                action_text: "Finalize launch checklist",
                raw_content: "Finalize launch checklist",
                explicit_signal: "task",
              },
              provenance: {
                capture_event_id: "capture-1",
                source_kind: "continuity_capture_event",
              },
              confidence: 1,
              created_at: "2026-03-29T09:00:00Z",
              updated_at: "2026-03-29T09:00:00Z",
            },
          },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              capture_event: {
                id: "capture-1",
                raw_content: "Finalize launch checklist",
                explicit_signal: "task",
                admission_posture: "DERIVED",
                admission_reason: "explicit_signal_task",
                created_at: "2026-03-29T09:00:00Z",
              },
              derived_object: null,
            },
          ],
          summary: {
            limit: 20,
            returned_count: 1,
            total_count: 1,
            derived_count: 1,
            triage_count: 0,
            order: ["created_at_desc", "id_desc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          capture: {
            capture_event: {
              id: "capture-1",
              raw_content: "Finalize launch checklist",
              explicit_signal: "task",
              admission_posture: "DERIVED",
              admission_reason: "explicit_signal_task",
              created_at: "2026-03-29T09:00:00Z",
            },
            derived_object: null,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await createContinuityCapture("https://api.example.com", {
      user_id: "user-1",
      raw_content: "Finalize launch checklist",
      explicit_signal: "task",
    });
    await listContinuityCaptures("https://api.example.com", "user-1", { limit: 20 });
    await getContinuityCaptureDetail("https://api.example.com", "capture-1", "user-1");

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/continuity/captures",
        expect.objectContaining({ method: "POST" }),
      ],
      [
        "https://api.example.com/v0/continuity/captures?user_id=user-1&limit=20",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/continuity/captures/capture-1?user_id=user-1",
        expect.objectContaining({ cache: "no-store" }),
      ],
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      raw_content: "Finalize launch checklist",
      explicit_signal: "task",
    });
  });

  it("throws ApiError when memory admission returns a backend error envelope", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "source_event_ids must all reference existing events owned by the user",
        }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(
      admitMemory("https://api.example.com", {
        user_id: "user-1",
        memory_key: "user.preference.supplement.magnesium",
        value: {
          merchant: "Thorne",
        },
        source_event_ids: ["missing-event"],
      }),
    ).rejects.toEqual(
      expect.objectContaining({
        message: "source_event_ids must all reference existing events owned by the user",
        status: 400,
      }),
    );
  });

  it("posts memory review labels to the shipped endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          label: {
            id: "label-1",
            memory_id: "memory-1",
            reviewer_user_id: "user-1",
            label: "correct",
            note: "Still matches latest evidence.",
            created_at: "2026-03-18T00:00:00Z",
          },
          summary: {
            memory_id: "memory-1",
            total_count: 1,
            counts_by_label: {
              correct: 1,
              incorrect: 0,
              outdated: 0,
              insufficient_evidence: 0,
            },
            order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
          },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );

    await submitMemoryLabel("https://api.example.com", "memory-1", {
      user_id: "user-1",
      label: "correct",
      note: "Still matches latest evidence.",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/memories/memory-1/labels",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      label: "correct",
      note: "Still matches latest evidence.",
    });
  });

  it("lists task runs from the shipped task-runs endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              id: "run-1",
              task_id: "task-1",
              status: "running",
              checkpoint: {
                cursor: 1,
                target_steps: 3,
                wait_for_signal: false,
              },
              tick_count: 1,
              step_count: 1,
              max_ticks: 3,
              retry_count: 0,
              retry_cap: 3,
              retry_posture: "none",
              failure_class: null,
              stop_reason: null,
              last_transitioned_at: "2026-03-27T10:05:00Z",
              created_at: "2026-03-27T10:00:00Z",
              updated_at: "2026-03-27T10:05:00Z",
            },
          ],
          summary: {
            task_id: "task-1",
            total_count: 1,
            order: ["created_at_asc", "id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await listTaskRuns("https://api.example.com", "task-1", "user-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/tasks/task-1/runs?user_id=user-1",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("throws ApiError when task-run listing returns a backend error envelope", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "task task-1 was not found",
        }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(listTaskRuns("https://api.example.com", "task-1", "user-1")).rejects.toEqual(
      expect.objectContaining({
        message: "task task-1 was not found",
        status: 404,
      }),
    );
  });

  it("queries continuity recall with scoped filter parameters", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          summary: {
            query: "rollout",
            filters: { thread_id: "thread-1", since: null, until: null },
            limit: 20,
            returned_count: 0,
            total_count: 0,
            order: ["relevance_desc", "created_at_desc", "id_desc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await queryContinuityRecall("https://api.example.com", "user-1", {
      query: "rollout",
      threadId: "thread-1",
      project: "Project Phoenix",
      person: "Alex",
      limit: 20,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/continuity/recall?user_id=user-1&query=rollout&thread_id=thread-1&project=Project+Phoenix&person=Alex&limit=20",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("reads continuity retrieval evaluation fixture summary from the shipped endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          fixtures: [],
          summary: {
            fixture_count: 3,
            evaluated_fixture_count: 3,
            passing_fixture_count: 3,
            precision_at_k_mean: 1,
            precision_at_1_mean: 1,
            precision_target: 0.8,
            status: "pass",
            fixture_order: ["fixture_id_asc"],
            result_order: ["precision_at_k_desc", "fixture_id_asc"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await getContinuityRetrievalEvaluation("https://api.example.com", "user-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/continuity/retrieval-evaluation?user_id=user-1",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("reads continuity resumption briefs with deterministic section limits", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          brief: {
            assembly_version: "continuity_resumption_brief_v0",
            scope: { thread_id: "thread-1", since: null, until: null },
            last_decision: { item: null, empty_state: { is_empty: true, message: "none" } },
            open_loops: {
              items: [],
              summary: { limit: 3, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
              empty_state: { is_empty: true, message: "none" },
            },
            recent_changes: {
              items: [],
              summary: { limit: 4, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
              empty_state: { is_empty: true, message: "none" },
            },
            next_action: { item: null, empty_state: { is_empty: true, message: "none" } },
            sources: ["continuity_capture_events", "continuity_objects"],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await getContinuityResumptionBrief("https://api.example.com", "user-1", {
      threadId: "thread-1",
      maxRecentChanges: 4,
      maxOpenLoops: 3,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/continuity/resumption-brief?user_id=user-1&thread_id=thread-1&max_recent_changes=4&max_open_loops=3",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("uses continuity review queue/detail/correction endpoints", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [],
            summary: {
              status: "correction_ready",
              limit: 20,
              returned_count: 0,
              total_count: 0,
              order: ["updated_at_desc", "created_at_desc", "id_desc"],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            review: {
              continuity_object: {
                id: "object-1",
                capture_event_id: "capture-1",
                object_type: "Decision",
                status: "active",
                title: "Decision: Keep rollout phased",
                body: { decision_text: "Keep rollout phased" },
                provenance: {},
                confidence: 0.9,
                last_confirmed_at: null,
                supersedes_object_id: null,
                superseded_by_object_id: null,
                created_at: "2026-03-30T10:00:00Z",
                updated_at: "2026-03-30T10:00:00Z",
              },
              correction_events: [],
              supersession_chain: { supersedes: null, superseded_by: null },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            continuity_object: {
              id: "object-1",
              capture_event_id: "capture-1",
              object_type: "Decision",
              status: "active",
              title: "Decision: Keep rollout phased",
              body: { decision_text: "Keep rollout phased" },
              provenance: {},
              confidence: 0.9,
              last_confirmed_at: "2026-03-30T10:01:00Z",
              supersedes_object_id: null,
              superseded_by_object_id: null,
              created_at: "2026-03-30T10:00:00Z",
              updated_at: "2026-03-30T10:01:00Z",
            },
            correction_event: {
              id: "event-1",
              continuity_object_id: "object-1",
              action: "confirm",
              reason: "Reviewed",
              before_snapshot: {},
              after_snapshot: {},
              payload: {},
              created_at: "2026-03-30T10:01:00Z",
            },
            replacement_object: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    await listContinuityReviewQueue("https://api.example.com", "user-1", {
      status: "correction_ready",
      limit: 20,
    });
    await getContinuityReviewDetail("https://api.example.com", "object-1", "user-1");
    await applyContinuityCorrection("https://api.example.com", "object-1", {
      user_id: "user-1",
      action: "confirm",
      reason: "Reviewed",
    });

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/continuity/review-queue?user_id=user-1&status=correction_ready&limit=20",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/continuity/review-queue/object-1?user_id=user-1",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/continuity/review-queue/object-1/corrections",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        }),
      ],
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[2]?.[1]?.body))).toEqual({
      user_id: "user-1",
      action: "confirm",
      reason: "Reviewed",
    });
  });

  it("uses continuity open-loop dashboard, daily/weekly brief, and review-action endpoints", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            dashboard: {
              scope: { thread_id: "thread-1", since: null, until: null },
              waiting_for: {
                items: [],
                summary: { limit: 10, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              blocker: {
                items: [],
                summary: { limit: 10, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              stale: {
                items: [],
                summary: { limit: 10, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              next_action: {
                items: [],
                summary: { limit: 10, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              summary: {
                limit: 10,
                total_count: 0,
                posture_order: ["waiting_for", "blocker", "stale", "next_action"],
                item_order: ["created_at_desc", "id_desc"],
              },
              sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            brief: {
              assembly_version: "continuity_daily_brief_v0",
              scope: { thread_id: "thread-1", since: null, until: null },
              waiting_for_highlights: {
                items: [],
                summary: { limit: 3, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              blocker_highlights: {
                items: [],
                summary: { limit: 3, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              stale_items: {
                items: [],
                summary: { limit: 3, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              next_suggested_action: { item: null, empty_state: { is_empty: true, message: "none" } },
              sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            review: {
              assembly_version: "continuity_weekly_review_v0",
              scope: { thread_id: "thread-1", since: null, until: null },
              rollup: {
                total_count: 0,
                waiting_for_count: 0,
                blocker_count: 0,
                stale_count: 0,
                correction_recurrence_count: 0,
                freshness_drift_count: 0,
                next_action_count: 0,
                posture_order: ["waiting_for", "blocker", "stale", "next_action"],
              },
              waiting_for: {
                items: [],
                summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              blocker: {
                items: [],
                summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              stale: {
                items: [],
                summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              next_action: {
                items: [],
                summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
                empty_state: { is_empty: true, message: "none" },
              },
              sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            continuity_object: {
              id: "object-1",
              capture_event_id: "capture-1",
              object_type: "WaitingFor",
              status: "completed",
              title: "Waiting For: Vendor quote",
              body: { waiting_for_text: "Vendor quote" },
              provenance: {},
              confidence: 0.9,
              last_confirmed_at: null,
              supersedes_object_id: null,
              superseded_by_object_id: null,
              created_at: "2026-03-30T10:00:00Z",
              updated_at: "2026-03-30T10:01:00Z",
            },
            correction_event: {
              id: "event-1",
              continuity_object_id: "object-1",
              action: "edit",
              reason: "done in standup",
              before_snapshot: {},
              after_snapshot: {},
              payload: { review_action: "done" },
              created_at: "2026-03-30T10:01:00Z",
            },
            review_action: "done",
            lifecycle_outcome: "completed",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    await getContinuityOpenLoopDashboard("https://api.example.com", "user-1", {
      threadId: "thread-1",
      limit: 10,
    });
    await getContinuityDailyBrief("https://api.example.com", "user-1", {
      threadId: "thread-1",
      limit: 3,
    });
    await getContinuityWeeklyReview("https://api.example.com", "user-1", {
      threadId: "thread-1",
      limit: 5,
    });
    await applyContinuityOpenLoopReviewAction("https://api.example.com", "object-1", {
      user_id: "user-1",
      action: "done",
      note: "done in standup",
    });

    expect(fetchMock.mock.calls).toEqual([
      [
        "https://api.example.com/v0/continuity/open-loops?user_id=user-1&thread_id=thread-1&limit=10",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/continuity/daily-brief?user_id=user-1&thread_id=thread-1&limit=3",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/continuity/weekly-review?user_id=user-1&thread_id=thread-1&limit=5",
        expect.objectContaining({ cache: "no-store" }),
      ],
      [
        "https://api.example.com/v0/continuity/open-loops/object-1/review-action",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        }),
      ],
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[3]?.[1]?.body))).toEqual({
      user_id: "user-1",
      action: "done",
      note: "done in standup",
    });
  });

  it("uses the live vNext workspace endpoints and write payloads", async () => {
    fetchMock.mockImplementation(
      async () =>
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );

    await getVNextWorkspace("https://api.example.com", "user-1");
    await createVNextSource("https://api.example.com", {
      user_id: "user-1",
      raw_text: "Decision: live workspace uses Postgres.",
      title: "Live workspace note",
      domain: "project",
      sensitivity: "private",
    });
    await createVNextContextPack("https://api.example.com", {
      user_id: "user-1",
      query: "live workspace",
      scope: { domains: ["project"] },
      options: { sensitivity_allowed: ["public", "private"] },
    });
    await generateVNextDailyBrief("https://api.example.com", {
      user_id: "user-1",
      scope: { domains: ["project"] },
      options: { generated_for: "2026-05-11" },
    });
    await generateVNextWeeklySynthesis("https://api.example.com", {
      user_id: "user-1",
      scope: { domains: ["project"] },
      options: { generated_for: "2026-W20" },
    });
    await reviewVNextArtifact("https://api.example.com", "artifact-1", {
      user_id: "user-1",
      action: "archive",
    });
    await rateVNextArtifactQuality("https://api.example.com", "artifact-1", {
      user_id: "user-1",
      usefulness: 4,
      accuracy: 5,
      source_grounding: 5,
      novel_connections: 3,
      actionability: 4,
      hallucination_risk: 1,
      verbosity: "right_sized",
      comments: "Useful and grounded.",
    });
    await reviewVNextMemory("https://api.example.com", "memory-1", {
      user_id: "user-1",
      action: "assign_project",
      project_id: "project-1",
      reason: "Project review",
    });
    await createVNextProject("https://api.example.com", {
      user_id: "user-1",
      name: "Launch",
      domain: "project",
      sensitivity: "private",
    });
    await generateVNextProjectUpdate("https://api.example.com", {
      user_id: "user-1",
      scope: { domains: ["project"] },
      options: { project_id: "project-1" },
    });
    await createVNextOpenLoop("https://api.example.com", {
      user_id: "user-1",
      title: "Confirm launch owner",
      project_id: "project-1",
      priority: "high",
      domain: "project",
      sensitivity: "private",
    });
    await reviewVNextOpenLoop("https://api.example.com", "loop-1", {
      user_id: "user-1",
      action: "snooze",
      due_at: "2026-05-12T09:00:00Z",
    });
    await getVNextBrainCharter("https://api.example.com", "user-1");
    await upsertVNextBrainCharter("https://api.example.com", {
      user_id: "user-1",
      content_markdown: "# ALICE.md",
      sensitivity: "private",
    });
    await getVNextSchedulerFailures("https://api.example.com", "user-1", 5);
    await runVNextSchedulerWorkflowNow("https://api.example.com", "daily_brief", {
      user_id: "user-1",
      scope: { domains: ["project"] },
      options: { sensitivity_allowed: ["public", "private"] },
    });
    await runVNextSchedulerDue("https://api.example.com", { user_id: "user-1", limit: 10 });
    await getVNextQualityEvals("https://api.example.com", "user-1", { artifactId: "artifact-1", limit: 5 });
    await getVNextPolicyTelemetry("https://api.example.com", "user-1");
    await captureVNextBrowserClip("https://api.example.com", {
      user_id: "user-1",
      url: "https://example.com/live-capture",
      title: "Live capture",
      selected_text: "Fact: browser clips enter the review queue.",
      user_note: "Review this source.",
      domain: "professional",
      sensitivity: "private",
    });
    await getVNextConnectorsHealth("https://api.example.com", "user-1");
    await getVNextDogfoodingDashboard("https://api.example.com", "user-1");
    await recordVNextArtifactInsightFeedback("https://api.example.com", "artifact-1", {
      user_id: "user-1",
      useful_insight: "yes",
      surfaced_missed: "no",
      comments: "Grounded in captured evidence.",
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "https://api.example.com/v0/vnext/workspace?user_id=user-1",
      "https://api.example.com/v0/vnext/sources",
      "https://api.example.com/v0/vnext/context-packs",
      "https://api.example.com/v0/vnext/artifacts/generate/daily-brief",
      "https://api.example.com/v0/vnext/artifacts/generate/weekly-synthesis",
      "https://api.example.com/v0/vnext/artifacts/artifact-1/review",
      "https://api.example.com/v0/vnext/artifacts/artifact-1/quality-ratings",
      "https://api.example.com/v0/vnext/memories/memory-1/review",
      "https://api.example.com/v0/vnext/projects",
      "https://api.example.com/v0/vnext/projects/update-candidates",
      "https://api.example.com/v0/vnext/open-loops",
      "https://api.example.com/v0/vnext/open-loops/loop-1/review",
      "https://api.example.com/v0/vnext/settings/brain-charter?user_id=user-1",
      "https://api.example.com/v0/vnext/settings/brain-charter",
      "https://api.example.com/v0/vnext/scheduler/failures?user_id=user-1&limit=5",
      "https://api.example.com/v0/vnext/scheduler/workflows/daily_brief/run-now",
      "https://api.example.com/v0/vnext/scheduler/run-due",
      "https://api.example.com/v0/vnext/quality-evals?user_id=user-1&limit=5&artifact_id=artifact-1",
      "https://api.example.com/v0/vnext/agents/policy-telemetry?user_id=user-1",
      "https://api.example.com/v0/vnext/connectors/browser-clipper/capture",
      "https://api.example.com/v0/vnext/connectors/health?user_id=user-1",
      "https://api.example.com/v0/vnext/dogfooding?user_id=user-1",
      "https://api.example.com/v0/vnext/artifacts/artifact-1/insight-feedback",
    ]);
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock.mock.calls[13]?.[1]).toEqual(
      expect.objectContaining({ method: "PUT" }),
    );
    expect(fetchMock.mock.calls[15]?.[1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock.mock.calls[16]?.[1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock.mock.calls[19]?.[1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock.mock.calls[22]?.[1]).toEqual(
      expect.objectContaining({ method: "POST" }),
    );
    expect(JSON.parse(String(fetchMock.mock.calls[7]?.[1]?.body))).toEqual({
      user_id: "user-1",
      action: "assign_project",
      project_id: "project-1",
      reason: "Project review",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[11]?.[1]?.body))).toEqual({
      user_id: "user-1",
      action: "snooze",
      due_at: "2026-05-12T09:00:00Z",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[19]?.[1]?.body))).toEqual({
      user_id: "user-1",
      url: "https://example.com/live-capture",
      title: "Live capture",
      selected_text: "Fact: browser clips enter the review queue.",
      user_note: "Review this source.",
      domain: "professional",
      sensitivity: "private",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[22]?.[1]?.body))).toEqual({
      user_id: "user-1",
      useful_insight: "yes",
      surfaced_missed: "no",
      comments: "Grounded in captured evidence.",
    });
  });

  it("uses vNext source review, trace, and doctor endpoints", async () => {
    fetchMock.mockImplementation(
      async () =>
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );

    await reviewVNextSource("https://api.example.com", "source-1", {
      user_id: "user-1",
      action: "assign_project",
      title: "Reviewed source",
      domain: "project",
      sensitivity: "private",
      project_id: "project-1",
      review_note: "Reviewed in operator console.",
    });
    await getVNextSourceTrace("https://api.example.com", "source-1", "user-1");
    await getVNextArtifactTrace("https://api.example.com", "artifact-1", "user-1");
    await runVNextDoctor("https://api.example.com", {
      user_id: "user-1",
      fix_safe: true,
      ci: true,
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "https://api.example.com/v0/vnext/sources/source-1/review",
      "https://api.example.com/v0/vnext/traces/sources/source-1?user_id=user-1",
      "https://api.example.com/v0/vnext/traces/artifacts/artifact-1?user_id=user-1",
      "https://api.example.com/v0/vnext/doctor/run",
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      action: "assign_project",
      title: "Reviewed source",
      domain: "project",
      sensitivity: "private",
      project_id: "project-1",
      review_note: "Reviewed in operator console.",
    });
    expect(JSON.parse(String(fetchMock.mock.calls[3]?.[1]?.body))).toEqual({
      user_id: "user-1",
      fix_safe: true,
      ci: true,
    });
  });

  it("submits bounded inline confirmation actions", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "committed",
          write_mode: "confirm_inline",
          confirmation_id: "confirm-1",
          memory: { id: "memory-1" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await confirmVNextMemory("https://api.example.com", {
      user_id: "user-1",
      confirmation_id: "confirm-1",
      action: "edit",
      canonical_text: "Reviewed and corrected memory text.",
      rationale: "Reviewed in the operator console.",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/vnext/memories/confirm",
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      confirmation_id: "confirm-1",
      action: "edit",
      canonical_text: "Reviewed and corrected memory text.",
      rationale: "Reviewed in the operator console.",
    });
  });
});
