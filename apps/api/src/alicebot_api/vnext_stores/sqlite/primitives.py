"""SQLite vNext store serialization and identity primitives."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject


def _sorted_field_names(record: JsonObject) -> list[str]:
    return sorted(str(key) for key in record)


def _utc_now_iso() -> str:
    # timespec pins the fractional part: isoformat() omits it entirely when
    # microsecond == 0, and a '...59Z' string sorts lexicographically AFTER
    # every '...59.000123Z' sibling, corrupting timestamp ordering for the
    # ~1e-6 of writes that land on a whole second.
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _iso_or_none(value: object | None) -> str | None:
    """Normalize timestamps to ISO-8601 UTC TEXT with a trailing ``Z``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _iso_or_now(value: object | None) -> str:
    return _iso_or_none(value) or _utc_now_iso()


def _new_id(value: object | None) -> str:
    if value is None or value == "":
        return str(uuid4())
    return str(value)


def _uuid_text(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_object_text(value: object | None) -> str:
    if value is None:
        value = {}
    return json.dumps(json_safe(value), ensure_ascii=False, separators=(",", ":"))


def _json_list_text(value: object | None) -> str:
    if value is None:
        value = []
    return json.dumps(json_safe(value), ensure_ascii=False, separators=(",", ":"))


for _primitive in (
    _sorted_field_names,
    _utc_now_iso,
    _iso_or_none,
    _iso_or_now,
    _new_id,
    _uuid_text,
    _json_object_text,
    _json_list_text,
):
    _primitive.__module__ = "alicebot_api.sqlite_store"
    _primitive.__qualname__ = _primitive.__name__
del _primitive
