"""Minimal OpenAI-compatible ``/chat/completions`` client for the harness.

Stdlib-only (``urllib``), mirroring the HTTP style of
``alicebot_api.vnext_embeddings.OpenAICompatibleEmbeddingProvider``. Retries
transient failures (429 and 5xx, honouring ``Retry-After``) with exponential
backoff so parallel workers stay rate-limit friendly.

Env contract (see docs/plans/longmemeval.md):

- answer model:  ``ALICE_LME_MODEL_BASE_URL`` / ``ALICE_LME_MODEL`` /
  ``ALICE_LME_MODEL_API_KEY``
- judge model:   ``ALICE_LME_JUDGE_BASE_URL`` / ``ALICE_LME_JUDGE_MODEL`` /
  ``ALICE_LME_JUDGE_API_KEY`` (each falls back to the answer-model value)
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import random
import time
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


MODEL_BASE_URL_ENV = "ALICE_LME_MODEL_BASE_URL"
MODEL_NAME_ENV = "ALICE_LME_MODEL"
MODEL_API_KEY_ENV = "ALICE_LME_MODEL_API_KEY"
JUDGE_BASE_URL_ENV = "ALICE_LME_JUDGE_BASE_URL"
JUDGE_NAME_ENV = "ALICE_LME_JUDGE_MODEL"
JUDGE_API_KEY_ENV = "ALICE_LME_JUDGE_API_KEY"

DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_MAX_RETRIES = 4
DEFAULT_RETRY_BASE_SECONDS = 2.0
_RETRYABLE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})


class ChatCompletionError(RuntimeError):
    """Raised when the chat endpoint fails after all retries."""


def redacted_base_url(value: str) -> str:
    """Endpoint identity without credentials, query tokens, or fragments."""
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        if not parsed.scheme or hostname is None:
            raise ValueError("endpoint must be an absolute URL")
        host = f"[{hostname}]" if ":" in hostname else hostname
        netloc = f"{host}:{parsed.port}" if parsed.port is not None else host
        return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    except ValueError:
        # Keep malformed/local adapter strings attributable without exposing
        # their content in an evidence artifact.
        import hashlib

        return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True, slots=True)
class ChatModelConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS

    def redacted(self) -> dict[str, object]:
        """Config for reports: never includes the API key."""
        return {
            "base_url": redacted_base_url(self.base_url),
            "model": self.model,
            "api_key_configured": self.api_key is not None,
}


@dataclass(frozen=True, slots=True)
class ChatCompletionResult:
    text: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_seconds: float
    retries: int = 0


def _env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def model_config_from_env() -> ChatModelConfig | None:
    """The answer-generation model, or ``None`` when unconfigured."""
    base_url = _env(MODEL_BASE_URL_ENV)
    model = _env(MODEL_NAME_ENV)
    if base_url is None or model is None:
        return None
    return ChatModelConfig(base_url=base_url.rstrip("/"), model=model, api_key=_env(MODEL_API_KEY_ENV))


def judge_config_from_env() -> ChatModelConfig | None:
    """The judge model; each field falls back to the answer-model env."""
    base_url = _env(JUDGE_BASE_URL_ENV) or _env(MODEL_BASE_URL_ENV)
    model = _env(JUDGE_NAME_ENV) or _env(MODEL_NAME_ENV)
    if base_url is None or model is None:
        return None
    api_key = _env(JUDGE_API_KEY_ENV) or _env(MODEL_API_KEY_ENV)
    return ChatModelConfig(base_url=base_url.rstrip("/"), model=model, api_key=api_key)


def _retry_delay_seconds(attempt: int, *, base: float, retry_after: str | None) -> float:
    if retry_after is not None:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return base * (2**attempt) + random.uniform(0.0, base)


def parse_chat_completion_payload(payload: object) -> tuple[str, int | None, int | None]:
    """Extract ``(text, prompt_tokens, completion_tokens)`` or raise."""
    if not isinstance(payload, dict):
        raise ChatCompletionError("chat response was not a JSON object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ChatCompletionError("chat response did not include choices")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ChatCompletionError("chat response choice did not include message content")
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    prompt_tokens = usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"), int) else None
    completion_tokens = usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"), int) else None
    return message["content"], prompt_tokens, completion_tokens


def chat_completion(
    config: ChatModelConfig,
    messages: Sequence[dict[str, str]],
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> ChatCompletionResult:
    safe_base_url = redacted_base_url(config.base_url)

    def sanitized_error_text(value: object) -> str:
        text = str(value)
        # urllib exceptions and provider error bodies can echo the configured
        # endpoint. Never let URL userinfo, query tokens, or fragments reach a
        # checkpoint through the runner's generic exception serialization.
        return text.replace(config.base_url, safe_base_url)

    body: dict[str, object] = {
        "model": config.model,
        "messages": list(messages),
        "temperature": temperature,
    }
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    headers = {"Content-Type": "application/json"}
    if config.api_key is not None:
        headers["Authorization"] = f"Bearer {config.api_key}"
    request = Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    started = time.monotonic()
    last_error: str = "no attempt was made"
    for attempt in range(config.max_retries + 1):
        try:
            with urlopen(request, timeout=config.timeout_seconds) as response:
                payload = json.loads(response.read())
            text, prompt_tokens, completion_tokens = parse_chat_completion_payload(payload)
            return ChatCompletionResult(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_seconds=time.monotonic() - started,
                retries=attempt,
            )
        except HTTPError as exc:
            last_error = f"HTTP {exc.code} from {safe_base_url}"
            if exc.code not in _RETRYABLE_HTTP_CODES or attempt == config.max_retries:
                detail = ""
                try:
                    detail = sanitized_error_text(
                        exc.read().decode("utf-8", errors="replace")[:500]
                    )
                except OSError:  # pragma: no cover - best-effort error body
                    pass
                raise ChatCompletionError(f"{last_error}: {detail}") from exc
            delay = _retry_delay_seconds(
                attempt,
                base=config.retry_base_seconds,
                retry_after=exc.headers.get("Retry-After") if exc.headers else None,
            )
            time.sleep(delay)
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = f"chat request to {safe_base_url} failed: {sanitized_error_text(exc)}"
            if attempt == config.max_retries:
                raise ChatCompletionError(last_error) from exc
            time.sleep(_retry_delay_seconds(attempt, base=config.retry_base_seconds, retry_after=None))
    raise ChatCompletionError(last_error)  # pragma: no cover - loop always returns or raises


__all__ = [
    "ChatCompletionError",
    "ChatCompletionResult",
    "ChatModelConfig",
    "JUDGE_API_KEY_ENV",
    "JUDGE_BASE_URL_ENV",
    "JUDGE_NAME_ENV",
    "MODEL_API_KEY_ENV",
    "MODEL_BASE_URL_ENV",
    "MODEL_NAME_ENV",
    "chat_completion",
    "judge_config_from_env",
    "model_config_from_env",
    "parse_chat_completion_payload",
    "redacted_base_url",
]
