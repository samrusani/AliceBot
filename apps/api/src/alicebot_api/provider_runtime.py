from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import NotRequired, Protocol, TypedDict
from uuid import UUID

from alicebot_api.config import Settings
from alicebot_api.contracts import (
    ModelInvocationRequest,
    ModelInvocationResponse,
    PromptAssemblyResult,
    PromptSection,
)
from alicebot_api.local_provider_helpers import (
    build_auth_headers,
    parse_llamacpp_invoke_response,
    parse_llamacpp_models,
    parse_ollama_invoke_response,
    parse_ollama_models,
    prompt_sections_to_messages,
    request_json,
)
from alicebot_api.response_generation import (
    ModelInvocationError,
    OpenAICompatibleTransportConfig,
    invoke_openai_compatible_model,
)
from alicebot_api.provider_secrets import resolve_provider_api_key
from alicebot_api.store import JsonObject
from alicebot_api.vllm_provider_helpers import extract_vllm_invoke_passthrough_options

OPENAI_COMPATIBLE_ADAPTER_KEY = "openai_compatible"
OLLAMA_ADAPTER_KEY = "ollama"
LLAMACPP_ADAPTER_KEY = "llamacpp"
VLLM_ADAPTER_KEY = "vllm"
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
    supports_normalized_usage_telemetry: bool
    supports_normalized_latency_telemetry: bool
    health_status: NotRequired[str]
    health_endpoint: NotRequired[str]
    models_endpoint: NotRequired[str]
    invoke_endpoint: NotRequired[str]
    model_count: NotRequired[int]
    models: NotRequired[list[str]]
    telemetry_flow_scope: NotRequired[list[str]]


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
    auth_mode: str
    default_model: str
    status: str
    model_list_path: str
    healthcheck_path: str
    invoke_path: str
    adapter_options: JsonObject
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
            auth_mode=str(row.get("auth_mode", "bearer")),
            default_model=str(row["default_model"]),
            status=str(row["status"]),
            model_list_path=str(row.get("model_list_path", "")),
            healthcheck_path=str(row.get("healthcheck_path", "")),
            invoke_path=str(row.get("invoke_path", "")),
            adapter_options=row.get("adapter_options", {}),  # type: ignore[assignment]
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
    supports_normalized_usage_telemetry: bool = False,
    supports_normalized_latency_telemetry: bool = False,
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
        "supports_normalized_usage_telemetry": supports_normalized_usage_telemetry,
        "supports_normalized_latency_telemetry": supports_normalized_latency_telemetry,
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


class OllamaAdapter:
    adapter_key = OLLAMA_ADAPTER_KEY
    runtime_provider = OPENAI_RESPONSES_PROVIDER
    default_healthcheck_path = "/api/version"
    default_model_list_path = "/api/tags"
    default_invoke_path = "/api/chat"

    def discover_capabilities(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
    ) -> ProviderCapabilitySnapshot:
        headers = build_auth_headers(auth_mode=config.auth_mode, api_key=config.api_key)
        healthcheck_path = config.healthcheck_path or self.default_healthcheck_path
        model_list_path = config.model_list_path or self.default_model_list_path
        request_json(
            method="GET",
            base_url=config.base_url,
            path=healthcheck_path,
            timeout_seconds=settings.healthcheck_timeout_seconds,
            headers=headers,
        )
        model_payload = request_json(
            method="GET",
            base_url=config.base_url,
            path=model_list_path,
            timeout_seconds=settings.healthcheck_timeout_seconds,
            headers=headers,
        )
        models = parse_ollama_models(model_payload)
        snapshot = normalized_capability_snapshot(
            adapter_key=self.adapter_key,
            runtime_provider=self.runtime_provider,
            supports_tool_calls=False,
            supports_streaming=False,
            supports_store=False,
            supports_vision_input=False,
            supports_audio_input=False,
        )
        snapshot.update(
            {
                "health_status": "ok",
                "health_endpoint": healthcheck_path,
                "models_endpoint": model_list_path,
                "invoke_endpoint": config.invoke_path or self.default_invoke_path,
                "model_count": len(models),
                "models": models,
            }
        )
        return snapshot

    def invoke(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
        request: ModelInvocationRequest,
    ) -> ModelInvocationResponse:
        if request.provider != self.runtime_provider:
            raise ModelInvocationError(f"unsupported model provider: {request.provider}")
        headers = build_auth_headers(auth_mode=config.auth_mode, api_key=config.api_key)
        payload = request_json(
            method="POST",
            base_url=config.base_url,
            path=config.invoke_path or self.default_invoke_path,
            timeout_seconds=settings.model_timeout_seconds,
            headers=headers,
            payload={
                "model": request.model,
                "stream": False,
                "messages": prompt_sections_to_messages(request),
            },
        )
        return parse_ollama_invoke_response(request=request, payload=payload)


class LlamaCppAdapter:
    adapter_key = LLAMACPP_ADAPTER_KEY
    runtime_provider = OPENAI_RESPONSES_PROVIDER
    default_healthcheck_path = "/health"
    default_model_list_path = "/v1/models"
    default_invoke_path = "/v1/chat/completions"

    def discover_capabilities(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
    ) -> ProviderCapabilitySnapshot:
        headers = build_auth_headers(auth_mode=config.auth_mode, api_key=config.api_key)
        healthcheck_path = config.healthcheck_path or self.default_healthcheck_path
        model_list_path = config.model_list_path or self.default_model_list_path
        request_json(
            method="GET",
            base_url=config.base_url,
            path=healthcheck_path,
            timeout_seconds=settings.healthcheck_timeout_seconds,
            headers=headers,
        )
        model_payload = request_json(
            method="GET",
            base_url=config.base_url,
            path=model_list_path,
            timeout_seconds=settings.healthcheck_timeout_seconds,
            headers=headers,
        )
        models = parse_llamacpp_models(model_payload)
        snapshot = normalized_capability_snapshot(
            adapter_key=self.adapter_key,
            runtime_provider=self.runtime_provider,
            supports_tool_calls=False,
            supports_streaming=False,
            supports_store=False,
            supports_vision_input=False,
            supports_audio_input=False,
        )
        snapshot.update(
            {
                "health_status": "ok",
                "health_endpoint": healthcheck_path,
                "models_endpoint": model_list_path,
                "invoke_endpoint": config.invoke_path or self.default_invoke_path,
                "model_count": len(models),
                "models": models,
            }
        )
        return snapshot

    def invoke(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
        request: ModelInvocationRequest,
    ) -> ModelInvocationResponse:
        if request.provider != self.runtime_provider:
            raise ModelInvocationError(f"unsupported model provider: {request.provider}")
        headers = build_auth_headers(auth_mode=config.auth_mode, api_key=config.api_key)
        payload = request_json(
            method="POST",
            base_url=config.base_url,
            path=config.invoke_path or self.default_invoke_path,
            timeout_seconds=settings.model_timeout_seconds,
            headers=headers,
            payload={
                "model": request.model,
                "stream": False,
                "messages": prompt_sections_to_messages(request),
            },
        )
        return parse_llamacpp_invoke_response(request=request, payload=payload)


class VllmAdapter:
    adapter_key = VLLM_ADAPTER_KEY
    runtime_provider = OPENAI_RESPONSES_PROVIDER
    default_healthcheck_path = "/health"
    default_model_list_path = "/v1/models"
    default_invoke_path = "/v1/chat/completions"

    def discover_capabilities(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
    ) -> ProviderCapabilitySnapshot:
        headers = build_auth_headers(auth_mode=config.auth_mode, api_key=config.api_key)
        healthcheck_path = config.healthcheck_path or self.default_healthcheck_path
        model_list_path = config.model_list_path or self.default_model_list_path
        request_json(
            method="GET",
            base_url=config.base_url,
            path=healthcheck_path,
            timeout_seconds=settings.healthcheck_timeout_seconds,
            headers=headers,
        )
        model_payload = request_json(
            method="GET",
            base_url=config.base_url,
            path=model_list_path,
            timeout_seconds=settings.healthcheck_timeout_seconds,
            headers=headers,
        )
        models = parse_llamacpp_models(model_payload)
        snapshot = normalized_capability_snapshot(
            adapter_key=self.adapter_key,
            runtime_provider=self.runtime_provider,
            supports_tool_calls=False,
            supports_streaming=False,
            supports_store=False,
            supports_vision_input=False,
            supports_audio_input=False,
            supports_normalized_usage_telemetry=True,
            supports_normalized_latency_telemetry=True,
        )
        snapshot.update(
            {
                "health_status": "ok",
                "health_endpoint": healthcheck_path,
                "models_endpoint": model_list_path,
                "invoke_endpoint": config.invoke_path or self.default_invoke_path,
                "model_count": len(models),
                "models": models,
                "telemetry_flow_scope": ["provider_test", "runtime_invoke"],
            }
        )
        return snapshot

    def invoke(
        self,
        *,
        config: RuntimeProviderConfig,
        settings: Settings,
        request: ModelInvocationRequest,
    ) -> ModelInvocationResponse:
        if request.provider != self.runtime_provider:
            raise ModelInvocationError(f"unsupported model provider: {request.provider}")

        headers = build_auth_headers(auth_mode=config.auth_mode, api_key=config.api_key)
        payload: dict[str, object] = {
            "model": request.model,
            "stream": False,
            "messages": prompt_sections_to_messages(request),
        }
        payload.update(
            extract_vllm_invoke_passthrough_options(
                adapter_options=config.adapter_options,
            )
        )
        response_payload = request_json(
            method="POST",
            base_url=config.base_url,
            path=config.invoke_path or self.default_invoke_path,
            timeout_seconds=settings.model_timeout_seconds,
            headers=headers,
            payload=payload,
        )
        return parse_llamacpp_invoke_response(
            request=request,
            payload=response_payload,
        )


def make_provider_adapter_registry() -> ProviderAdapterRegistry:
    registry = ProviderAdapterRegistry()
    registry.register(OpenAICompatibleAdapter())
    registry.register(OllamaAdapter())
    registry.register(LlamaCppAdapter())
    registry.register(VllmAdapter())
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
