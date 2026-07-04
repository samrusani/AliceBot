from __future__ import annotations

import io
import json

import pytest

import alicebot_api.vnext_embeddings as vnext_embeddings
from alicebot_api.vnext_embeddings import (
    EMBEDDING_VECTOR_DIMENSIONS,
    OpenAICompatibleEmbeddingProvider,
    VNextEmbeddingConfigurationError,
    VNextEmbeddingProviderError,
    attach_memory_embedding,
    get_embedding_provider,
    memory_embedding_text,
    pad_embedding_vector,
)


class _FakeResponse(io.BytesIO):
    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_pad_embedding_vector_zero_pads_to_storage_width() -> None:
    padded = pad_embedding_vector([0.5, -0.25])

    assert len(padded) == EMBEDDING_VECTOR_DIMENSIONS
    assert padded[0] == 0.5
    assert padded[1] == -0.25
    assert set(padded[2:]) == {0.0}


def test_pad_embedding_vector_keeps_full_width_vectors_unchanged() -> None:
    vector = [0.001] * EMBEDDING_VECTOR_DIMENSIONS

    assert pad_embedding_vector(vector) == vector


def test_pad_embedding_vector_rejects_oversized_vectors() -> None:
    with pytest.raises(VNextEmbeddingConfigurationError, match="1537 dimensions"):
        pad_embedding_vector([0.1] * (EMBEDDING_VECTOR_DIMENSIONS + 1))


def test_pad_embedding_vector_rejects_empty_and_non_numeric_vectors() -> None:
    with pytest.raises(VNextEmbeddingConfigurationError, match="must not be empty"):
        pad_embedding_vector([])
    with pytest.raises(VNextEmbeddingConfigurationError, match="only numbers"):
        pad_embedding_vector([0.1, "bad"])  # type: ignore[list-item]


def test_get_embedding_provider_returns_none_when_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_API_KEY", raising=False)

    assert get_embedding_provider() is None

    monkeypatch.setenv("ALICE_EMBEDDINGS_BASE_URL", "http://localhost:11434/v1")
    assert get_embedding_provider() is None

    monkeypatch.setenv("ALICE_EMBEDDINGS_MODEL", "nomic-embed-text")
    provider = get_embedding_provider()
    assert provider is not None
    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.model == "nomic-embed-text"
    assert provider.api_key is None

    monkeypatch.setenv("ALICE_EMBEDDINGS_API_KEY", "sk-local")
    provider_with_key = get_embedding_provider()
    assert provider_with_key is not None
    assert provider_with_key.api_key == "sk-local"


def test_embed_batch_posts_openai_shape_and_pads_vectors(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        body = json.dumps(
            {
                "data": [
                    {"index": 1, "embedding": [0.2, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.3]},
                ]
            }
        ).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr(vnext_embeddings, "urlopen", fake_urlopen)
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="http://localhost:11434/v1/",
        model="nomic-embed-text",
        api_key="sk-local",
    )

    vectors = provider.embed_batch(["first text", "second text"])

    assert captured["url"] == "http://localhost:11434/v1/embeddings"
    assert captured["payload"] == {"model": "nomic-embed-text", "input": ["first text", "second text"]}
    assert dict(captured["headers"]).get("Authorization") == "Bearer sk-local"
    assert len(vectors) == 2
    assert vectors[0][:2] == [0.1, 0.3]
    assert vectors[1][:2] == [0.2, 0.4]
    assert all(len(vector) == EMBEDDING_VECTOR_DIMENSIONS for vector in vectors)


def test_embed_batch_omits_authorization_header_without_api_key(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        del timeout
        captured["headers"] = {key.casefold(): value for key, value in request.header_items()}
        return _FakeResponse(json.dumps({"data": [{"index": 0, "embedding": [0.1]}]}).encode("utf-8"))

    monkeypatch.setattr(vnext_embeddings, "urlopen", fake_urlopen)
    provider = OpenAICompatibleEmbeddingProvider(base_url="http://localhost:1234/v1", model="local-embed")

    provider.embed_text("local server text")

    assert "authorization" not in captured["headers"]


def test_embed_batch_raises_provider_error_on_bad_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        vnext_embeddings,
        "urlopen",
        lambda request, timeout: _FakeResponse(json.dumps({"unexpected": True}).encode("utf-8")),
    )
    provider = OpenAICompatibleEmbeddingProvider(base_url="http://localhost:1234/v1", model="local-embed")

    with pytest.raises(VNextEmbeddingProviderError, match="data array"):
        provider.embed_text("text")


def test_embed_batch_rejects_empty_inputs_and_oversized_batches() -> None:
    provider = OpenAICompatibleEmbeddingProvider(base_url="http://localhost:1234/v1", model="local-embed")

    assert provider.embed_batch([]) == []
    with pytest.raises(VNextEmbeddingConfigurationError, match="non-empty strings"):
        provider.embed_batch(["ok", "   "])
    with pytest.raises(VNextEmbeddingConfigurationError, match="limited to"):
        provider.embed_batch(["text"] * (vnext_embeddings.MAX_EMBEDDINGS_BATCH_SIZE + 1))


def test_memory_embedding_text_joins_title_canonical_text_and_summary() -> None:
    text = memory_embedding_text(
        {"title": "Coffee", "canonical_text": "Sam prefers pour over.", "summary": "Coffee"}
    )

    assert text == "Coffee\nSam prefers pour over."
    assert memory_embedding_text({"title": None, "canonical_text": "  "}) == ""


class _AttachStore:
    def __init__(self) -> None:
        self.embeddings: list[tuple[str, list[float]]] = []
        self.events: list[dict[str, object]] = []

    def update_memory_embedding(self, *, memory_id: str, vector: list[float]) -> dict[str, object]:
        self.embeddings.append((memory_id, vector))
        return {"id": memory_id}

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event


class _StubProvider:
    provider = "stub"
    model = "stub-embedding"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def embed_text(self, text: str) -> list[float]:
        if self.fail:
            raise VNextEmbeddingProviderError("embeddings request failed: connection refused")
        return pad_embedding_vector([0.5, 0.5])

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


def test_attach_memory_embedding_noops_without_provider(monkeypatch) -> None:
    monkeypatch.delenv("ALICE_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("ALICE_EMBEDDINGS_MODEL", raising=False)
    store = _AttachStore()

    attached = attach_memory_embedding(store, {"id": "memory-1", "canonical_text": "Fact."})

    assert attached is False
    assert store.embeddings == []
    assert store.events == []


def test_attach_memory_embedding_writes_vector_with_provider() -> None:
    store = _AttachStore()

    attached = attach_memory_embedding(
        store,
        {"id": "memory-1", "title": "Fact", "canonical_text": "Fact text."},
        provider=_StubProvider(),
    )

    assert attached is True
    assert store.embeddings[0][0] == "memory-1"
    assert len(store.embeddings[0][1]) == EMBEDDING_VECTOR_DIMENSIONS


def test_attach_memory_embedding_logs_event_but_never_blocks_on_failure() -> None:
    store = _AttachStore()

    attached = attach_memory_embedding(
        store,
        {"id": "memory-1", "canonical_text": "Fact text."},
        provider=_StubProvider(fail=True),
        actor_type="agent",
        actor_id="hermes",
    )

    assert attached is False
    assert store.embeddings == []
    assert store.events[-1]["event_type"] == "memory.embedding_failed"
    assert store.events[-1]["actor_id"] == "hermes"
    assert "connection refused" in str(store.events[-1]["payload_json"])
