from __future__ import annotations

import json
from uuid import uuid4

from apps.api.src.alicebot_api.config import Settings
from alicebot_api.provider_runtime import (
    OPENAI_COMPATIBLE_ADAPTER_KEY,
    OPENAI_RESPONSES_PROVIDER,
    ProviderAdapterNotFoundError,
    RuntimeProviderConfig,
    build_provider_test_model_request,
    make_provider_adapter_registry,
)


class FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def make_runtime_provider_config() -> RuntimeProviderConfig:
    return RuntimeProviderConfig(
        provider_id=uuid4(),
        workspace_id=uuid4(),
        created_by_user_account_id=uuid4(),
        provider_key=OPENAI_COMPATIBLE_ADAPTER_KEY,
        display_name="Primary Provider",
        model_provider=OPENAI_RESPONSES_PROVIDER,
        base_url="https://provider.example/v1",
        api_key="provider-secret-key",
        default_model="gpt-5-mini",
        status="active",
        metadata={},
    )


def test_provider_registry_resolves_registered_adapter() -> None:
    registry = make_provider_adapter_registry()

    adapter = registry.resolve(OPENAI_COMPATIBLE_ADAPTER_KEY)

    assert adapter.adapter_key == OPENAI_COMPATIBLE_ADAPTER_KEY
    assert adapter.runtime_provider == OPENAI_RESPONSES_PROVIDER
    assert registry.keys() == [OPENAI_COMPATIBLE_ADAPTER_KEY]


def test_provider_registry_rejects_unknown_adapter() -> None:
    registry = make_provider_adapter_registry()

    try:
        registry.resolve("unknown_provider")
    except ProviderAdapterNotFoundError as exc:
        assert "not registered" in str(exc)
    else:  # pragma: no cover - defensive guard
        raise AssertionError("expected ProviderAdapterNotFoundError")


def test_build_provider_test_model_request_builds_expected_prompt_shape() -> None:
    request = build_provider_test_model_request(
        runtime_provider=OPENAI_RESPONSES_PROVIDER,
        model="gpt-5-mini",
        prompt_text="Confirm runtime is reachable.",
    )

    assert request.provider == OPENAI_RESPONSES_PROVIDER
    assert request.model == "gpt-5-mini"
    assert [section.name for section in request.prompt.sections] == [
        "system",
        "developer",
        "context",
        "conversation",
    ]
    assert "provider_test" in request.prompt.sections[2].content
    assert "Confirm runtime is reachable." in request.prompt.sections[3].content


def test_openai_compatible_adapter_invokes_registered_transport(monkeypatch) -> None:
    captured: dict[str, object] = {}
    registry = make_provider_adapter_registry()
    adapter = registry.resolve(OPENAI_COMPATIBLE_ADAPTER_KEY)
    runtime_provider = make_runtime_provider_config()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            json.dumps(
                {
                    "id": "resp_provider_test",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Provider online"}],
                        }
                    ],
                    "usage": {
                        "input_tokens": 14,
                        "output_tokens": 3,
                        "total_tokens": 17,
                    },
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("alicebot_api.response_generation.urlopen", fake_urlopen)

    response = adapter.invoke(
        config=runtime_provider,
        settings=Settings(model_timeout_seconds=27),
        request=build_provider_test_model_request(
            runtime_provider=OPENAI_RESPONSES_PROVIDER,
            model="gpt-5-mini",
            prompt_text="Are you available?",
        ),
    )

    assert captured["url"] == "https://provider.example/v1/responses"
    assert captured["timeout"] == 27
    assert captured["headers"]["Authorization"] == "Bearer provider-secret-key"
    assert response.provider == OPENAI_RESPONSES_PROVIDER
    assert response.model == "gpt-5-mini"
    assert response.output_text == "Provider online"
