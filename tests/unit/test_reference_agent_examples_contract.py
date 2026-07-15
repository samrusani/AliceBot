from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import types
from typing import Any, Literal, NotRequired, Required, Union, get_args, get_origin, get_type_hints, is_typeddict

from alicebot_api.contracts import (
    CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0,
    ContinuityBriefResponse,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPO_ROOT / "fixtures" / "reference_integrations" / "continuity_brief_agent_handoff_v1.json"
)


def _unwrap_presence_marker(annotation: object) -> object:
    origin = get_origin(annotation)
    if origin in {Required, NotRequired}:
        return get_args(annotation)[0]
    return annotation


def _typed_dict_contract(annotation: object) -> tuple[dict[str, object], set[str]]:
    hints = get_type_hints(annotation, include_extras=True)
    required_keys: set[str] = set()
    total = bool(getattr(annotation, "__total__", True))
    for key, field_annotation in hints.items():
        origin = get_origin(field_annotation)
        if origin is Required or (origin is not NotRequired and total):
            required_keys.add(key)
    return hints, required_keys


def _contract_errors(value: object, annotation: object, path: str = "$") -> list[str]:
    annotation = _unwrap_presence_marker(annotation)
    if annotation is Any:
        return []

    if is_typeddict(annotation):
        if not isinstance(value, dict):
            return [f"{path}: expected object, got {type(value).__name__}"]
        hints, required_keys = _typed_dict_contract(annotation)
        actual_keys = set(value)
        errors = [
            f"{path}.{key}: missing required key"
            for key in sorted(required_keys - actual_keys)
        ]
        errors.extend(
            f"{path}.{key}: unexpected key"
            for key in sorted(actual_keys - set(hints))
        )
        for key in sorted(actual_keys & set(hints)):
            errors.extend(_contract_errors(value[key], hints[key], f"{path}.{key}"))
        return errors

    origin = get_origin(annotation)
    if origin in {Union, types.UnionType}:
        branch_errors = [
            _contract_errors(value, member, path) for member in get_args(annotation)
        ]
        if any(not errors for errors in branch_errors):
            return []
        summaries = "; ".join(errors[0] for errors in branch_errors if errors)
        return [f"{path}: no union member matched ({summaries})"]

    if origin is Literal:
        if value not in get_args(annotation):
            return [f"{path}: expected one of {get_args(annotation)!r}, got {value!r}"]
        return []

    if origin is list:
        if not isinstance(value, list):
            return [f"{path}: expected list, got {type(value).__name__}"]
        item_annotation = get_args(annotation)[0]
        return [
            error
            for index, item in enumerate(value)
            for error in _contract_errors(item, item_annotation, f"{path}[{index}]")
        ]

    if origin is dict:
        if not isinstance(value, dict):
            return [f"{path}: expected object, got {type(value).__name__}"]
        key_annotation, item_annotation = get_args(annotation)
        return [
            error
            for key, item in value.items()
            for error in (
                *_contract_errors(key, key_annotation, f"{path}.<key>"),
                *_contract_errors(item, item_annotation, f"{path}.{key}"),
            )
        ]

    if annotation is type(None):
        return [] if value is None else [f"{path}: expected null, got {value!r}"]
    if annotation is float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return []
        return [f"{path}: expected float, got {type(value).__name__}"]
    if annotation is int:
        return [] if type(value) is int else [f"{path}: expected int, got {type(value).__name__}"]
    if annotation is bool:
        return [] if type(value) is bool else [f"{path}: expected bool, got {type(value).__name__}"]
    if annotation is str:
        return [] if isinstance(value, str) else [f"{path}: expected str, got {type(value).__name__}"]
    if isinstance(annotation, type):
        if isinstance(value, annotation):
            return []
        return [f"{path}: expected {annotation.__name__}, got {type(value).__name__}"]
    return [f"{path}: unsupported contract annotation {annotation!r}"]


def _matching_annotation(value: object, annotation: object, path: str) -> object:
    annotation = _unwrap_presence_marker(annotation)
    if get_origin(annotation) in {Union, types.UnionType}:
        for member in get_args(annotation):
            if not _contract_errors(value, member, path):
                return member
    return annotation


def _populated_typed_dict_nodes(
    value: object,
    annotation: object,
    path: tuple[str | int, ...] = (),
) -> list[tuple[tuple[str | int, ...], object]]:
    annotation = _matching_annotation(value, annotation, "$")
    if is_typeddict(annotation):
        if not isinstance(value, dict):
            return []
        hints, _required_keys = _typed_dict_contract(annotation)
        nodes = [(path, annotation)]
        for key in sorted(set(value) & set(hints)):
            nodes.extend(
                _populated_typed_dict_nodes(value[key], hints[key], (*path, key))
            )
        return nodes

    origin = get_origin(annotation)
    if origin is list and isinstance(value, list):
        item_annotation = get_args(annotation)[0]
        return [
            node
            for index, item in enumerate(value)
            for node in _populated_typed_dict_nodes(
                item,
                item_annotation,
                (*path, index),
            )
        ]
    if origin is dict and isinstance(value, dict):
        item_annotation = get_args(annotation)[1]
        return [
            node
            for key, item in value.items()
            for node in _populated_typed_dict_nodes(
                item,
                item_annotation,
                (*path, str(key)),
            )
        ]
    return []


def _value_at_path(payload: object, path: tuple[str | int, ...]) -> object:
    current = payload
    for token in path:
        current = current[token]  # type: ignore[index]
    return current


def test_reference_agent_fixture_tracks_continuity_brief_contract() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    brief = payload["brief"]

    assert _contract_errors(payload, ContinuityBriefResponse) == []
    assert brief["selection_strategy"]["briefing_strategy"] == "balanced"
    serialized = json.dumps(payload, sort_keys=True)
    assert "model_pack_strategy" not in serialized
    assert "model_pack" not in serialized
    assert brief["assembly_version"] == CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0
    assert brief["brief_type"] == "agent_handoff"


def test_recursive_fixture_validator_rejects_missing_and_extra_keys_in_every_record() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    nodes = _populated_typed_dict_nodes(payload, ContinuityBriefResponse)
    assert nodes
    for path, annotation in nodes:
        hints, required_keys = _typed_dict_contract(annotation)
        original_record = _value_at_path(payload, path)
        assert isinstance(original_record, dict)
        assert required_keys <= set(original_record)

        for required_key in sorted(required_keys):
            missing_payload = deepcopy(payload)
            missing_record = _value_at_path(missing_payload, path)
            assert isinstance(missing_record, dict)
            del missing_record[required_key]
            assert _contract_errors(missing_payload, ContinuityBriefResponse)

        extra_payload = deepcopy(payload)
        extra_record = _value_at_path(extra_payload, path)
        assert isinstance(extra_record, dict)
        extra_record["__unexpected_contract_key__"] = True
        assert _contract_errors(extra_payload, ContinuityBriefResponse)
