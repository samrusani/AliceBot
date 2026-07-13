from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json


# These values identify an execution attempt, not a logical workflow request.
# They must never make a retry publish a second set of durable domain objects.
_VOLATILE_ATTEMPT_KEYS = frozenset(
    {
        "agent_run_id",
        "run_id",
        "scheduler_run_id",
        "trace_id",
    }
)


def _logical_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _logical_value(child) for key, child in value.items() if str(key) not in _VOLATILE_ATTEMPT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_logical_value(child) for child in value]
    return value


def logical_workflow_digest(payload: object) -> str:
    """Hash the semantic request while recursively excluding attempt identity."""

    encoded = json.dumps(
        _logical_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = ["logical_workflow_digest"]
