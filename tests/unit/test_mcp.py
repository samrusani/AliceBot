from __future__ import annotations

from io import BytesIO
from uuid import UUID

import pytest

import alicebot_api.mcp_server as mcp_server
from alicebot_api.mcp_tools import MCPRuntimeContext, MCPToolError, MCPToolNotFoundError, call_mcp_tool, list_mcp_tools


def test_mcp_tool_surface_is_adr_aligned_and_deterministic() -> None:
    tools = list_mcp_tools()
    names = [tool["name"] for tool in tools]
    assert names == [
        "alice_capture",
        "alice_capture_candidates",
        "alice_commit_captures",
        "alice_memory_mutations_generate",
        "alice_memory_mutations_list_candidates",
        "alice_memory_mutations_commit",
        "alice_memory_mutations_list_operations",
        "alice_recall",
        "alice_recall_debug",
        "alice_state_at",
        "alice_resume",
        "alice_resume_debug",
        "alice_task_brief",
        "alice_task_brief_show",
        "alice_task_brief_compare",
        "alice_retrieval_trace",
        "alice_prefetch_context",
        "alice_open_loops",
        "alice_recent_decisions",
        "alice_recent_changes",
        "alice_timeline",
        "alice_review_queue",
        "alice_review_apply",
        "alice_contradictions_detect",
        "alice_contradictions_list",
        "alice_contradictions_resolve",
        "alice_trust_signals",
        "alice_memory_review",
        "alice_memory_correct",
        "alice_explain",
        "alice_artifact_inspect",
        "alice_context_pack",
    ]

    for tool in tools:
        assert isinstance(tool["inputSchema"], dict)
        assert tool["inputSchema"].get("type") == "object"
        assert tool["inputSchema"].get("additionalProperties") is False


def test_call_mcp_tool_rejects_unknown_tool() -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    with pytest.raises(MCPToolNotFoundError, match="unknown tool"):
        call_mcp_tool(context, name="alice_nonexistent", arguments={})


def test_call_mcp_tool_requires_object_arguments() -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    with pytest.raises(MCPToolError, match="tool arguments must be a JSON object"):
        call_mcp_tool(context, name="alice_recall", arguments=["not-a-json-object"])


def test_mcp_server_initialize_and_tools_list(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    server = mcp_server.MCPServer(context=context, input_stream=BytesIO(), output_stream=BytesIO())

    initialize_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }
    )
    assert initialize_response is not None
    assert initialize_response["result"]["protocolVersion"] == "2024-11-05"
    assert initialize_response["result"]["serverInfo"]["name"] == "alice-core-mcp"

    monkeypatch.setattr(
        mcp_server,
        "list_mcp_tools",
        lambda: [{"name": "alice_recall", "description": "Recall", "inputSchema": {"type": "object"}}],
    )
    list_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
    )
    assert list_response is not None
    assert list_response["result"]["tools"] == [
        {"name": "alice_recall", "description": "Recall", "inputSchema": {"type": "object"}}
    ]


def test_mcp_server_tools_call_success_and_error_paths(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    server = mcp_server.MCPServer(context=context, input_stream=BytesIO(), output_stream=BytesIO())

    monkeypatch.setattr(mcp_server, "call_mcp_tool", lambda *_args, **_kwargs: {"ok": True})
    success_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "alice_recall", "arguments": {}},
        }
    )
    assert success_response is not None
    assert success_response["result"]["isError"] is False
    assert success_response["result"]["structuredContent"] == {"ok": True}

    def raise_tool_error(*_args, **_kwargs):
        raise MCPToolError("invalid input")

    monkeypatch.setattr(mcp_server, "call_mcp_tool", raise_tool_error)
    error_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "alice_recall", "arguments": {}},
        }
    )
    assert error_response is not None
    assert error_response["result"]["isError"] is True
    assert error_response["result"]["content"][0]["text"] == "invalid input"
