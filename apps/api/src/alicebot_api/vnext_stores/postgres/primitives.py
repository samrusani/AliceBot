"""PostgreSQL vNext store serialization primitives."""

from __future__ import annotations

from psycopg.types.json import Jsonb

from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject


def _sorted_field_names(record: JsonObject) -> list[str]:
    return sorted(str(key) for key in record)


def _json_object(value: object | None) -> Jsonb:
    if value is None:
        value = {}
    return Jsonb(_json_safe(value))


def _json_list(value: object | None) -> Jsonb:
    if value is None:
        value = []
    return Jsonb(_json_safe(value))


def _json_safe(value: object) -> object:
    return json_safe(value)


for _primitive in (_sorted_field_names, _json_object, _json_list, _json_safe):
    _primitive.__module__ = "alicebot_api.vnext_store"
    _primitive.__qualname__ = _primitive.__name__
del _primitive
