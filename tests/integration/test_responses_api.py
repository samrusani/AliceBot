from __future__ import annotations

import json
from uuid import UUID, uuid4

import anyio
import psycopg
import pytest

import apps.api.src.alicebot_api.main as main_module
import alicebot_api.response_generation as response_generation_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


def invoke_generate_response(payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    messages: list[dict[str, object]] = []
    encoded_body = json.dumps(payload).encode()
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}

        request_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v0/responses",
        "raw_path": b"/v0/responses",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    anyio.run(main_module.app, scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start_message["status"], json.loads(body)


def seed_response_thread(
    database_url: str,
    *,
    email: str = "owner@example.com",
    display_name: str = "Owner",
    agent_profile_id: str = "assistant_default",
) -> dict[str, object]:
    user_id = uuid4()

    with user_connection(database_url, user_id) as conn:
        store = ContinuityStore(conn)
        store.create_user(user_id, email, display_name)
        thread = store.create_thread("Response thread", agent_profile_id=agent_profile_id)
        session = store.create_session(thread["id"], status="active")
        prior_event = store.append_event(
            thread["id"],
            session["id"],
            "message.user",
            {"text": "Remember that I like oat milk."},
        )
        memory = store.create_memory(
            memory_key="user.preference.coffee",
            value={"likes": "oat milk"},
            status="active",
            source_event_ids=[str(prior_event["id"])],
        )

    return {
        "user_id": user_id,
        "thread_id": thread["id"],
        "session_id": session["id"],
        "prior_event_id": prior_event["id"],
        "memory_id": memory["id"],
    }


def test_generate_response_persists_user_and_assistant_events_and_trace_metadata(
    migrated_database_urls,
    monkeypatch,
) -> None:
    seeded = seed_response_thread(
        migrated_database_urls["app"],
        agent_profile_id="coach_default",
    )
    captured: dict[str, object] = {}

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
        captured["settings"] = settings
        captured["request_payload"] = request.as_payload()
        return response_generation_module.ModelInvocationResponse(
            provider="openai_responses",
            model="gpt-5-mini",
            response_id="resp_123",
            finish_reason="completed",
            output_text="You prefer oat milk.",
            usage={"input_tokens": 20, "output_tokens": 6, "total_tokens": 26},
        )

    monkeypatch.setattr(response_generation_module, "invoke_model", fake_invoke_model)

    status_code, payload = invoke_generate_response(
        {
            "user_id": str(seeded["user_id"]),
            "thread_id": str(seeded["thread_id"]),
            "message": "What do I usually take in coffee?",
        }
    )

    assert status_code == 200
    assert payload["metadata"] == {"agent_profile_id": "coach_default"}
    assert payload["assistant"] == {
        "event_id": payload["assistant"]["event_id"],
        "sequence_no": 3,
        "text": "You prefer oat milk.",
        "model_provider": "openai_responses",
        "model": "gpt-5-mini",
    }
    assert payload["trace"]["compile_trace_event_count"] > 0
    assert payload["trace"]["response_trace_event_count"] == 2
    assert captured["request_payload"]["tool_choice"] == "none"
    assert captured["request_payload"]["tools"] == []
    assert captured["request_payload"]["store"] is False
    assert captured["request_payload"]["sections"] == [
        "system",
        "developer",
        "context",
        "conversation",
    ]

    with user_connection(migrated_database_urls["app"], seeded["user_id"]) as conn:
        store = ContinuityStore(conn)
        events = store.list_thread_events(seeded["thread_id"])
        compile_trace = store.get_trace(UUID(payload["trace"]["compile_trace_id"]))
        response_trace = store.get_trace(UUID(payload["trace"]["response_trace_id"]))
        response_trace_events = store.list_trace_events(UUID(payload["trace"]["response_trace_id"]))

    assert [event["sequence_no"] for event in events] == [1, 2, 3]
    assert [event["kind"] for event in events] == [
        "message.user",
        "message.user",
        "message.assistant",
    ]
    assert events[1]["payload"] == {"text": "What do I usually take in coffee?"}
    assert events[2]["payload"] == {
        "text": "You prefer oat milk.",
        "model": {
            "provider": "openai_responses",
            "model": "gpt-5-mini",
            "response_id": "resp_123",
            "finish_reason": "completed",
            "usage": {"input_tokens": 20, "output_tokens": 6, "total_tokens": 26},
        },
        "prompt": {
            "assembly_version": "prompt_assembly_v0",
            "prompt_sha256": events[2]["payload"]["prompt"]["prompt_sha256"],
            "section_order": ["system", "developer", "context", "conversation"],
        },
    }
    assert compile_trace["kind"] == "context.compile"
    assert response_trace["kind"] == "response.generate"
    assert response_trace["compiler_version"] == "response_generation_v0"
    assert [event["kind"] for event in response_trace_events] == [
        "response.prompt.assembled",
        "response.model.completed",
    ]
    assert response_trace_events[0]["payload"]["compile_trace_id"] == payload["trace"]["compile_trace_id"]
    assert response_trace_events[1]["payload"] == {
        "provider": "openai_responses",
        "model": "gpt-5-mini",
        "tool_choice": "none",
        "tools_enabled": False,
        "response_id": "resp_123",
        "finish_reason": "completed",
        "output_text_char_count": len("You prefer oat milk."),
        "usage": {"input_tokens": 20, "output_tokens": 6, "total_tokens": 26},
        "error_message": None,
    }

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with pytest.raises(psycopg.Error, match="append-only"):
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE events SET kind = 'message.mutated' WHERE id = %s",
                    (UUID(payload["assistant"]["event_id"]),),
                )


def test_generate_response_persists_optional_cached_token_telemetry_in_event_and_trace(
    migrated_database_urls,
    monkeypatch,
) -> None:
    seeded = seed_response_thread(migrated_database_urls["app"])

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
        del request
        return response_generation_module.ModelInvocationResponse(
            provider="openai_responses",
            model="gpt-5-mini",
            response_id="resp_cached",
            finish_reason="completed",
            output_text="You prefer oat milk.",
            usage={
                "input_tokens": 20,
                "output_tokens": 6,
                "total_tokens": 26,
                "cached_input_tokens": 16,
            },
        )

    monkeypatch.setattr(response_generation_module, "invoke_model", fake_invoke_model)

    status_code, payload = invoke_generate_response(
        {
            "user_id": str(seeded["user_id"]),
            "thread_id": str(seeded["thread_id"]),
            "message": "What do I usually take in coffee?",
        }
    )

    assert status_code == 200
    assert payload["metadata"] == {"agent_profile_id": "assistant_default"}

    with user_connection(migrated_database_urls["app"], seeded["user_id"]) as conn:
        store = ContinuityStore(conn)
        events = store.list_thread_events(seeded["thread_id"])
        response_trace_events = store.list_trace_events(UUID(payload["trace"]["response_trace_id"]))

    assert events[2]["payload"]["model"]["usage"] == {
        "input_tokens": 20,
        "output_tokens": 6,
        "total_tokens": 26,
        "cached_input_tokens": 16,
    }
    assert response_trace_events[1]["payload"]["usage"] == {
        "input_tokens": 20,
        "output_tokens": 6,
        "total_tokens": 26,
        "cached_input_tokens": 16,
    }


def test_generate_response_returns_clean_failure_without_persisting_assistant_event(
    migrated_database_urls,
    monkeypatch,
) -> None:
    seeded = seed_response_thread(migrated_database_urls["app"])

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
    monkeypatch.setattr(
        response_generation_module,
        "invoke_model",
        lambda **_kwargs: (_ for _ in ()).throw(
            response_generation_module.ModelInvocationError("upstream timeout")
        ),
    )

    status_code, payload = invoke_generate_response(
        {
            "user_id": str(seeded["user_id"]),
            "thread_id": str(seeded["thread_id"]),
            "message": "What do I usually take in coffee?",
        }
    )

    assert status_code == 502
    assert payload["detail"] == "upstream timeout"
    assert payload["metadata"] == {"agent_profile_id": "assistant_default"}
    assert payload["trace"]["compile_trace_event_count"] > 0
    assert payload["trace"]["response_trace_event_count"] == 2

    with user_connection(migrated_database_urls["app"], seeded["user_id"]) as conn:
        store = ContinuityStore(conn)
        events = store.list_thread_events(seeded["thread_id"])
        response_trace_events = store.list_trace_events(UUID(payload["trace"]["response_trace_id"]))

    assert [event["sequence_no"] for event in events] == [1, 2]
    assert [event["kind"] for event in events] == ["message.user", "message.user"]
    assert events[-1]["payload"] == {"text": "What do I usually take in coffee?"}
    assert [event["kind"] for event in response_trace_events] == [
        "response.prompt.assembled",
        "response.model.failed",
    ]
    assert response_trace_events[1]["payload"] == {
        "provider": "openai_responses",
        "model": "gpt-5-mini",
        "tool_choice": "none",
        "tools_enabled": False,
        "response_id": None,
        "finish_reason": "incomplete",
        "output_text_char_count": 0,
        "usage": {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        "error_message": "upstream timeout",
    }


def test_generate_response_respects_per_user_isolation(migrated_database_urls, monkeypatch) -> None:
    owner = seed_response_thread(migrated_database_urls["app"])
    intruder = seed_response_thread(
        migrated_database_urls["app"],
        email="intruder@example.com",
        display_name="Intruder",
    )
    captured = {"invoke_model_called": False}

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

    def fake_invoke_model(**_kwargs):
        captured["invoke_model_called"] = True
        raise AssertionError("invoke_model should not be called for cross-user access")

    monkeypatch.setattr(response_generation_module, "invoke_model", fake_invoke_model)

    status_code, payload = invoke_generate_response(
        {
            "user_id": str(intruder["user_id"]),
            "thread_id": str(owner["thread_id"]),
            "message": "Tell me their preferences.",
        }
    )

    assert status_code == 404
    assert payload == {"detail": "get_thread did not return a row from the database"}
    assert captured["invoke_model_called"] is False

    with user_connection(migrated_database_urls["app"], owner["user_id"]) as conn:
        owner_events = ContinuityStore(conn).list_thread_events(owner["thread_id"])

    assert [event["sequence_no"] for event in owner_events] == [1]
