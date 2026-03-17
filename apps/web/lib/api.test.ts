import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  combinePageModes,
  getTraceDetail,
  getTraceEvents,
  listTraces,
  pageModeLabel,
  resolveApproval,
  submitApprovalRequest,
} from "./api";

describe("api helpers", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("combines live and fixture sources into a mixed page mode", () => {
    expect(combinePageModes("live", "fixture")).toBe("mixed");
    expect(pageModeLabel("mixed")).toBe("Mixed fallback");
  });

  it("posts governed approval requests to the shipped endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          request: {
            thread_id: "thread-1",
            tool_id: "tool-1",
            action: "place_order",
            scope: "supplements",
            domain_hint: "ecommerce",
            risk_hint: "purchase",
            attributes: { quantity: "1" },
          },
          decision: "approval_required",
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
          reasons: [],
          task: {
            id: "task-1",
            thread_id: "thread-1",
            tool_id: "tool-1",
            status: "pending_approval",
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
            latest_approval_id: "approval-1",
            latest_execution_id: null,
            created_at: "2026-03-17T00:00:00Z",
            updated_at: "2026-03-17T00:00:00Z",
          },
          approval: null,
          routing_trace: {
            trace_id: "route-trace-1",
            trace_event_count: 3,
          },
          trace: {
            trace_id: "request-trace-1",
            trace_event_count: 6,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await submitApprovalRequest("https://api.example.com", {
      user_id: "user-1",
      thread_id: "thread-1",
      tool_id: "tool-1",
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: { quantity: "1" },
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/approvals/requests",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      thread_id: "thread-1",
      tool_id: "tool-1",
      action: "place_order",
      scope: "supplements",
      domain_hint: "ecommerce",
      risk_hint: "purchase",
      attributes: { quantity: "1" },
    });
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
    ).rejects.toEqual(expect.objectContaining<ApiError>({ message: "approval conflict", status: 409 }));

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/approvals/approval-1/approve",
      expect.objectContaining({
        method: "POST",
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
});
