from __future__ import annotations

from dataclasses import dataclass
import json

from alicebot_api.store import JsonObject


CONTINUITY_IMPORT_STATUSES = {
    "active",
    "stale",
    "completed",
    "cancelled",
    "superseded",
}


class OpenClawAdapterValidationError(ValueError):
    """Raised when an OpenClaw import payload is invalid."""


@dataclass(frozen=True, slots=True)
class OpenClawWorkspaceContext:
    fixture_id: str | None
    workspace_id: str
    workspace_name: str | None
    source_path: str


@dataclass(frozen=True, slots=True)
class OpenClawNormalizedItem:
    source_item_id: str
    source_file: str
    source_locator: JsonObject
    source_segment_text: str
    source_segment_kind: str
    object_type: str
    status: str
    raw_content: str
    title: str
    body: JsonObject
    confidence: float
    source_provenance: JsonObject
    dedupe_key: str


@dataclass(frozen=True, slots=True)
class OpenClawNormalizedBatch:
    context: OpenClawWorkspaceContext
    items: list[OpenClawNormalizedItem]


def normalize_optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        return None
    return normalized


def normalize_required_text(value: object, *, field_name: str) -> str:
    normalized = normalize_optional_text(value)
    if normalized is None:
        raise OpenClawAdapterValidationError(f"{field_name} must be a non-empty string")
    return normalized


def parse_optional_confidence(value: object) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise OpenClawAdapterValidationError("confidence must be a number")

    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            parsed = float(stripped)
        except ValueError as exc:
            raise OpenClawAdapterValidationError("confidence must be a number") from exc
    else:
        raise OpenClawAdapterValidationError("confidence must be a number")

    if parsed < 0.0 or parsed > 1.0:
        raise OpenClawAdapterValidationError("confidence must be between 0.0 and 1.0")
    return parsed


def parse_optional_status(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    if normalized is None:
        return None
    lowered = normalized.casefold()
    if lowered not in CONTINUITY_IMPORT_STATUSES:
        supported = ", ".join(sorted(CONTINUITY_IMPORT_STATUSES))
        raise OpenClawAdapterValidationError(
            f"status must be one of: {supported}"
        )
    return lowered


def ensure_json_object(value: object, *, field_name: str) -> JsonObject:
    if not isinstance(value, dict):
        raise OpenClawAdapterValidationError(f"{field_name} must be a JSON object")
    return value


def canonicalize_json(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): canonicalize_json(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [canonicalize_json(item) for item in value]
    return value


def canonical_json_string(value: object) -> str:
    return json.dumps(
        canonicalize_json(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def as_json_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        return {}
    output: JsonObject = {}
    for key, child in value.items():
        if not isinstance(key, str):
            continue
        output[key] = _as_json_value(child)
    return output


def _as_json_value(value: object):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_as_json_value(item) for item in value]
    if isinstance(value, dict):
        return as_json_object(value)
    return str(value)


def merge_json_objects(*payloads: JsonObject) -> JsonObject:
    merged: JsonObject = {}
    for payload in payloads:
        merged.update(payload)
    return merged


def pick_first_text(*candidates: object) -> str | None:
    for candidate in candidates:
        normalized = normalize_optional_text(candidate)
        if normalized is not None:
            return normalized
    return None


def to_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        normalized = normalize_optional_text(value)
        return [] if normalized is None else [normalized]

    if isinstance(value, list):
        items: list[str] = []
        seen: set[str] = set()
        for raw in value:
            normalized = normalize_optional_text(raw)
            if normalized is None or normalized in seen:
                continue
            items.append(normalized)
            seen.add(normalized)
        return items

    return []


__all__ = [
    "OpenClawAdapterValidationError",
    "OpenClawNormalizedBatch",
    "OpenClawNormalizedItem",
    "OpenClawWorkspaceContext",
    "as_json_object",
    "canonical_json_string",
    "ensure_json_object",
    "merge_json_objects",
    "normalize_optional_text",
    "normalize_required_text",
    "parse_optional_confidence",
    "parse_optional_status",
    "pick_first_text",
    "to_string_list",
]
