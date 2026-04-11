from __future__ import annotations

from typing import Any

from alicebot_api.store import JsonObject


_VLLM_NUMERIC_PASSTHROUGH_FIELDS = {
    "temperature",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
}
_VLLM_INT_PASSTHROUGH_FIELDS = {
    "max_tokens",
    "n",
    "seed",
}


def extract_vllm_invoke_passthrough_options(*, adapter_options: JsonObject) -> dict[str, Any]:
    """Return bounded vLLM invoke passthrough options from persisted adapter options."""

    passthrough_payload = adapter_options.get("invoke_passthrough")
    if not isinstance(passthrough_payload, dict):
        return {}

    bounded: dict[str, Any] = {}

    for key in _VLLM_NUMERIC_PASSTHROUGH_FIELDS:
        coerced = _coerce_float(passthrough_payload.get(key))
        if coerced is not None:
            bounded[key] = coerced

    for key in _VLLM_INT_PASSTHROUGH_FIELDS:
        coerced = _coerce_int(passthrough_payload.get(key))
        if coerced is not None:
            bounded[key] = coerced

    stop_payload = passthrough_payload.get("stop")
    if isinstance(stop_payload, str) and stop_payload.strip() != "":
        bounded["stop"] = stop_payload
    elif isinstance(stop_payload, list):
        stops = [item for item in stop_payload if isinstance(item, str) and item.strip() != ""]
        if len(stops) > 0:
            bounded["stop"] = stops

    return bounded


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None
