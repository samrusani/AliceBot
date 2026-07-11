"""Content-version evidence shared by review-gated memory workflows."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Mapping

from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject


def memory_content_digest(memory: Mapping[str, object]) -> str:
    encoded = json.dumps(
        {
            "title": memory.get("title"),
            "canonical_text": memory.get("canonical_text"),
            "summary": memory.get("summary"),
            "value": json_safe(memory.get("value")),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def memory_version_snapshot(memory: Mapping[str, object]) -> JsonObject:
    return {
        "id": str(memory.get("id")),
        "status": str(memory.get("status") or ""),
        "updated_at": str(memory.get("updated_at") or ""),
        "content_digest": memory_content_digest(memory),
    }


def memory_matches_snapshot(memory: Mapping[str, object], snapshot: Mapping[str, object]) -> bool:
    current = memory_version_snapshot(memory)
    return all(current.get(key) == snapshot.get(key) for key in current)


__all__ = ["memory_content_digest", "memory_matches_snapshot", "memory_version_snapshot"]

