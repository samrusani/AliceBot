import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  combinePageModes,
  createThread,
  deriveThreadWorkflowState,
  getEntityDetail,
  getMemoryDetail,
  getMemoryEvaluationSummary,
  getMemoryRevisions,
  getTaskSteps,
  getThreadDetail,
  getThreadEvents,
  getThreadSessions,
  executeApproval,
  listEntities,
  listEntityEdges,
  listMemories,
  listMemoryLabels,
  listMemoryReviewQueue,
  getToolExecution,
  getTraceDetail,
  getTraceEvents,
  listThreads,
  listTraces,
  pageModeLabel,
  resolveApproval,
  shouldExpectThreadExecutionReview,
  submitAssistantResponse,
  submitApprovalRequest,
  submitMemoryLabel,
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

  it("does not borrow an older unrelated execution from the same thread", () => {
    const approval = {
      id: "approval-new",
      thread_id: "thread-1",
      task_step_id: "step-new",
      status: "approved",
      request: {
        thread_id: "thread-1",
        tool_id: "tool-1",
        action: "place_order",
        scope: "supplements",
        domain_hint: "ecommerce",
        risk_hint: "purchase",
        attributes: {},
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
          trace_id: "trace-approval-new",
          trace_event_count: 3,
        },
      },
      created_at: "2026-03-18T10:00:00Z",
      resolution: {
        resolved_at: "2026-03-18T10:05:00Z",
        resolved_by_user_id: "user-1",
      },
    };

    const olderApproval = {
      ...approval,
      id: "approval-old",
      task_step_id: "step-old",
      created_at: "2026-03-17T10:00:00Z",
    };

    const task = {
      id: "task-new",
      thread_id: "thread-1",
      tool_id: "tool-1",
      status: "approved",
      request: approval.request,
      tool: approval.tool,
      latest_approval_id: "approval-new",
      latest_execution_id: null,
      created_at: "2026-03-18T10:00:00Z",
      updated_at: "2026-03-18T10:05:00Z",
    };

    const olderTask = {
      ...task,
      id: "task-old",
      latest_approval_id: "approval-old",
      latest_execution_id: "execution-old",
      created_at: "2026-03-17T10:00:00Z",
      updated_at: "2026-03-17T10:10:00Z",
    };

    const olderExecution = {
      id: "execution-old",
      approval_id: "approval-old",
      task_step_id: "step-old",
      thread_id: "thread-1",
      tool_id: "tool-1",
      trace_id: "trace-execution-old",
      request_event_id: "request-event-old",
      result_event_id: "result-event-old",
      status: "completed",
      handler_key: "proxy.echo",
      request: approval.request,
      tool: approval.tool,
      result: {
        handler_key: "proxy.echo",
        status: "completed",
        output: { ok: true },
        reason: null,
      },
      executed_at: "2026-03-17T10:10:00Z",
    };

    const workflow = deriveThreadWorkflowState(
      "thread-1",
      [olderApproval, approval],
      [olderTask, task],
      [olderExecution],
    );

    expect(workflow.approval?.id).toBe("approval-new");
    expect(workflow.task?.id).toBe("task-new");
    expect(workflow.execution).toBeNull();
    expect(shouldExpectThreadExecutionReview(workflow.approval, workflow.task)).toBe(true);
  });

  it("returns explicitly linked execution when the selected task carries latest_execution_id", () => {
    const approval = {
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
        attributes: {},
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
          trace_id: "trace-approval-1",
          trace_event_count: 3,
        },
      },
      created_at: "2026-03-18T10:00:00Z",
      resolution: {
        resolved_at: "2026-03-18T10:05:00Z",
        resolved_by_user_id: "user-1",
      },
    };

    const task = {
      id: "task-1",
      thread_id: "thread-1",
      tool_id: "tool-1",
      status: "executed",
      request: approval.request,
      tool: approval.tool,
      latest_approval_id: "approval-1",
      latest_execution_id: "execution-1",
      created_at: "2026-03-18T10:00:00Z",
      updated_at: "2026-03-18T10:06:00Z",
    };

    const execution = {
      id: "execution-1",
      approval_id: "approval-1",
      task_step_id: "step-1",
      thread_id: "thread-1",
      tool_id: "tool-1",
      trace_id: "trace-execution-1",
      request_event_id: "request-event-1",
      result_event_id: "result-event-1",
      status: "completed",
      handler_key: "proxy.echo",
      request: approval.request,
      tool: approval.tool,
      result: {
        handler_key: "proxy.echo",
        status: "completed",
        output: { ok: true },
        reason: null,
      },
      executed_at: "2026-03-18T10:06:00Z",
    };

    const workflow = deriveThreadWorkflowState("thread-1", [approval], [task], [execution]);

    expect(workflow.execution?.id).toBe("execution-1");
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

  it("posts assistant messages to the shipped response endpoint", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          assistant: {
            event_id: "assistant-event-1",
            sequence_no: 3,
            text: "You prefer oat milk.",
            model_provider: "openai_responses",
            model: "gpt-5-mini",
          },
          trace: {
            compile_trace_id: "compile-trace-1",
            compile_trace_event_count: 3,
            response_trace_id: "response-trace-1",
            response_trace_event_count: 2,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await submitAssistantResponse("https://api.example.com", {
      user_id: "user-1",
      thread_id: "thread-1",
      message: "What do I usually take in coffee?",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v0/responses",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      thread_id: "thread-1",
      message: "What do I usually take in coffee?",
    });
  });

  it("uses the shipped continuity endpoints for thread create and review", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            thread: {
              id: "thread-1",
              title: "Gamma thread",
              created_at: "2026-03-17T10:00:00Z",
              updated_at: "2026-03-17T10:00:00Z",
            },
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [
              {
                id: "thread-1",
                title: "Gamma thread",
                created_at: "2026-03-17T10:00:00Z",
                updated_at: "2026-03-17T10:00:00Z",
              },
            ],
            summary: {
              total_count: 1,
              order: ["created_at_desc", "id_desc"],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            thread: {
              id: "thread-1",
              title: "Gamma thread",
              created_at: "2026-03-17T10:00:00Z",
              updated_at: "2026-03-17T10:00:00Z",
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [
              {
                id: "session-1",
                thread_id: "thread-1",
                status: "active",
                started_at: "2026-03-17T10:00:00Z",
                ended_at: null,
                created_at: "2026-03-17T10:00:00Z",
              },
            ],
            summary: {
              thread_id: "thread-1",
              total_count: 1,
              order: ["started_at_asc", "created_at_asc", "id_asc"],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [
              {
                id: "event-1",
                thread_id: "thread-1",
                session_id: "session-1",
                sequence_no: 1,
                kind: "message.user",
                payload: { text: "Hello" },
                created_at: "2026-03-17T10:00:00Z",
              },
            ],
            summary: {
              thread_id: "thread-1",
              total_count: 1,
              order: ["sequence_no_asc"],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    await createThread("https://api.example.com", {
      user_id: "user-1",
      title: "Gamma thread",
    });
    await listThreads("https://api.example.com", "user-1");
    await getThreadDetail("https://api.example.com", "thread-1", "user-1");
    await getThreadSessions("https://api.example.com", "thread-1", "user-1");
    await getThreadEvents("https://api.example.com", "thread-1", "user-1");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "https://api.example.com/v0/threads",
      "https://api.example.com/v0/threads?user_id=user-1",
      "https://api.example.com/v0/threads/thread-1?user_id=user-1",
      "https://api.example.com/v0/threads/thread-1/sessions?user_id=user-1",
      "https://api.example.com/v0/threads/thread-1/events?user_id=user-1",
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      user_id: "user-1",
      title: "Gamma thread",
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
    await listMemoryReviewQueue("https://api.example.com", "user-1", 3);
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
        "https://api.example.com/v0/memories/review-queue?user_id=user-1&limit=3",
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
});
