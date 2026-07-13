"""Canonical multi-project scope helpers for vNext resources."""

from __future__ import annotations

from typing import Mapping, Sequence

from alicebot_api.vnext_repositories import JsonObject


def normalize_project_scope(value: object) -> tuple[str, ...]:
    values: list[str] = []

    def add(item: object) -> None:
        if isinstance(item, (str, int)):
            normalized = " ".join(str(item).split()).strip()
            if normalized:
                values.append(normalized)
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            for nested in item:
                add(nested)

    add(value)
    return tuple(dict.fromkeys(values))


def memory_project_scope(memory: Mapping[str, object]) -> tuple[str, ...]:
    """Canonical array scope with non-widening singular legacy fallbacks."""
    if "project_scope" in memory:
        return normalize_project_scope(memory.get("project_scope"))
    metadata = memory.get("metadata_json")
    if isinstance(metadata, Mapping):
        if "project_scope" in metadata:
            return normalize_project_scope(metadata.get("project_scope"))
        agentic = metadata.get("agentic_memory")
        if isinstance(agentic, Mapping):
            legacy_agentic_scope = normalize_project_scope(agentic.get("project_scope"))
            if legacy_agentic_scope:
                return legacy_agentic_scope
    direct_project = normalize_project_scope(memory.get("project_id"))
    if direct_project:
        return direct_project
    if isinstance(metadata, Mapping):
        return normalize_project_scope(metadata.get("project_id"))
    return ()


def canonical_memory_metadata(memory: Mapping[str, object]) -> JsonObject:
    metadata = memory.get("metadata_json")
    result = dict(metadata) if isinstance(metadata, Mapping) else {}
    scope = memory_project_scope(memory)
    if scope or "project_scope" in memory or (
        isinstance(metadata, Mapping) and "project_scope" in metadata
    ):
        result["project_scope"] = list(scope)
    return result


def expose_memory_project_scope(row: JsonObject) -> JsonObject:
    if "memory_key" in row and "canonical_text" in row:
        row["project_scope"] = list(memory_project_scope(row))
    return row


def project_scopes_overlap(resource_scope: object, requested_scope: object) -> bool:
    requested = set(normalize_project_scope(requested_scope))
    return bool(requested and requested.intersection(normalize_project_scope(resource_scope)))


__all__ = [
    "canonical_memory_metadata",
    "expose_memory_project_scope",
    "memory_project_scope",
    "normalize_project_scope",
    "project_scopes_overlap",
]
