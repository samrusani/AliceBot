from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from alicebot_api.store import JsonObject


CONTINUITY_IMPORT_STATUSES = {
    "active",
    "stale",
    "completed",
    "cancelled",
    "superseded",
}

CONTINUITY_IMPORT_OBJECT_TYPES = {
    "Decision",
    "NextAction",
    "Commitment",
    "WaitingFor",
    "Blocker",
    "MemoryFact",
    "Note",
}

OBJECT_TYPE_TO_EXPLICIT_SIGNAL: dict[str, str] = {
    "Decision": "decision",
    "NextAction": "next_action",
    "Commitment": "commitment",
    "WaitingFor": "waiting_for",
    "Blocker": "blocker",
    "MemoryFact": "remember_this",
    "Note": "note",
}

OBJECT_TYPE_TO_BODY_KEY: dict[str, str] = {
    "Note": "body",
    "MemoryFact": "fact_text",
    "Decision": "decision_text",
    "Commitment": "commitment_text",
    "WaitingFor": "waiting_for_text",
    "Blocker": "blocking_reason",
    "NextAction": "action_text",
}

OBJECT_TYPE_TO_PREFIX: dict[str, str] = {
    "Decision": "Decision",
    "Commitment": "Commitment",
    "WaitingFor": "Waiting For",
    "Blocker": "Blocker",
    "NextAction": "Next Action",
    "MemoryFact": "Memory Fact",
    "Note": "Note",
}

_TYPE_ALIAS_TO_OBJECT_TYPE: dict[str, str] = {
    "decision": "Decision",
    "decisions": "Decision",
    "task": "NextAction",
    "next": "NextAction",
    "next_action": "NextAction",
    "nextaction": "NextAction",
    "action": "NextAction",
    "commitment": "Commitment",
    "waiting": "WaitingFor",
    "waiting_for": "WaitingFor",
    "waitingfor": "WaitingFor",
    "blocker": "Blocker",
    "fact": "MemoryFact",
    "memory_fact": "MemoryFact",
    "memory": "MemoryFact",
    "note": "Note",
}


class ImporterValidationError(ValueError):
    """Raised when an importer source payload is invalid."""


@dataclass(frozen=True, slots=True)
class ImporterWorkspaceContext:
    fixture_id: str | None
    workspace_id: str
    workspace_name: str | None
    source_path: str


@dataclass(frozen=True, slots=True)
class ImporterNormalizedItem:
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
class ImporterNormalizedBatch:
    context: ImporterWorkspaceContext
    items: list[ImporterNormalizedItem]


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
        raise ImporterValidationError(f"{field_name} must be a non-empty string")
    return normalized


def normalize_object_type(value: object, *, default: str = "Note") -> str:
    normalized = normalize_optional_text(value)
    if normalized is None:
        return default

    if normalized in CONTINUITY_IMPORT_OBJECT_TYPES:
        return normalized

    lowered = normalized.casefold().replace("-", "_").replace(" ", "_")
    return _TYPE_ALIAS_TO_OBJECT_TYPE.get(lowered, default)


def parse_optional_confidence(value: object) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise ImporterValidationError("confidence must be a number")

    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            parsed = float(stripped)
        except ValueError as exc:
            raise ImporterValidationError("confidence must be a number") from exc
    else:
        raise ImporterValidationError("confidence must be a number")

    if parsed < 0.0 or parsed > 1.0:
        raise ImporterValidationError("confidence must be between 0.0 and 1.0")
    return parsed


def parse_optional_status(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    if normalized is None:
        return None
    lowered = normalized.casefold()
    if lowered not in CONTINUITY_IMPORT_STATUSES:
        supported = ", ".join(sorted(CONTINUITY_IMPORT_STATUSES))
        raise ImporterValidationError(
            f"status must be one of: {supported}"
        )
    return lowered


def ensure_json_object(value: object, *, field_name: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ImporterValidationError(f"{field_name} must be a JSON object")
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


def dedupe_key_for_payload(value: object) -> str:
    return sha256(canonical_json_string(value).encode("utf-8")).hexdigest()


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
    "CONTINUITY_IMPORT_OBJECT_TYPES",
    "CONTINUITY_IMPORT_STATUSES",
    "ImporterNormalizedBatch",
    "ImporterNormalizedItem",
    "ImporterValidationError",
    "ImporterWorkspaceContext",
    "OBJECT_TYPE_TO_BODY_KEY",
    "OBJECT_TYPE_TO_EXPLICIT_SIGNAL",
    "OBJECT_TYPE_TO_PREFIX",
    "as_json_object",
    "canonical_json_string",
    "dedupe_key_for_payload",
    "ensure_json_object",
    "merge_json_objects",
    "normalize_object_type",
    "normalize_optional_text",
    "normalize_required_text",
    "parse_optional_confidence",
    "parse_optional_status",
    "pick_first_text",
    "to_string_list",
]
