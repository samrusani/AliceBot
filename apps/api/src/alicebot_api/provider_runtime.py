from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Protocol, TypedDict
from uuid import UUID

from alicebot_api.config import Settings
from alicebot_api.contracts import (
    ModelInvocationRequest,
    ModelInvocationResponse,
    PromptAssemblyResult,
    PromptSection,
)
from alicebot_api.response_generation import (
    ModelInvocationError,
    OpenAICompatibleTransportConfig,
    invoke_openai_compatible_model,
)
from alicebot_api.provider_secrets import resolve_provider_api_key
from alicebot_api.store import JsonObject

OPENAI_COMPATIBLE_ADAPTER_KEY = "openai_compatible"
OPENAI_RESPONSES_PROVIDER = "openai_responses"
PROVIDER_CAPABILITY_VERSION_V1 = "provider_capability_v1"


class ProviderRuntimeError(RuntimeError):
    """Base error for provider-runtime operations."""


class ProviderAdapterNotFoundError(ProviderRuntimeError):
    """Raised when no adapter is registered for a provider key."""


class ProviderCapabilitySnapshot(TypedDict):
    capability_version: str
    adapter_key: str
    runtime_provider: str
    supports_text_input: bool
    supports_text_output: bool
    supports_tool_calls: bool
    supports_streaming: bool
    supports_store: bool
    supports_vision_input: bool
    supports_audio_input: bool


@dataclass(frozen=True, slots=True)
class RuntimeProviderConfig:
    provider_id: UUID
    workspace_id: UUID
    created_by_user_account_id: UUID
    provider_key: str
    display_name: str
    model_provider: str
    base_url: str
    api_key: str
    default_model: str
    status: str
    metadata: JsonObject

    @classmethod
    def from_row(cls, row: dict[str, object]) -> RuntimeProviderConfig:
        return cls(
            provider_id=row["id"],  # type: ignore[arg-type]
            workspace_id=row["workspace_id"],  # type: ignore[arg-type]
            created_by_user_account_id=row["created_by_user_account_id"],  # type: ignore[arg-type]
            provider_key=str(row["provider_key"]),
            display_name=str(row["display_name"]),
            model_provider=str(row["model_provider"]),
            base_url=str(row["base_url"]),
            api_key=str(row["api_key"]),
            default_model=str(row["default_model"]),
            status=str(row["status"]),
            metadata=row["metadata"],  # type: ignore[assignment]
        )


class ProviderAdapter(Protocol):
    adapter_key: str
    runtime_provider: str

    def discover_capabilities(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
    ) -> ProviderCapabilitySnapshot: ...

    def invoke(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
        request: ModelInvocationRequest,
    ) -> ModelInvocationResponse: ...


class ProviderAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, adapter: ProviderAdapter) -> None:
        key = adapter.adapter_key.strip().lower()
        if key == "":
            raise ValueError("adapter key is required")
        if key in self._adapters:
            raise ValueError(f"adapter key {key} is already registered")
        self._adapters[key] = adapter

    def resolve(self, provider_key: str) -> ProviderAdapter:
        key = provider_key.strip().lower()
        adapter = self._adapters.get(key)
        if adapter is None:
            raise ProviderAdapterNotFoundError(f"provider adapter {provider_key} is not registered")
        return adapter

    def keys(self) -> list[str]:
        return sorted(self._adapters.keys())


def normalized_capability_snapshot(
    *,
    adapter_key: str,
    runtime_provider: str,
    supports_tool_calls: bool,
    supports_streaming: bool,
    supports_store: bool,
    supports_vision_input: bool,
    supports_audio_input: bool,
) -> ProviderCapabilitySnapshot:
    return {
        "capability_version": PROVIDER_CAPABILITY_VERSION_V1,
        "adapter_key": adapter_key,
        "runtime_provider": runtime_provider,
        "supports_text_input": True,
        "supports_text_output": True,
        "supports_tool_calls": supports_tool_calls,
        "supports_streaming": supports_streaming,
        "supports_store": supports_store,
        "supports_vision_input": supports_vision_input,
        "supports_audio_input": supports_audio_input,
    }


class OpenAICompatibleAdapter:
    adapter_key = OPENAI_COMPATIBLE_ADAPTER_KEY
    runtime_provider = OPENAI_RESPONSES_PROVIDER

    def discover_capabilities(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
    ) -> ProviderCapabilitySnapshot:
        del config, settings
        return normalized_capability_snapshot(
            adapter_key=self.adapter_key,
            runtime_provider=self.runtime_provider,
            supports_tool_calls=False,
            supports_streaming=False,
            supports_store=False,
            supports_vision_input=False,
            supports_audio_input=False,
        )

    def invoke(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
        request: ModelInvocationRequest,
    ) -> ModelInvocationResponse:
        if request.provider != self.runtime_provider:
            raise ModelInvocationError(f"unsupported model provider: {request.provider}")

        return invoke_openai_compatible_model(
            transport=OpenAICompatibleTransportConfig(
                base_url=config.base_url,
                api_key=config.api_key,
                timeout_seconds=settings.model_timeout_seconds,
            ),
            request=request,
        )


def make_provider_adapter_registry() -> ProviderAdapterRegistry:
    registry = ProviderAdapterRegistry()
    registry.register(OpenAICompatibleAdapter())
    return registry


def resolve_runtime_provider_config_secrets(
    *,
    config: RuntimeProviderConfig,
    settings: Settings,
) -> RuntimeProviderConfig:
    return replace(
        config,
        api_key=resolve_provider_api_key(settings=settings, api_key_field=config.api_key),
    )


def _deterministic_json(value: JsonObject | list[object]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def build_provider_test_model_request(
    *,
    runtime_provider: str,
    model: str,
    prompt_text: str,
) -> ModelInvocationRequest:
    if runtime_provider != OPENAI_RESPONSES_PROVIDER:
        raise ModelInvocationError(f"unsupported model provider: {runtime_provider}")

    prompt = PromptAssemblyResult(
        sections=(
            PromptSection(
                name="system",
                content=(
                    "You are validating provider connectivity for AliceBot. "
                    "Return a concise plain-text response."
                ),
            ),
            PromptSection(
                name="developer",
                content="Do not call tools. Reply in one sentence.",
            ),
            PromptSection(
                name="context",
                content=_deterministic_json({"kind": "provider_test", "version": "v1"}),
            ),
            PromptSection(
                name="conversation",
                content=_deterministic_json(
                    {
                        "events": [
                            {
                                "id": "provider-test-1",
                                "kind": "message.user",
                                "payload": {"text": prompt_text},
                            }
                        ]
                    }
                ),
            ),
        ),
        prompt_text="",
        prompt_sha256="",
        trace_payload={
            "version": "prompt_assembly_v0",
            "compile_trace_id": "provider_test",
            "compiler_version": "provider_test_v1",
            "prompt_sha256": "",
            "prompt_char_count": 0,
            "section_order": ["system", "developer", "context", "conversation"],
            "section_characters": {
                "system": 0,
                "developer": 0,
                "context": 0,
                "conversation": 0,
            },
            "included_session_count": 0,
            "included_event_count": 1,
            "included_memory_count": 0,
            "included_entity_count": 0,
            "included_entity_edge_count": 0,
        },
    )
    return ModelInvocationRequest(
        provider=OPENAI_RESPONSES_PROVIDER,
        model=model,
        prompt=prompt,
    )
