from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from alicebot_api.contracts import ModelInvocationRequest, ModelInvocationResponse, ModelUsagePayload
from alicebot_api.provider_security import validate_provider_base_url
from alicebot_api.response_generation import ModelInvocationError


def build_auth_headers(*, auth_mode: str, api_key: str) -> dict[str, str]:
    mode = auth_mode.strip().lower()
    if mode == "none":
        return {}
    if mode == "bearer":
        token = api_key.strip()
        if token == "":  # nosec B105
            raise ModelInvocationError("provider api_key is required when auth_mode is bearer")
        return {"Authorization": f"Bearer {token}"}
    raise ModelInvocationError(f"unsupported provider auth_mode: {auth_mode}")


def request_json(
    *,
    method: str,
    base_url: str,
    path: str,
    timeout_seconds: int,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validated_base_url = validate_provider_base_url(base_url)
    normalized_path = path if path.startswith("/") else f"/{path}"
    endpoint = validated_base_url.rstrip("/") + normalized_path
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = Request(endpoint, data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
            raw_payload = response.read()
    except HTTPError as exc:
        raise ModelInvocationError(f"model provider returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ModelInvocationError("model provider request failed") from exc

    try:
        parsed_payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ModelInvocationError("model provider returned invalid JSON") from exc

    if not isinstance(parsed_payload, dict):
        raise ModelInvocationError("model provider returned invalid JSON")
    return parsed_payload


def prompt_sections_to_messages(request: ModelInvocationRequest) -> list[dict[str, str]]:
    sections = {section.name: section.content for section in request.prompt.sections}
    return [
        {"role": "system", "content": sections["system"]},
        {"role": "developer", "content": sections["developer"]},
        {"role": "user", "content": f"[CONTEXT]\n{sections['context']}"},
        {"role": "user", "content": f"[CONVERSATION]\n{sections['conversation']}"},
    ]


def parse_ollama_models(payload: dict[str, Any]) -> list[str]:
    models_payload = payload.get("models")
    if not isinstance(models_payload, list):
        raise ModelInvocationError("ollama model enumeration payload is invalid")
    model_names: set[str] = set()
    for model_payload in models_payload:
        if not isinstance(model_payload, dict):
            continue
        raw_name = model_payload.get("name")
        if isinstance(raw_name, str) and raw_name.strip():
            model_names.add(raw_name.strip())
    return sorted(model_names)


def parse_llamacpp_models(payload: dict[str, Any]) -> list[str]:
    data_payload = payload.get("data")
    if not isinstance(data_payload, list):
        raise ModelInvocationError("llamacpp model enumeration payload is invalid")
    model_names: set[str] = set()
    for model_payload in data_payload:
        if not isinstance(model_payload, dict):
            continue
        raw_name = model_payload.get("id")
        if isinstance(raw_name, str) and raw_name.strip():
            model_names.add(raw_name.strip())
    return sorted(model_names)


def parse_ollama_invoke_response(*, request: ModelInvocationRequest, payload: dict[str, Any]) -> ModelInvocationResponse:
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ModelInvocationError("ollama response did not include message payload")
    output_text = message.get("content")
    if not isinstance(output_text, str) or output_text.strip() == "":
        raise ModelInvocationError("ollama response did not include assistant output text")
    done = payload.get("done")
    finish_reason = "completed" if done is True else "incomplete"
    prompt_tokens = payload.get("prompt_eval_count")
    completion_tokens = payload.get("eval_count")
    total_tokens = (
        prompt_tokens + completion_tokens
        if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int)
        else None
    )
    usage: ModelUsagePayload = {
        "input_tokens": prompt_tokens if isinstance(prompt_tokens, int) else None,
        "output_tokens": completion_tokens if isinstance(completion_tokens, int) else None,
        "total_tokens": total_tokens,
    }
    return ModelInvocationResponse(
        provider=request.provider,
        model=request.model,
        response_id=None,
        finish_reason=finish_reason,
        output_text=output_text,
        usage=usage,
    )


def parse_llamacpp_invoke_response(
    *,
    request: ModelInvocationRequest,
    payload: dict[str, Any],
) -> ModelInvocationResponse:
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise ModelInvocationError("llamacpp response did not include choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ModelInvocationError("llamacpp response did not include choices")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ModelInvocationError("llamacpp response did not include message payload")
    output_text = message.get("content")
    if not isinstance(output_text, str) or output_text.strip() == "":
        raise ModelInvocationError("llamacpp response did not include assistant output text")
    raw_finish_reason = first_choice.get("finish_reason")
    finish_reason = "completed" if raw_finish_reason in {"stop", "completed", "eos"} else "incomplete"
    usage_payload = payload.get("usage")
    if isinstance(usage_payload, dict):
        usage: ModelUsagePayload = {
            "input_tokens": (
                usage_payload.get("prompt_tokens")
                if isinstance(usage_payload.get("prompt_tokens"), int)
                else None
            ),
            "output_tokens": (
                usage_payload.get("completion_tokens")
                if isinstance(usage_payload.get("completion_tokens"), int)
                else None
            ),
            "total_tokens": (
                usage_payload.get("total_tokens")
                if isinstance(usage_payload.get("total_tokens"), int)
                else None
            ),
        }
    else:
        usage = {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    response_id = payload.get("id") if isinstance(payload.get("id"), str) else None
    return ModelInvocationResponse(
        provider=request.provider,
        model=request.model,
        response_id=response_id,
        finish_reason=finish_reason,
        output_text=output_text,
        usage=usage,
    )
