from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
import json
import logging
import math
import os
from hashlib import sha256
from typing import Iterator, Mapping, Protocol, Sequence, TypedDict
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_repositories import JsonObject


logger = logging.getLogger(__name__)


EMBEDDING_VECTOR_DIMENSIONS = 1536
EMBEDDINGS_BASE_URL_ENV = "ALICE_EMBEDDINGS_BASE_URL"
EMBEDDINGS_MODEL_ENV = "ALICE_EMBEDDINGS_MODEL"
EMBEDDINGS_API_KEY_ENV = "ALICE_EMBEDDINGS_API_KEY"
DEFAULT_EMBEDDINGS_TIMEOUT_SECONDS = 30
MAX_EMBEDDINGS_BATCH_SIZE = 128
EMBEDDING_SIGNATURE_METADATA_KEY = "_alice_embedding"
# Version 2 adds the endpoint fingerprint to the signature. Bumping invalidates
# pre-endpoint (v1) vectors so they are re-embedded rather than silently pooled
# across endpoints that share provider/model labels.
EMBEDDING_SIGNATURE_VERSION = 2
EMBEDDING_PREPARATION_ERROR_CODE = "embedding_preparation_failed"
EMBEDDING_PREPARATION_ERROR_MESSAGE = "Memory embedding preparation failed"
EMBEDDING_PERSISTENCE_ERROR_CODE = "embedding_persistence_failed"
EMBEDDING_PERSISTENCE_ERROR_MESSAGE = "Memory embedding persistence failed"


class VNextEmbeddingConfigurationError(ValueError):
    """Raised when embedding input or configuration is invalid."""


class VNextEmbeddingProviderError(RuntimeError):
    """Raised when the embeddings endpoint request fails."""


class EmbeddingProvider(Protocol):
    provider: str
    model: str
    base_url: str

    def embed_text(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]: ...


class SignedMemoryEmbeddingUpdate(TypedDict):
    """Complete storage contract for one v2 content-derived vector."""

    memory_id: str
    vector: list[float]
    provider: str
    model: str
    endpoint: str
    content_sha256: str
    signature_version: int


@dataclass(frozen=True, slots=True)
class DeferredMemoryEmbedding:
    """Immutable id/text snapshot safe to carry across a commit boundary."""

    memory_id: str
    title: str | None
    canonical_text: str | None
    summary: str | None

    @classmethod
    def from_memory(cls, memory: Mapping[str, object]) -> "DeferredMemoryEmbedding":
        memory_id = str(memory.get("id") or "").strip()
        if not memory_id:
            raise VNextEmbeddingConfigurationError(
                "deferred memory embedding inputs require a non-empty id"
            )

        def text_field(name: str) -> str | None:
            value = memory.get(name)
            return value if isinstance(value, str) else None

        return cls(
            memory_id=memory_id,
            title=text_field("title"),
            canonical_text=text_field("canonical_text"),
            summary=text_field("summary"),
        )

    def to_memory_record(self) -> Mapping[str, object]:
        return {
            "id": self.memory_id,
            "title": self.title,
            "canonical_text": self.canonical_text,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class PreparedMemoryEmbedding:
    """Validated vector write prepared without an open database transaction."""

    memory_id: str
    vector: tuple[float, ...]
    provider: str
    model: str
    endpoint: str
    content_sha256: str
    signature_version: int

    def to_update(self) -> SignedMemoryEmbeddingUpdate:
        return {
            "memory_id": self.memory_id,
            "vector": list(self.vector),
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "content_sha256": self.content_sha256,
            "signature_version": self.signature_version,
        }


@dataclass(frozen=True, slots=True)
class MemoryEmbeddingFailure:
    memory_id: str
    error_code: str
    error_message: str


@dataclass(frozen=True, slots=True)
class MemoryEmbeddingPreparation:
    """Provider result ready for a separate, short persistence transaction."""

    prepared: tuple[PreparedMemoryEmbedding, ...]
    failures: tuple[MemoryEmbeddingFailure, ...]
    provider: str | None
    model: str | None


def _canonical_endpoint(base_url: str) -> str:
    """Normalize URL identity without changing case-sensitive route data."""
    raw = base_url.strip()
    if raw == "":
        return ""
    try:
        parsed = urlsplit(raw)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        # Invalid URLs are rejected when the provider request is built. Keep a
        # stable fingerprint here without inventing URL semantics.
        return raw
    if hostname is None:
        return raw.rstrip("/")

    userinfo = parsed.netloc.rsplit("@", 1)[0] + "@" if "@" in parsed.netloc else ""
    canonical_host = hostname.casefold()
    if ":" in canonical_host and not canonical_host.startswith("["):
        canonical_host = f"[{canonical_host}]"
    scheme = parsed.scheme.casefold()
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    port_suffix = "" if port is None or default_port else f":{port}"
    path = parsed.path.rstrip("/")
    return urlunsplit(
        SplitResult(
            scheme,
            f"{userinfo}{canonical_host}{port_suffix}",
            path,
            parsed.query,
            parsed.fragment,
        )
    )


def endpoint_fingerprint(base_url: object) -> str:
    """Stable, non-secret identity for an embedding endpoint.

    Two endpoints that share a provider/model label but serve different
    coordinate spaces (e.g. distinct hosts) must not have their vectors pooled.
    The base_url is hashed rather than stored verbatim so internal endpoint
    URLs never leak into memory metadata. Providers without a base_url yield an
    empty fingerprint (there is no endpoint to distinguish).
    """
    if not isinstance(base_url, str):
        return ""
    normalized = _canonical_endpoint(base_url)
    if normalized == "":
        return ""
    return sha256(normalized.encode("utf-8")).hexdigest()[:16]


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
        normalized_value = float(value)
        if not math.isfinite(normalized_value):
            raise VNextEmbeddingConfigurationError("embedding vectors must contain only finite numbers")
        values.append(normalized_value)
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
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VNextEmbeddingProviderError(f"embeddings request failed: {exc}") from exc
        return _extract_embeddings(response_payload, expected_count=len(texts))


def _extract_embeddings(payload: object, *, expected_count: int) -> list[list[float]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise VNextEmbeddingProviderError("embeddings response did not include a data array")
    rows: list[tuple[int | None, list[float]]] = []
    index_presence: list[bool] = []
    for item in payload["data"]:
        if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
            raise VNextEmbeddingProviderError("embeddings response item did not include an embedding")
        has_index = "index" in item
        item_index = item.get("index") if has_index else None
        if has_index and (isinstance(item_index, bool) or not isinstance(item_index, int)):
            raise VNextEmbeddingProviderError(
                "embeddings response indices must be non-boolean integers"
            )
        index_presence.append(has_index)
        rows.append(
            (
                item_index,
                pad_embedding_vector(item["embedding"]),
            )
        )
    if len(rows) != expected_count:
        raise VNextEmbeddingProviderError(
            f"embeddings response returned {len(rows)} vectors for {expected_count} inputs"
        )
    indexed = [row_index for row_index, _vector in rows if row_index is not None]
    if any(index_presence) and not all(index_presence):
        raise VNextEmbeddingProviderError(
            "embeddings response must either index every vector or omit every index"
        )
    if indexed:
        expected_indices = list(range(expected_count))
        if sorted(indexed) != expected_indices:
            raise VNextEmbeddingProviderError(
                "embeddings response indices must be an exact 0-based permutation of the inputs"
            )
        rows.sort(key=lambda row: row[0] if row[0] is not None else -1)
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


def memory_embedding_content_sha256(memory: Mapping[str, object]) -> str:
    """Digest the exact normalized text used to derive a memory vector."""
    return sha256(memory_embedding_text(memory).encode("utf-8")).hexdigest()


def memory_embedding_signature_is_current(memory: Mapping[str, object]) -> bool:
    """Return whether persisted vector metadata matches the row's current text.

    Lifecycle hooks and database triggers normally clear stale vectors. This
    read-time check remains as a fail-closed guard for legacy adapters, restored
    snapshots, and direct SQL that can bypass those paths.
    """
    metadata = memory.get("metadata_json")
    if not isinstance(metadata, Mapping):
        return False
    signature = metadata.get(EMBEDDING_SIGNATURE_METADATA_KEY)
    if not isinstance(signature, Mapping):
        return False
    stored_digest = signature.get("content_sha256")
    return (
        signature.get("version") == EMBEDDING_SIGNATURE_VERSION
        and isinstance(signature.get("provider"), str)
        and bool(signature.get("provider"))
        and isinstance(signature.get("model"), str)
        and bool(signature.get("model"))
        and isinstance(signature.get("endpoint"), str)
        and isinstance(stored_digest, str)
        and stored_digest == memory_embedding_content_sha256(memory)
    )


def memory_embedding_signature(
    memory: Mapping[str, object],
    *,
    provider: EmbeddingProvider,
) -> JsonObject:
    """Compatibility metadata for a content-derived memory vector."""
    return {
        "version": EMBEDDING_SIGNATURE_VERSION,
        "provider": provider.provider,
        "model": provider.model,
        "endpoint": endpoint_fingerprint(getattr(provider, "base_url", "")),
        "content_sha256": memory_embedding_content_sha256(memory),
    }


def signed_memory_embedding_update(
    memory: Mapping[str, object],
    vector: Sequence[float],
    *,
    provider: EmbeddingProvider,
) -> SignedMemoryEmbeddingUpdate:
    """Build the one complete v2 vector-write contract used by Alice.

    Centralizing this prevents a caller from persisting a vector without the
    provider/model/endpoint/content identity required for safe retrieval.
    The vector is validated and normalized to the storage width before it can
    cross a store boundary.
    """
    try:
        memory_id = str(memory["id"])
    except KeyError as exc:
        raise VNextEmbeddingConfigurationError("memory embedding writes require an id") from exc
    if memory_id.strip() == "":
        raise VNextEmbeddingConfigurationError("memory embedding writes require a non-empty id")
    signature = memory_embedding_signature(memory, provider=provider)
    signature_version = signature["version"]
    if not isinstance(signature_version, int):
        raise VNextEmbeddingConfigurationError("memory embedding signature version must be an integer")
    return {
        "memory_id": memory_id,
        "vector": pad_embedding_vector(vector),
        "provider": str(signature["provider"]),
        "model": str(signature["model"]),
        "endpoint": str(signature["endpoint"]),
        "content_sha256": str(signature["content_sha256"]),
        "signature_version": signature_version,
    }


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
    return (
        attach_memory_embeddings(
            store,
            [memory],
            provider=provider,
            actor_type=actor_type,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        == 1
    )


def _log_embedding_failure(
    store: object,
    memory_id: str,
    *,
    error_code: str,
    error_message: str,
    provider: str | None,
    model: str | None,
    actor_type: str,
    actor_id: str | None,
    trace_id: str | None,
) -> None:
    """Best-effort diagnostic for an already best-effort vector write."""
    try:
        with _embedding_write_savepoint(store):
            append_event(
                store,  # type: ignore[arg-type]
                event_type="memory.embedding_failed",
                actor_type=actor_type,
                actor_id=actor_id,
                target_type="memory",
                target_id=memory_id,
                trace_id=trace_id,
                payload={
                    "error_code": error_code,
                    "error_message": error_message,
                    "provider": provider,
                    "model": model,
                },
            )
    except Exception:
        # Event persistence is diagnostic only. A second store failure must not
        # turn an optional embedding write into a failed memory operation.
        return


@contextmanager
def _embedding_write_savepoint(store: object) -> Iterator[None]:
    """Isolate one optional vector/event write from its caller transaction."""
    conn = getattr(store, "conn", None)
    transaction = getattr(conn, "transaction", None)
    if callable(transaction):
        with transaction():
            yield
        return
    execute = getattr(conn, "execute", None)
    if callable(execute):
        name = "alice_embedding_write"
        execute(f"SAVEPOINT {name}")
        try:
            yield
        except Exception:
            execute(f"ROLLBACK TO SAVEPOINT {name}")
            execute(f"RELEASE SAVEPOINT {name}")
            raise
        else:
            execute(f"RELEASE SAVEPOINT {name}")
        return
    yield


def prepare_memory_embeddings(
    inputs: Sequence[DeferredMemoryEmbedding],
    *,
    provider: EmbeddingProvider | None = None,
) -> MemoryEmbeddingPreparation:
    """Call the provider in batches without touching a database connection."""
    resolved_provider = provider if provider is not None else get_embedding_provider()
    if resolved_provider is None:
        return MemoryEmbeddingPreparation((), (), None, None)
    embeddable = [
        (item, text)
        for item in inputs
        if (text := memory_embedding_text(item.to_memory_record())) != ""
    ]
    prepared: list[PreparedMemoryEmbedding] = []
    failures: list[MemoryEmbeddingFailure] = []
    for batch_start in range(0, len(embeddable), MAX_EMBEDDINGS_BATCH_SIZE):
        batch = embeddable[batch_start : batch_start + MAX_EMBEDDINGS_BATCH_SIZE]
        try:
            vectors = resolved_provider.embed_batch([text for _item, text in batch])
            if len(vectors) != len(batch):
                raise VNextEmbeddingProviderError(
                    f"embedding provider returned {len(vectors)} vectors for {len(batch)} inputs"
                )
        except Exception:
            logger.exception(
                "memory embedding preparation batch failed error_code=%s",
                EMBEDDING_PREPARATION_ERROR_CODE,
            )
            failures.extend(
                MemoryEmbeddingFailure(
                    item.memory_id,
                    EMBEDDING_PREPARATION_ERROR_CODE,
                    EMBEDDING_PREPARATION_ERROR_MESSAGE,
                )
                for item, _text in batch
            )
            continue

        for (item, _text), vector in zip(batch, vectors, strict=True):
            try:
                update = signed_memory_embedding_update(
                    item.to_memory_record(), vector, provider=resolved_provider
                )
                prepared.append(
                    PreparedMemoryEmbedding(
                        memory_id=update["memory_id"],
                        vector=tuple(update["vector"]),
                        provider=update["provider"],
                        model=update["model"],
                        endpoint=update["endpoint"],
                        content_sha256=update["content_sha256"],
                        signature_version=update["signature_version"],
                    )
                )
            except Exception:
                logger.exception(
                    "memory embedding signature preparation failed memory_id=%s error_code=%s",
                    item.memory_id,
                    EMBEDDING_PREPARATION_ERROR_CODE,
                )
                failures.append(
                    MemoryEmbeddingFailure(
                        item.memory_id,
                        EMBEDDING_PREPARATION_ERROR_CODE,
                        EMBEDDING_PREPARATION_ERROR_MESSAGE,
                    )
                )
    return MemoryEmbeddingPreparation(
        tuple(prepared),
        tuple(failures),
        resolved_provider.provider,
        resolved_provider.model,
    )


def persist_prepared_memory_embeddings(
    store: object,
    preparation: MemoryEmbeddingPreparation,
    *,
    actor_type: str = "system",
    actor_id: str | None = None,
    trace_id: str | None = None,
) -> int:
    """Best-effort persistence half of the two-phase embedding contract."""
    update_memory_embedding = getattr(store, "update_memory_embedding", None)
    if not callable(update_memory_embedding):
        return 0
    for failure in preparation.failures:
        _log_embedding_failure(
            store,
            failure.memory_id,
            error_code=failure.error_code,
            error_message=failure.error_message,
            provider=preparation.provider,
            model=preparation.model,
            actor_type=actor_type,
            actor_id=actor_id,
            trace_id=trace_id,
        )
    attached_count = 0
    for prepared in preparation.prepared:
        try:
            with _embedding_write_savepoint(store):
                updated = update_memory_embedding(**prepared.to_update())
            # Bundled stores use the signed content digest as an optimistic
            # compare-and-set token.  ``None`` means the memory changed after
            # provider preparation, so the stale vector must be discarded.
            if updated is not None:
                attached_count += 1
        except Exception:
            logger.exception(
                "memory embedding persistence failed memory_id=%s error_code=%s",
                prepared.memory_id,
                EMBEDDING_PERSISTENCE_ERROR_CODE,
            )
            _log_embedding_failure(
                store,
                prepared.memory_id,
                error_code=EMBEDDING_PERSISTENCE_ERROR_CODE,
                error_message=EMBEDDING_PERSISTENCE_ERROR_MESSAGE,
                provider=prepared.provider,
                model=prepared.model,
                actor_type=actor_type,
                actor_id=actor_id,
                trace_id=trace_id,
            )
    return attached_count


def persist_deferred_memory_embeddings_best_effort(
    inputs: Sequence[DeferredMemoryEmbedding],
    *,
    store_context: Callable[[], AbstractContextManager[object]],
    provider: EmbeddingProvider | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    trace_id: str | None = None,
) -> int:
    """Prepare vectors without a connection and persist after the primary commit.

    Embeddings are an optional derived index. Once the authoritative memory
    transaction has committed, failure to acquire the follow-up connection,
    write a vector, or commit that follow-up transaction must not turn the
    successful memory operation into an error. Store-level failures are logged
    through ``memory.embedding_failed`` when possible; connection/commit
    failures are logged through the process logger because no usable store may
    remain.
    """

    if not inputs:
        return 0
    try:
        preparation = prepare_memory_embeddings(inputs, provider=provider)
    except Exception as exc:
        logger.warning(
            "best-effort memory embedding preparation failed: %s: %s",
            type(exc).__name__,
            exc,
        )
        return 0
    if not preparation.prepared and not preparation.failures:
        return 0
    try:
        with store_context() as store:
            return persist_prepared_memory_embeddings(
                store,
                preparation,
                actor_type=actor_type,
                actor_id=actor_id,
                trace_id=trace_id,
            )
    except Exception as exc:
        logger.warning(
            "best-effort memory embedding persistence failed after the primary commit: %s: %s",
            type(exc).__name__,
            exc,
        )
        return 0


def attach_memory_embeddings(
    store: object,
    memories: Sequence[Mapping[str, object]],
    *,
    provider: EmbeddingProvider | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    trace_id: str | None = None,
) -> int:
    """Best-effort batched embed-on-write for memory rows.

    Provider calls are bounded to ``MAX_EMBEDDINGS_BATCH_SIZE``. A failed
    provider batch or individual store write is logged for the affected rows
    and never blocks the already-completed memory writes.
    """
    update_memory_embedding = getattr(store, "update_memory_embedding", None)
    if not callable(update_memory_embedding):
        return 0
    try:
        inputs = tuple(DeferredMemoryEmbedding.from_memory(memory) for memory in memories)
    except VNextEmbeddingConfigurationError:
        inputs = tuple(
            DeferredMemoryEmbedding.from_memory(memory)
            for memory in memories
            if str(memory.get("id") or "").strip()
        )
    preparation = prepare_memory_embeddings(inputs, provider=provider)
    return persist_prepared_memory_embeddings(
        store,
        preparation,
        actor_type=actor_type,
        actor_id=actor_id,
        trace_id=trace_id,
    )


__all__ = [
    "DEFAULT_EMBEDDINGS_TIMEOUT_SECONDS",
    "EMBEDDING_VECTOR_DIMENSIONS",
    "EMBEDDINGS_API_KEY_ENV",
    "EMBEDDINGS_BASE_URL_ENV",
    "EMBEDDINGS_MODEL_ENV",
    "EMBEDDING_SIGNATURE_METADATA_KEY",
    "EMBEDDING_SIGNATURE_VERSION",
    "EMBEDDING_PREPARATION_ERROR_CODE",
    "EMBEDDING_PREPARATION_ERROR_MESSAGE",
    "EMBEDDING_PERSISTENCE_ERROR_CODE",
    "EMBEDDING_PERSISTENCE_ERROR_MESSAGE",
    "DeferredMemoryEmbedding",
    "EmbeddingProvider",
    "MemoryEmbeddingFailure",
    "MemoryEmbeddingPreparation",
    "PreparedMemoryEmbedding",
    "SignedMemoryEmbeddingUpdate",
    "endpoint_fingerprint",
    "MAX_EMBEDDINGS_BATCH_SIZE",
    "OpenAICompatibleEmbeddingProvider",
    "VNextEmbeddingConfigurationError",
    "VNextEmbeddingProviderError",
    "attach_memory_embedding",
    "attach_memory_embeddings",
    "get_embedding_provider",
    "memory_embedding_content_sha256",
    "memory_embedding_signature_is_current",
    "memory_embedding_text",
    "memory_embedding_signature",
    "pad_embedding_vector",
    "persist_prepared_memory_embeddings",
    "persist_deferred_memory_embeddings_best_effort",
    "prepare_memory_embeddings",
    "signed_memory_embedding_update",
]
