from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from alicebot_api.model_packs import (
    MODEL_PACK_CONTRACT_VERSION_V1,
    ModelPackNotFoundError,
    ModelPackValidationError,
    apply_runtime_limit_caps,
    build_model_pack_runtime_shape,
    ensure_tier1_model_packs_for_workspace,
    is_reserved_tier1_pack_key,
    normalize_model_pack_contract,
    normalize_pack_id,
    normalize_pack_version,
    resolve_workspace_model_pack_selection,
)


_NOW = datetime.now(timezone.utc)


def _contract(*, system_append: str = "", developer_append: str = "") -> dict[str, object]:
    return {
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
            "system_instruction_append": system_append,
            "developer_instruction_append": developer_append,
        },
        "compatibility": {
            "provider_keys": ["openai_compatible", "ollama", "llamacpp"],
            "runtime_providers": ["openai_responses"],
            "notes": "unit test",
        },
    }


def _pack_row(*, pack_id: str, pack_version: str = "1.0.0") -> dict[str, object]:
    return {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "created_by_user_account_id": uuid4(),
        "pack_id": pack_id,
        "pack_version": pack_version,
        "display_name": f"{pack_id} pack",
        "family": "custom",
        "description": "desc",
        "status": "active",
        "contract": normalize_model_pack_contract(_contract()),
        "metadata": {},
        "created_at": _NOW,
        "updated_at": _NOW,
    }


class FakeModelPackStore:
    def __init__(self) -> None:
        self.packs_by_key: dict[tuple[str, str], dict[str, object]] = {}
        self.packs_by_row_id: dict[object, dict[str, object]] = {}
        self.binding: dict[str, object] | None = None

    def get_model_pack_for_workspace_optional(
        self,
        *,
        workspace_id,
        pack_id: str,
        pack_version: str | None = None,
    ):
        del workspace_id
        if pack_version is None:
            candidates = [
                row
                for (candidate_pack_id, _), row in self.packs_by_key.items()
                if candidate_pack_id == pack_id
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
            return candidates[0]
        return self.packs_by_key.get((pack_id, pack_version))

    def create_model_pack(
        self,
        *,
        workspace_id,
        created_by_user_account_id,
        pack_id: str,
        pack_version: str,
        display_name: str,
        family: str,
        description: str,
        status: str,
        contract,
        metadata,
    ):
        row = {
            "id": uuid4(),
            "workspace_id": workspace_id,
            "created_by_user_account_id": created_by_user_account_id,
            "pack_id": pack_id,
            "pack_version": pack_version,
            "display_name": display_name,
            "family": family,
            "description": description,
            "status": status,
            "contract": contract,
            "metadata": metadata,
            "created_at": _NOW,
            "updated_at": _NOW,
        }
        self.packs_by_key[(pack_id, pack_version)] = row
        self.packs_by_row_id[row["id"]] = row
        return row

    def create_model_pack_if_absent_optional(
        self,
        *,
        workspace_id,
        created_by_user_account_id,
        pack_id: str,
        pack_version: str,
        display_name: str,
        family: str,
        description: str,
        status: str,
        contract,
        metadata,
    ):
        key = (pack_id, pack_version)
        if key in self.packs_by_key:
            return None
        return self.create_model_pack(
            workspace_id=workspace_id,
            created_by_user_account_id=created_by_user_account_id,
            pack_id=pack_id,
            pack_version=pack_version,
            display_name=display_name,
            family=family,
            description=description,
            status=status,
            contract=contract,
            metadata=metadata,
        )

    def get_latest_workspace_model_pack_binding_optional(self, *, workspace_id):
        del workspace_id
        return self.binding

    def get_model_pack_for_workspace_by_row_id_optional(self, *, workspace_id, model_pack_id):
        del workspace_id
        return self.packs_by_row_id.get(model_pack_id)


class SimulatedSeedRaceModelPackStore(FakeModelPackStore):
    def __init__(self) -> None:
        super().__init__()
        self._simulated_race_for_keys: set[tuple[str, str]] = set()

    def create_model_pack_if_absent_optional(
        self,
        *,
        workspace_id,
        created_by_user_account_id,
        pack_id: str,
        pack_version: str,
        display_name: str,
        family: str,
        description: str,
        status: str,
        contract,
        metadata,
    ):
        key = (pack_id, pack_version)
        if key == ("llama", "1.0.0") and key not in self._simulated_race_for_keys:
            self._simulated_race_for_keys.add(key)
            super().create_model_pack(
                workspace_id=workspace_id,
                created_by_user_account_id=created_by_user_account_id,
                pack_id=pack_id,
                pack_version=pack_version,
                display_name=display_name,
                family=family,
                description=description,
                status=status,
                contract=contract,
                metadata=metadata,
            )
            return None
        return super().create_model_pack_if_absent_optional(
            workspace_id=workspace_id,
            created_by_user_account_id=created_by_user_account_id,
            pack_id=pack_id,
            pack_version=pack_version,
            display_name=display_name,
            family=family,
            description=description,
            status=status,
            contract=contract,
            metadata=metadata,
        )


def test_normalize_pack_id_and_version() -> None:
    assert normalize_pack_id(" GPT-OSS ") == "gpt-oss"
    assert normalize_pack_version("1.2.3") == "1.2.3"

    with pytest.raises(ModelPackValidationError, match="pack_id"):
        normalize_pack_id("Bad ID")
    with pytest.raises(ModelPackValidationError, match="semver"):
        normalize_pack_version("v1")


def test_normalize_model_pack_contract_rejects_invalid_provider_key() -> None:
    with pytest.raises(ModelPackValidationError, match="unsupported provider key"):
        normalize_model_pack_contract(
            {
                "contract_version": MODEL_PACK_CONTRACT_VERSION_V1,
                "context": {},
                "tools": {"mode": "none"},
                "response": {},
                "compatibility": {
                    "provider_keys": ["unknown"],
                    "runtime_providers": ["openai_responses"],
                },
            }
        )


def test_build_runtime_shape_and_apply_caps() -> None:
    shape = build_model_pack_runtime_shape(
        normalize_model_pack_contract(
            _contract(
                system_append="System overlay",
                developer_append="Developer overlay",
            )
        )
    )

    assert shape.system_instruction_append == "System overlay"
    assert shape.developer_instruction_append == "Developer overlay"

    assert apply_runtime_limit_caps(
        max_sessions=20,
        max_events=40,
        max_memories=60,
        max_entities=80,
        max_entity_edges=100,
        shape=shape,
    ) == (3, 8, 5, 5, 10)


def test_ensure_tier1_model_packs_for_workspace_seeds_once() -> None:
    store = FakeModelPackStore()
    workspace_id = uuid4()
    user_account_id = uuid4()

    first_seed = ensure_tier1_model_packs_for_workspace(
        store=store,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        created_by_user_account_id=user_account_id,
    )
    second_seed = ensure_tier1_model_packs_for_workspace(
        store=store,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        created_by_user_account_id=user_account_id,
    )

    assert len(first_seed) == 4
    assert len(second_seed) == 4
    assert len(store.packs_by_key) == 4
    assert {row["pack_id"] for row in first_seed} == {"llama", "qwen", "gemma", "gpt-oss"}


def test_ensure_tier1_model_packs_handles_seed_race_with_existing_row() -> None:
    store = SimulatedSeedRaceModelPackStore()
    seeded = ensure_tier1_model_packs_for_workspace(
        store=store,  # type: ignore[arg-type]
        workspace_id=uuid4(),
        created_by_user_account_id=uuid4(),
    )
    assert len(seeded) == 4
    assert {row["pack_id"] for row in seeded} == {"llama", "qwen", "gemma", "gpt-oss"}


def test_is_reserved_tier1_pack_key() -> None:
    assert is_reserved_tier1_pack_key(pack_id="llama", pack_version="1.0.0")
    assert not is_reserved_tier1_pack_key(pack_id="llama", pack_version="1.0.1")
    assert not is_reserved_tier1_pack_key(pack_id="custom-brief", pack_version="1.0.0")


def test_pack_selection_prefers_request_over_workspace_binding() -> None:
    store = FakeModelPackStore()
    workspace_id = uuid4()
    request_pack = _pack_row(pack_id="qwen")
    bound_pack = _pack_row(pack_id="llama")
    store.packs_by_key[("qwen", "1.0.0")] = request_pack
    store.packs_by_key[("llama", "1.0.0")] = bound_pack
    store.packs_by_row_id[request_pack["id"]] = request_pack
    store.packs_by_row_id[bound_pack["id"]] = bound_pack
    store.binding = {
        "model_pack_id": bound_pack["id"],
    }

    selected = resolve_workspace_model_pack_selection(
        store=store,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        requested_pack_id="qwen",
        requested_pack_version="1.0.0",
    )

    assert selected.source == "request"
    assert selected.pack is request_pack


def test_pack_selection_uses_workspace_binding_when_request_not_supplied() -> None:
    store = FakeModelPackStore()
    workspace_id = uuid4()
    bound_pack = _pack_row(pack_id="llama")
    store.packs_by_key[("llama", "1.0.0")] = bound_pack
    store.packs_by_row_id[bound_pack["id"]] = bound_pack
    store.binding = {
        "model_pack_id": bound_pack["id"],
    }

    selected = resolve_workspace_model_pack_selection(
        store=store,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        requested_pack_id=None,
        requested_pack_version=None,
    )

    assert selected.source == "workspace_binding"
    assert selected.pack is bound_pack


def test_pack_selection_raises_when_request_pack_is_missing() -> None:
    store = FakeModelPackStore()

    with pytest.raises(ModelPackNotFoundError, match="was not found"):
        resolve_workspace_model_pack_selection(
            store=store,  # type: ignore[arg-type]
            workspace_id=uuid4(),
            requested_pack_id="gemma",
            requested_pack_version="1.0.0",
        )
