import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  admitMemory,
  ApiError,
  combinePageModes,
  connectCalendarAccount,
  connectGmailAccount,
  createThread,
  deriveThreadWorkflowState,
  createOpenLoop,
  getCalendarAccountDetail,
  getGmailAccountDetail,
  getOpenLoopDetail,
  getTaskArtifactDetail,
  getTaskWorkspaceDetail,
  getEntityDetail,
  getMemoryDetail,
  getMemoryEvaluationSummary,
  getMemoryRevisions,
  getTaskSteps,
  getThreadDetail,
  getThreadEvents,
  getThreadSessions,
  executeApproval,
  ingestCalendarEvent,
  ingestGmailMessage,
  listCalendarAccounts,
  listCalendarEvents,
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
  updateOpenLoopStatus,
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
          workspace: {
            id: "workspace-1",
            task_id: "task-1",
            status: "active",
            local_path: "/tmp/workspace/task-1",
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
    await getTaskWorkspaceDetail("https://api.example.com", "workspace-1", "user-1");
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
        "https://api.example.com/v0/task-workspaces/workspace-1?user_id=user-1",
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
      expect.objectContaining<ApiError>({
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
});
