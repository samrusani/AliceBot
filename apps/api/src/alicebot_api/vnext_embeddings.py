from __future__ import annotations

import json
import os
from typing import Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


EMBEDDING_VECTOR_DIMENSIONS = 1536
EMBEDDINGS_BASE_URL_ENV = "ALICE_EMBEDDINGS_BASE_URL"
EMBEDDINGS_MODEL_ENV = "ALICE_EMBEDDINGS_MODEL"
EMBEDDINGS_API_KEY_ENV = "ALICE_EMBEDDINGS_API_KEY"
DEFAULT_EMBEDDINGS_TIMEOUT_SECONDS = 30
MAX_EMBEDDINGS_BATCH_SIZE = 128


class VNextEmbeddingConfigurationError(ValueError):
    """Raised when embedding input or configuration is invalid."""


class VNextEmbeddingProviderError(RuntimeError):
    """Raised when the embeddings endpoint request fails."""


class EmbeddingProvider(Protocol):
    provider: str
    model: str

    def embed_text(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]: ...


def pad_embedding_vector(
    vector: Sequence[float],
    *,
    dimensions: int = EMBEDDING_VECTOR_DIMENSIONS,
) -> list[float]:
    """Zero-pad an embedding to the storage width.

    Zero-padding preserves cosine similarity between vectors from the same
    model, so smaller local models can share the 1536-dim column.
    """
    values: list[float] = []
    for value in vector:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VNextEmbeddingConfigurationError("embedding vectors must contain only numbers")
        values.append(float(value))
    if not values:
        raise VNextEmbeddingConfigurationError("embedding vectors must not be empty")
    if len(values) > dimensions:
        raise VNextEmbeddingConfigurationError(
            f"embedding has {len(values)} dimensions but the storage column holds {dimensions}; "
            "configure an embedding model that emits at most "
            f"{dimensions} dimensions"
        )
    if len(values) < dimensions:
        values.extend(0.0 for _ in range(dimensions - len(values)))
    return values


class OpenAICompatibleEmbeddingProvider:
    """Embeddings client for any OpenAI-compatible ``/embeddings`` endpoint.

    Works against OpenAI, Ollama's ``/v1``, LM Studio, and vLLM. Uses only the
    standard library, matching the vNext model-intelligence HTTP style.
    """

    provider = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: int = DEFAULT_EMBEDDINGS_TIMEOUT_SECONDS,
    ) -> None:
        normalized_base_url = base_url.strip().rstrip("/")
        normalized_model = model.strip()
        if normalized_base_url == "":
            raise VNextEmbeddingConfigurationError("embeddings base_url must not be empty")
        if normalized_model == "":
            raise VNextEmbeddingConfigurationError("embeddings model must not be empty")
        self.base_url = normalized_base_url
        self.model = normalized_model
        self.api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        self.timeout_seconds = timeout_seconds

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if len(texts) > MAX_EMBEDDINGS_BATCH_SIZE:
            raise VNextEmbeddingConfigurationError(
                f"embedding batches are limited to {MAX_EMBEDDINGS_BATCH_SIZE} texts per request"
            )
        for text in texts:
            if not isinstance(text, str) or text.strip() == "":
                raise VNextEmbeddingConfigurationError("embedding input texts must be non-empty strings")
        payload: JsonObject = {"model": self.model, "input": list(texts)}
        headers = {"Content-Type": "application/json"}
        if self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read())
        except HTTPError as exc:
            raise VNextEmbeddingProviderError(f"embeddings endpoint returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise VNextEmbeddingProviderError(f"embeddings request failed: {exc}") from exc
        return _extract_embeddings(response_payload, expected_count=len(texts))


def _extract_embeddings(payload: object, *, expected_count: int) -> list[list[float]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise VNextEmbeddingProviderError("embeddings response did not include a data array")
    rows: list[tuple[int, list[float]]] = []
    for index, item in enumerate(payload["data"]):
        if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
            raise VNextEmbeddingProviderError("embeddings response item did not include an embedding")
        item_index = item.get("index")
        rows.append(
            (
                item_index if isinstance(item_index, int) else index,
                pad_embedding_vector(item["embedding"]),
            )
        )
    if len(rows) != expected_count:
        raise VNextEmbeddingProviderError(
            f"embeddings response returned {len(rows)} vectors for {expected_count} inputs"
        )
    rows.sort(key=lambda row: row[0])
    return [vector for _index, vector in rows]


def get_embedding_provider() -> OpenAICompatibleEmbeddingProvider | None:
    """Build the configured embedding provider, or ``None`` when unconfigured.

    Unconfigured means full-text-search-only retrieval; there is no fake or
    hash-based embedding fallback.
    """
    base_url = os.environ.get(EMBEDDINGS_BASE_URL_ENV, "").strip()
    model = os.environ.get(EMBEDDINGS_MODEL_ENV, "").strip()
    if base_url == "" or model == "":
        return None
    api_key = os.environ.get(EMBEDDINGS_API_KEY_ENV, "").strip() or None
    return OpenAICompatibleEmbeddingProvider(base_url=base_url, model=model, api_key=api_key)


def memory_embedding_text(memory: Mapping[str, object]) -> str:
    """The text embedded for a memory row: the same fields as ``search_tsv``."""
    parts: list[str] = []
    for key in ("title", "canonical_text", "summary"):
        value = memory.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n".join(dict.fromkeys(parts))


def attach_memory_embedding(
    store: object,
    memory: Mapping[str, object],
    *,
    provider: EmbeddingProvider | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    trace_id: str | None = None,
) -> bool:
    """Best-effort embed-on-write for a memory row.

    Embedding failure never blocks the memory write: failures are logged to
    the event log and the ``embedding_vector`` column stays NULL for the
    ``alicebot vnext memories backfill-embeddings`` pass.
    """
    resolved_provider = provider if provider is not None else get_embedding_provider()
    if resolved_provider is None:
        return False
    update_memory_embedding = getattr(store, "update_memory_embedding", None)
    if not callable(update_memory_embedding):
        return False
    text = memory_embedding_text(memory)
    if text == "":
        return False
    try:
        vector = resolved_provider.embed_text(text)
        update_memory_embedding(memory_id=str(memory["id"]), vector=vector)
        return True
    except (VNextEmbeddingConfigurationError, VNextEmbeddingProviderError) as exc:
        append_event(
            store,  # type: ignore[arg-type]
            event_type="memory.embedding_failed",
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(memory.get("id")),
            trace_id=trace_id,
            payload={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "provider": resolved_provider.provider,
                "model": resolved_provider.model,
            },
        )
        return False


__all__ = [
    "DEFAULT_EMBEDDINGS_TIMEOUT_SECONDS",
    "EMBEDDING_VECTOR_DIMENSIONS",
    "EMBEDDINGS_API_KEY_ENV",
    "EMBEDDINGS_BASE_URL_ENV",
    "EMBEDDINGS_MODEL_ENV",
    "EmbeddingProvider",
    "MAX_EMBEDDINGS_BATCH_SIZE",
    "OpenAICompatibleEmbeddingProvider",
    "VNextEmbeddingConfigurationError",
    "VNextEmbeddingProviderError",
    "attach_memory_embedding",
    "get_embedding_provider",
    "memory_embedding_text",
    "pad_embedding_vector",
]
