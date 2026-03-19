from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

import apps.api.src.alicebot_api.main as main_module
import alicebot_api.response_generation as response_generation_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
import tests.integration.test_context_compile as context_compile_api
import tests.integration.test_memory_admission as memory_admission_api
import tests.integration.test_mvp_magnesium_reorder_flow as magnesium_flow_api
import tests.integration.test_proxy_execution_api as proxy_execution_api
import tests.integration.test_responses_api as responses_api
import tests.integration.test_traces_api as traces_api


INDUCED_FAILURE_ENV = "MVP_ACCEPTANCE_INDUCED_FAILURE_SCENARIO"


def _extract_context_payload_from_model_request(request: Any) -> dict[str, Any]:
    for section in request.prompt.sections:
        if section.name == "context":
            return json.loads(section.content)
    raise AssertionError("model request did not include a context section")


def _get_memory_by_key(context_payload: dict[str, Any], memory_key: str) -> dict[str, Any]:
    return next(memory for memory in context_payload["memories"] if memory["memory_key"] == memory_key)


def _assert_not_induced_failure(scenario: str) -> None:
    requested_scenario = os.getenv(INDUCED_FAILURE_ENV, "").strip()
    if requested_scenario == scenario:
        raise AssertionError(
            f"induced failure requested for scenario '{scenario}' via {INDUCED_FAILURE_ENV}"
        )


def test_acceptance_response_path_uses_admitted_memory_and_preference_correction(
    migrated_database_urls,
    monkeypatch,
) -> None:
    seeded = responses_api.seed_response_thread(migrated_database_urls["app"])
    captured_context_payloads: list[dict[str, Any]] = []

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            model_provider="openai_responses",
            model_name="gpt-5-mini",
            model_api_key="test-key",
        ),
    )

    def fake_invoke_model(*, settings, request):
        del settings
        context_payload = _extract_context_payload_from_model_request(request)
        captured_context_payloads.append(context_payload)
        coffee_memory = _get_memory_by_key(context_payload, "user.preference.coffee")
        likes_value = coffee_memory["value"]["likes"]
        return response_generation_module.ModelInvocationResponse(
            provider="openai_responses",
            model="gpt-5-mini",
            response_id="resp_acceptance",
            finish_reason="completed",
            output_text=f"You prefer {likes_value}.",
            usage={"input_tokens": 14, "output_tokens": 6, "total_tokens": 20},
        )

    monkeypatch.setattr(response_generation_module, "invoke_model", fake_invoke_model)

    first_admit_status, first_admit_payload = memory_admission_api.invoke_admit_memory(
        {
            "user_id": str(seeded["user_id"]),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk latte"},
            "source_event_ids": [str(seeded["prior_event_id"])],
        }
    )
    assert first_admit_status == 200
    assert first_admit_payload["decision"] == "UPDATE"

    first_response_status, first_response_payload = responses_api.invoke_generate_response(
        {
            "user_id": str(seeded["user_id"]),
            "thread_id": str(seeded["thread_id"]),
            "message": "What should I use in coffee?",
        }
    )
    assert first_response_status == 200
    assert first_response_payload["assistant"]["text"] == "You prefer oat milk latte."
    assert first_response_payload["trace"]["compile_trace_event_count"] > 0
    first_context_memory = _get_memory_by_key(
        captured_context_payloads[-1],
        "user.preference.coffee",
    )
    assert first_context_memory["value"] == {"likes": "oat milk latte"}
    assert first_context_memory["source_event_ids"] == [str(seeded["prior_event_id"])]

    second_admit_status, second_admit_payload = memory_admission_api.invoke_admit_memory(
        {
            "user_id": str(seeded["user_id"]),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "almond milk"},
            "source_event_ids": [str(seeded["prior_event_id"])],
        }
    )
    assert second_admit_status == 200
    assert second_admit_payload["decision"] == "UPDATE"

    compile_status, compile_payload = context_compile_api.invoke_compile_context(
        {
            "user_id": str(seeded["user_id"]),
            "thread_id": str(seeded["thread_id"]),
        }
    )
    assert compile_status == 200
    compiled_memory = _get_memory_by_key(
        compile_payload["context_pack"],
        "user.preference.coffee",
    )
    assert compiled_memory["value"] == {"likes": "almond milk"}
    assert compiled_memory["source_event_ids"] == [str(seeded["prior_event_id"])]

    second_response_status, second_response_payload = responses_api.invoke_generate_response(
        {
            "user_id": str(seeded["user_id"]),
            "thread_id": str(seeded["thread_id"]),
            "message": "Confirm the corrected coffee preference.",
        }
    )
    assert second_response_status == 200
    assert second_response_payload["assistant"]["text"] == "You prefer almond milk."
    assert second_response_payload["trace"]["response_trace_event_count"] == 2
    second_context_memory = _get_memory_by_key(
        captured_context_payloads[-1],
        "user.preference.coffee",
    )
    assert second_context_memory["value"] == {"likes": "almond milk"}

    _assert_not_induced_failure("response_memory")


def test_acceptance_approval_lifecycle_resolution_execution_and_trace_availability(
    migrated_database_urls,
    monkeypatch,
) -> None:
    owner = proxy_execution_api.seed_user(migrated_database_urls["app"], email="owner@example.com")
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url=migrated_database_urls["app"]))

    tool_id = proxy_execution_api.create_tool_and_policy(
        migrated_database_urls["app"],
        user_id=owner["user_id"],
        tool_key="proxy.echo",
    )
    create_status, create_payload = proxy_execution_api.create_pending_approval(
        user_id=owner["user_id"],
        thread_id=owner["thread_id"],
        tool_id=tool_id,
    )
    assert create_status == 200
    assert create_payload["decision"] == "approval_required"
    assert create_payload["approval"]["status"] == "pending"
    assert create_payload["task"]["latest_approval_id"] == create_payload["approval"]["id"]

    approve_status, approve_payload = proxy_execution_api.invoke_request(
        "POST",
        f"/v0/approvals/{create_payload['approval']['id']}/approve",
        payload={"user_id": str(owner["user_id"])},
    )
    assert approve_status == 200
    assert approve_payload["approval"]["status"] == "approved"

    execute_status, execute_payload = proxy_execution_api.invoke_request(
        "POST",
        f"/v0/approvals/{create_payload['approval']['id']}/execute",
        payload={"user_id": str(owner["user_id"])},
    )
    assert execute_status == 200
    assert execute_payload["approval"]["id"] == create_payload["approval"]["id"]
    assert execute_payload["approval"]["status"] == "approved"
    assert execute_payload["result"]["status"] == "completed"
    assert isinstance(execute_payload["events"]["request_event_id"], str)
    assert isinstance(execute_payload["events"]["result_event_id"], str)

    with user_connection(migrated_database_urls["app"], owner["user_id"]) as conn:
        store = ContinuityStore(conn)
        tasks = store.list_tasks()
        task_steps = store.list_task_steps_for_task(tasks[0]["id"])
        tool_executions = store.list_tool_executions()

    assert len(tasks) == 1
    assert len(task_steps) == 1
    assert len(tool_executions) == 1
    assert tasks[0]["latest_approval_id"] == UUID(create_payload["approval"]["id"])
    assert tasks[0]["latest_execution_id"] == tool_executions[0]["id"]
    assert tool_executions[0]["approval_id"] == UUID(create_payload["approval"]["id"])
    assert tool_executions[0]["task_step_id"] == task_steps[0]["id"]

    trace_list_status, trace_list_payload = traces_api.invoke_request(
        "GET",
        "/v0/traces",
        query_params={"user_id": str(owner["user_id"])},
    )
    assert trace_list_status == 200

    trace_ids = {item["id"] for item in trace_list_payload["items"]}
    approval_trace_id = create_payload["trace"]["trace_id"]
    execution_trace_id = execute_payload["trace"]["trace_id"]
    assert approval_trace_id in trace_ids
    assert execution_trace_id in trace_ids

    trace_detail_status, trace_detail_payload = traces_api.invoke_request(
        "GET",
        f"/v0/traces/{execution_trace_id}",
        query_params={"user_id": str(owner["user_id"])},
    )
    trace_events_status, trace_events_payload = traces_api.invoke_request(
        "GET",
        f"/v0/traces/{execution_trace_id}/events",
        query_params={"user_id": str(owner["user_id"])},
    )
    assert trace_detail_status == 200
    assert trace_detail_payload["trace"]["kind"] == "tool.proxy.execute"
    assert trace_events_status == 200
    assert trace_events_payload["summary"]["total_count"] >= 1
    event_kinds = [event["kind"] for event in trace_events_payload["items"]]
    assert "tool.proxy.execute.request" in event_kinds
    assert "tool.proxy.execute.summary" in event_kinds

    _assert_not_induced_failure("approval_execution")


def test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence(
    migrated_database_urls,
    monkeypatch,
) -> None:
    magnesium_flow_api.test_mvp_magnesium_reorder_flow_proves_ship_gate_evidence(
        migrated_database_urls,
        monkeypatch,
    )
    _assert_not_induced_failure("magnesium_reorder")
