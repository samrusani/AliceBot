from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Literal
from uuid import UUID

from alicebot_api.store import ContinuityStore, JsonObject, ModelPackRow

MODEL_PACK_CONTRACT_VERSION_V1 = "model_pack_contract_v1"
MODEL_PACK_STATUS_ACTIVE = "active"
MODEL_PACK_BINDING_SOURCE_MANUAL = "manual"
MODEL_PACK_BINDING_SOURCE_RUNTIME_OVERRIDE = "runtime_override"
MODEL_PACK_FAMILIES: tuple[str, ...] = (
    "llama",
    "qwen",
    "gemma",
    "gpt-oss",
    "deepseek",
    "kimi",
    "mistral",
    "custom",
)
MODEL_PACK_BRIEFING_STRATEGIES: tuple[str, ...] = ("balanced", "compact", "detailed")
MAX_CONTEXT_SESSIONS = 50
MAX_CONTEXT_EVENTS = 200
MAX_CONTEXT_MEMORIES = 200
MAX_CONTEXT_ENTITIES = 200
MAX_CONTEXT_ENTITY_EDGES = 400

_ALLOWED_PROVIDER_KEYS: tuple[str, ...] = ("openai_compatible", "ollama", "llamacpp", "vllm")
_ALLOWED_RUNTIME_PROVIDERS: tuple[str, ...] = ("openai_responses",)
_PACK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
_PACK_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class ModelPackValidationError(ValueError):
    """Raised when a model-pack request payload is invalid."""


class ModelPackNotFoundError(LookupError):
    """Raised when a model pack cannot be found in the workspace scope."""


class ModelPackCompatibilityError(ValueError):
    """Raised when a model pack is incompatible with the selected provider/runtime."""


PackSelectionSource = Literal["none", "request", "workspace_binding"]


@dataclass(frozen=True, slots=True)
class Tier1PackSpec:
    pack_id: str
    pack_version: str
    display_name: str
    family: str
    description: str
    briefing_strategy: str
    briefing_max_tokens: int | None
    contract: JsonObject
    seed: str
    seed_version: str


@dataclass(frozen=True, slots=True)
class ModelPackRuntimeShape:
    max_sessions_cap: int | None
    max_events_cap: int | None
    max_memories_cap: int | None
    max_entities_cap: int | None
    max_entity_edges_cap: int | None
    tools_mode: str
    system_instruction_append: str
    developer_instruction_append: str


@dataclass(frozen=True, slots=True)
class ResolvedModelPackSelection:
    source: PackSelectionSource
    pack: ModelPackRow | None


def apply_runtime_limit_caps(
    *,
    max_sessions: int,
    max_events: int,
    max_memories: int,
    max_entities: int,
    max_entity_edges: int,
    shape: ModelPackRuntimeShape,
) -> tuple[int, int, int, int, int]:
    return (
        max_sessions if shape.max_sessions_cap is None else min(max_sessions, shape.max_sessions_cap),
        max_events if shape.max_events_cap is None else min(max_events, shape.max_events_cap),
        max_memories if shape.max_memories_cap is None else min(max_memories, shape.max_memories_cap),
        max_entities if shape.max_entities_cap is None else min(max_entities, shape.max_entities_cap),
        max_entity_edges
        if shape.max_entity_edges_cap is None
        else min(max_entity_edges, shape.max_entity_edges_cap),
    )


def append_instruction(base_instruction: str, append_instruction_text: str) -> str:
    suffix = append_instruction_text.strip()
    if suffix == "":
        return base_instruction
    return f"{base_instruction}\n{suffix}"


def normalize_pack_id(pack_id: str) -> str:
    normalized = pack_id.strip().lower()
    if normalized == "":
        raise ModelPackValidationError("pack_id is required")
    if _PACK_ID_PATTERN.fullmatch(normalized) is None:
        raise ModelPackValidationError(
            "pack_id must contain only lowercase letters, digits, '.', '_', or '-'"
        )
    return normalized


def normalize_pack_version(pack_version: str) -> str:
    normalized = pack_version.strip()
    if normalized == "":
        raise ModelPackValidationError("pack_version is required")
    if _PACK_VERSION_PATTERN.fullmatch(normalized) is None:
        raise ModelPackValidationError("pack_version must use semver format: MAJOR.MINOR.PATCH")
    return normalized


def normalize_pack_family(family: str) -> str:
    normalized = family.strip().lower()
    if normalized not in MODEL_PACK_FAMILIES:
        raise ModelPackValidationError(f"unsupported model-pack family: {family}")
    return normalized


def normalize_briefing_strategy(strategy: str | None) -> str:
    if strategy is None:
        return "balanced"
    normalized = strategy.strip().lower()
    if normalized not in MODEL_PACK_BRIEFING_STRATEGIES:
        raise ModelPackValidationError(
            "briefing_strategy must be one of: "
            + ", ".join(MODEL_PACK_BRIEFING_STRATEGIES)
        )
    return normalized


def normalize_briefing_max_tokens(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ModelPackValidationError("briefing_max_tokens must be an integer")
    if value < 32 or value > 4000:
        raise ModelPackValidationError("briefing_max_tokens must be between 32 and 4000")
    return value


def _normalize_optional_instruction(*, field_name: str, value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ModelPackValidationError(f"{field_name} must be a string")
    normalized = value.strip()
    if len(normalized) > 2000:
        raise ModelPackValidationError(f"{field_name} must be at most 2000 characters")
    return normalized


def _normalize_cap(
    *,
    context: Mapping[str, object],
    key: str,
    maximum: int,
) -> int | None:
    value = context.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ModelPackValidationError(f"context.{key} must be an integer")
    if value < 1 or value > maximum:
        raise ModelPackValidationError(f"context.{key} must be between 1 and {maximum}")
    return value


def normalize_model_pack_contract(contract: Mapping[str, object]) -> JsonObject:
    if not isinstance(contract, Mapping):
        raise ModelPackValidationError("contract must be an object")

    contract_version = contract.get("contract_version")
    if contract_version != MODEL_PACK_CONTRACT_VERSION_V1:
        raise ModelPackValidationError(
            f"contract.contract_version must equal {MODEL_PACK_CONTRACT_VERSION_V1}"
        )

    context_raw = contract.get("context", {})
    if not isinstance(context_raw, Mapping):
        raise ModelPackValidationError("contract.context must be an object")

    tools_raw = contract.get("tools", {})
    if not isinstance(tools_raw, Mapping):
        raise ModelPackValidationError("contract.tools must be an object")
    tools_mode = tools_raw.get("mode", "none")
    if tools_mode != "none":
        raise ModelPackValidationError("contract.tools.mode must be 'none' in P11-S4")

    response_raw = contract.get("response", {})
    if not isinstance(response_raw, Mapping):
        raise ModelPackValidationError("contract.response must be an object")

    compatibility_raw = contract.get("compatibility", {})
    if not isinstance(compatibility_raw, Mapping):
        raise ModelPackValidationError("contract.compatibility must be an object")

    provider_keys_raw = compatibility_raw.get("provider_keys", [])
    if not isinstance(provider_keys_raw, list):
        raise ModelPackValidationError("contract.compatibility.provider_keys must be a list")
    provider_keys: list[str] = []
    for key in provider_keys_raw:
        if not isinstance(key, str) or key.strip() == "":
            raise ModelPackValidationError("contract.compatibility.provider_keys must contain strings")
        normalized_key = key.strip()
        if normalized_key not in _ALLOWED_PROVIDER_KEYS:
            raise ModelPackValidationError(f"unsupported provider key in compatibility: {normalized_key}")
        if normalized_key not in provider_keys:
            provider_keys.append(normalized_key)

    runtime_providers_raw = compatibility_raw.get("runtime_providers", [])
    if not isinstance(runtime_providers_raw, list):
        raise ModelPackValidationError("contract.compatibility.runtime_providers must be a list")
    runtime_providers: list[str] = []
    for runtime_provider in runtime_providers_raw:
        if not isinstance(runtime_provider, str) or runtime_provider.strip() == "":
            raise ModelPackValidationError(
                "contract.compatibility.runtime_providers must contain strings"
            )
        normalized_runtime_provider = runtime_provider.strip()
        if normalized_runtime_provider not in _ALLOWED_RUNTIME_PROVIDERS:
            raise ModelPackValidationError(
                f"unsupported runtime provider in compatibility: {normalized_runtime_provider}"
            )
        if normalized_runtime_provider not in runtime_providers:
            runtime_providers.append(normalized_runtime_provider)

    compatibility_notes_raw = compatibility_raw.get("notes")
    compatibility_notes = None
    if compatibility_notes_raw is not None:
        if not isinstance(compatibility_notes_raw, str):
            raise ModelPackValidationError("contract.compatibility.notes must be a string")
        compatibility_notes = compatibility_notes_raw.strip()
        if len(compatibility_notes) > 500:
            raise ModelPackValidationError("contract.compatibility.notes must be at most 500 characters")

    max_sessions_cap = _normalize_cap(
        context=context_raw,
        key="max_sessions_cap",
        maximum=MAX_CONTEXT_SESSIONS,
    )
    max_events_cap = _normalize_cap(
        context=context_raw,
        key="max_events_cap",
        maximum=MAX_CONTEXT_EVENTS,
    )
    max_memories_cap = _normalize_cap(
        context=context_raw,
        key="max_memories_cap",
        maximum=MAX_CONTEXT_MEMORIES,
    )
    max_entities_cap = _normalize_cap(
        context=context_raw,
        key="max_entities_cap",
        maximum=MAX_CONTEXT_ENTITIES,
    )
    max_entity_edges_cap = _normalize_cap(
        context=context_raw,
        key="max_entity_edges_cap",
        maximum=MAX_CONTEXT_ENTITY_EDGES,
    )

    system_instruction_append = _normalize_optional_instruction(
        field_name="contract.response.system_instruction_append",
        value=response_raw.get("system_instruction_append"),
    )
    developer_instruction_append = _normalize_optional_instruction(
        field_name="contract.response.developer_instruction_append",
        value=response_raw.get("developer_instruction_append"),
    )

    normalized_contract: JsonObject = {
        "contract_version": MODEL_PACK_CONTRACT_VERSION_V1,
        "context": {
            "max_sessions_cap": max_sessions_cap,
            "max_events_cap": max_events_cap,
            "max_memories_cap": max_memories_cap,
            "max_entities_cap": max_entities_cap,
            "max_entity_edges_cap": max_entity_edges_cap,
        },
        "tools": {
            "mode": "none",
        },
        "response": {
            "system_instruction_append": system_instruction_append,
            "developer_instruction_append": developer_instruction_append,
        },
        "compatibility": {
            "provider_keys": provider_keys,
            "runtime_providers": runtime_providers,
            "notes": compatibility_notes,
        },
    }
    return normalized_contract


def build_model_pack_runtime_shape(contract: Mapping[str, object]) -> ModelPackRuntimeShape:
    normalized_contract = normalize_model_pack_contract(contract)
    context = normalized_contract["context"]
    response = normalized_contract["response"]
    tools = normalized_contract["tools"]

    assert isinstance(context, dict)
    assert isinstance(response, dict)
    assert isinstance(tools, dict)

    return ModelPackRuntimeShape(
        max_sessions_cap=context.get("max_sessions_cap"),  # type: ignore[arg-type]
        max_events_cap=context.get("max_events_cap"),  # type: ignore[arg-type]
        max_memories_cap=context.get("max_memories_cap"),  # type: ignore[arg-type]
        max_entities_cap=context.get("max_entities_cap"),  # type: ignore[arg-type]
        max_entity_edges_cap=context.get("max_entity_edges_cap"),  # type: ignore[arg-type]
        tools_mode=str(tools.get("mode", "none")),
        system_instruction_append=str(response.get("system_instruction_append", "")),
        developer_instruction_append=str(response.get("developer_instruction_append", "")),
    )


def _tier1_pack_specs() -> tuple[Tier1PackSpec, ...]:
    return (
        Tier1PackSpec(
            pack_id="llama",
            pack_version="1.0.0",
            display_name="Llama Tier 1",
            family="llama",
            description="Tier-1 declarative runtime shaping for Llama-family instruct models.",
            briefing_strategy="compact",
            briefing_max_tokens=160,
            contract=normalize_model_pack_contract(
                {
                    "contract_version": MODEL_PACK_CONTRACT_VERSION_V1,
                    "context": {
                        "max_sessions_cap": 3,
                        "max_events_cap": 8,
                        "max_memories_cap": 5,
                        "max_entities_cap": 5,
                        "max_entity_edges_cap": 10,
                    },
                    "tools": {"mode": "none"},
                    "response": {
                        "system_instruction_append": (
                            "Prefer factual, concise output and surface uncertainty explicitly when context is incomplete."
                        ),
                        "developer_instruction_append": (
                            "Favor grounded continuity facts over stylistic elaboration."
                        ),
                    },
                    "compatibility": {
                        "provider_keys": ["openai_compatible", "ollama", "llamacpp", "vllm"],
                        "runtime_providers": ["openai_responses"],
                        "notes": "Tier-1 baseline for Llama-family backends.",
                    },
                }
            ),
            seed="tier1",
            seed_version="p11-s4",
        ),
        Tier1PackSpec(
            pack_id="qwen",
            pack_version="1.0.0",
            display_name="Qwen Tier 1",
            family="qwen",
            description="Tier-1 declarative runtime shaping for Qwen-family instruct models.",
            briefing_strategy="compact",
            briefing_max_tokens=144,
            contract=normalize_model_pack_contract(
                {
                    "contract_version": MODEL_PACK_CONTRACT_VERSION_V1,
                    "context": {
                        "max_sessions_cap": 3,
                        "max_events_cap": 8,
                        "max_memories_cap": 4,
                        "max_entities_cap": 5,
                        "max_entity_edges_cap": 8,
                    },
                    "tools": {"mode": "none"},
                    "response": {
                        "system_instruction_append": (
                            "Respond with deterministic structure and avoid unsupported speculation."
                        ),
                        "developer_instruction_append": (
                            "Keep outputs directly actionable and compact."
                        ),
                    },
                    "compatibility": {
                        "provider_keys": ["openai_compatible", "ollama", "llamacpp", "vllm"],
                        "runtime_providers": ["openai_responses"],
                        "notes": "Tier-1 baseline for Qwen-family backends.",
                    },
                }
            ),
            seed="tier1",
            seed_version="p11-s4",
        ),
        Tier1PackSpec(
            pack_id="gemma",
            pack_version="1.0.0",
            display_name="Gemma Tier 1",
            family="gemma",
            description="Tier-1 declarative runtime shaping for Gemma-family instruct models.",
            briefing_strategy="compact",
            briefing_max_tokens=128,
            contract=normalize_model_pack_contract(
                {
                    "contract_version": MODEL_PACK_CONTRACT_VERSION_V1,
                    "context": {
                        "max_sessions_cap": 2,
                        "max_events_cap": 8,
                        "max_memories_cap": 4,
                        "max_entities_cap": 4,
                        "max_entity_edges_cap": 8,
                    },
                    "tools": {"mode": "none"},
                    "response": {
                        "system_instruction_append": (
                            "Maintain directness and prioritize clear, bounded recommendations."
                        ),
                        "developer_instruction_append": (
                            "Prefer concise summaries with explicit next actions."
                        ),
                    },
                    "compatibility": {
                        "provider_keys": ["openai_compatible", "ollama", "llamacpp", "vllm"],
                        "runtime_providers": ["openai_responses"],
                        "notes": "Tier-1 baseline for Gemma-family backends.",
                    },
                }
            ),
            seed="tier1",
            seed_version="p11-s4",
        ),
        Tier1PackSpec(
            pack_id="gpt-oss",
            pack_version="1.0.0",
            display_name="gpt-oss Tier 1",
            family="gpt-oss",
            description="Tier-1 declarative runtime shaping for gpt-oss-family instruct models.",
            briefing_strategy="balanced",
            briefing_max_tokens=192,
            contract=normalize_model_pack_contract(
                {
                    "contract_version": MODEL_PACK_CONTRACT_VERSION_V1,
                    "context": {
                        "max_sessions_cap": 3,
                        "max_events_cap": 8,
                        "max_memories_cap": 6,
                        "max_entities_cap": 6,
                        "max_entity_edges_cap": 12,
                    },
                    "tools": {"mode": "none"},
                    "response": {
                        "system_instruction_append": (
                            "Use precise language, preserve continuity facts, and avoid narrative filler."
                        ),
                        "developer_instruction_append": (
                            "When uncertain, state the uncertainty and propose the smallest safe next step."
                        ),
                    },
                    "compatibility": {
                        "provider_keys": ["openai_compatible", "ollama", "llamacpp", "vllm"],
                        "runtime_providers": ["openai_responses"],
                        "notes": "Tier-1 baseline for gpt-oss-family backends.",
                    },
                }
            ),
            seed="tier1",
            seed_version="p11-s4",
        ),
    )


def _catalog_pack_specs() -> tuple[Tier1PackSpec, ...]:
    return _tier1_pack_specs()


def _compatibility_lists(contract: Mapping[str, object]) -> tuple[list[str], list[str]]:
    normalized_contract = normalize_model_pack_contract(contract)
    compatibility = normalized_contract["compatibility"]
    assert isinstance(compatibility, dict)
    provider_keys = compatibility.get("provider_keys", [])
    runtime_providers = compatibility.get("runtime_providers", [])
    assert isinstance(provider_keys, list)
    assert isinstance(runtime_providers, list)
    return ([str(item) for item in provider_keys], [str(item) for item in runtime_providers])


def assert_model_pack_runtime_compatibility(
    *,
    pack: ModelPackRow,
    provider_key: str,
    runtime_provider: str,
) -> None:
    compatible_provider_keys, compatible_runtime_providers = _compatibility_lists(pack["contract"])
    if provider_key not in compatible_provider_keys:
        raise ModelPackCompatibilityError(
            f"model pack {pack['pack_id']} is not compatible with provider key {provider_key}"
        )
    if runtime_provider not in compatible_runtime_providers:
        raise ModelPackCompatibilityError(
            f"model pack {pack['pack_id']} is not compatible with runtime provider {runtime_provider}"
        )


def is_reserved_tier1_pack_key(*, pack_id: str, pack_version: str) -> bool:
    normalized_pack_id = normalize_pack_id(pack_id)
    normalized_pack_version = normalize_pack_version(pack_version)
    return any(
        spec.pack_id == normalized_pack_id and spec.pack_version == normalized_pack_version
        for spec in _catalog_pack_specs()
    )


def ensure_tier1_model_packs_for_workspace(
    *,
    store: ContinuityStore,
    workspace_id: UUID,
    created_by_user_account_id: UUID,
) -> list[ModelPackRow]:
    packs: list[ModelPackRow] = []
    for spec in _catalog_pack_specs():
        created = store.create_model_pack_if_absent_optional(
            workspace_id=workspace_id,
            created_by_user_account_id=created_by_user_account_id,
            pack_id=spec.pack_id,
            pack_version=spec.pack_version,
            display_name=spec.display_name,
            family=spec.family,
            description=spec.description,
            status=MODEL_PACK_STATUS_ACTIVE,
            briefing_strategy=spec.briefing_strategy,
            briefing_max_tokens=spec.briefing_max_tokens,
            contract=spec.contract,
            metadata={"seed": spec.seed, "seed_version": spec.seed_version},
        )
        if created is not None:
            packs.append(created)
            continue

        existing = store.get_model_pack_for_workspace_optional(
            workspace_id=workspace_id,
            pack_id=spec.pack_id,
            pack_version=spec.pack_version,
        )
        if existing is None:
            raise RuntimeError(
                f"catalog model pack {spec.pack_id}@{spec.pack_version} was expected but missing"
            )
        packs.append(existing)
    return packs


def resolve_workspace_model_pack_selection(
    *,
    store: ContinuityStore,
    workspace_id: UUID,
    requested_pack_id: str | None,
    requested_pack_version: str | None,
    provider_id: UUID | None = None,
) -> ResolvedModelPackSelection:
    if requested_pack_id is not None:
        normalized_pack_id = normalize_pack_id(requested_pack_id)
        normalized_pack_version = (
            None
            if requested_pack_version is None
            else normalize_pack_version(requested_pack_version)
        )
        selected_pack = store.get_model_pack_for_workspace_optional(
            workspace_id=workspace_id,
            pack_id=normalized_pack_id,
            pack_version=normalized_pack_version,
        )
        if selected_pack is None:
            if normalized_pack_version is None:
                raise ModelPackNotFoundError(
                    f"model pack {normalized_pack_id} was not found"
                )
            raise ModelPackNotFoundError(
                f"model pack {normalized_pack_id}@{normalized_pack_version} was not found"
            )
        return ResolvedModelPackSelection(source="request", pack=selected_pack)

    binding = None
    if provider_id is not None:
        binding = store.get_resolved_workspace_model_pack_binding_optional(
            workspace_id=workspace_id,
            provider_id=provider_id,
        )
    else:
        binding = store.get_latest_workspace_model_pack_binding_optional(workspace_id=workspace_id)
    if binding is None:
        return ResolvedModelPackSelection(source="none", pack=None)

    selected_pack = store.get_model_pack_for_workspace_by_row_id_optional(
        workspace_id=workspace_id,
        model_pack_id=binding["model_pack_id"],
    )
    if selected_pack is None:
        return ResolvedModelPackSelection(source="none", pack=None)

    return ResolvedModelPackSelection(source="workspace_binding", pack=selected_pack)
