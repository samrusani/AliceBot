from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Request

from alicebot_api.config import Settings
from alicebot_api.store import JsonObject, JsonValue


LOGGER = logging.getLogger("alicebot_api.main")


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        output: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            output[key] = _json_value(item)
        return output
    raise ValueError(f"value of type {type(value).__name__} is not JSON-compatible")


def _json_object(value: object) -> JsonObject:
    normalized = _json_value(value)
    if not isinstance(normalized, dict):
        raise ValueError("expected a JSON object")
    return normalized


AUTH_USER_HEADER = "X-AliceBot-User-Id"


def _resolve_authenticated_user_id(settings: Settings, request: Request) -> UUID | None:
    if settings.auth_user_id != "":
        return UUID(settings.auth_user_id)

    header_value = request.headers.get(AUTH_USER_HEADER)
    if header_value is None or header_value.strip() == "":
        if settings.app_env in {"development", "test"}:
            return None
        raise ValueError(
            "request authentication is not configured; set ALICEBOT_AUTH_USER_ID or provide X-AliceBot-User-Id"
        )

    try:
        return UUID(header_value)
    except ValueError as exc:
        raise ValueError("X-AliceBot-User-Id must be a valid UUID") from exc


def _request_client_identifier(request: Request, settings: Settings) -> str:
    peer_host = ""
    if request.client is not None:
        peer_host = (request.client.host or "").strip()

    if settings.trust_proxy_headers and peer_host != "" and peer_host in settings.trusted_proxy_ips:
        forwarded_for = request.headers.get("x-forwarded-for", "").strip()
        if forwarded_for != "":
            first_hop = forwarded_for.split(",", maxsplit=1)[0].strip()
            if first_hop != "":
                return first_hop

    if peer_host == "":
        return "unknown"
    return peer_host


def _resolve_authenticated_v1_user_id(settings: Settings, request: Request) -> UUID:
    user_account_id = _resolve_authenticated_user_id(settings, request)
    if user_account_id is None:
        raise ValueError("local identity is required; set ALICEBOT_AUTH_USER_ID or provide X-AliceBot-User-Id")
    return user_account_id
