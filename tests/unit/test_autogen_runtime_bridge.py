from pathlib import Path
from typing import Any

import scripts.run_phase11_autogen_runtime_bridge as runtime_bridge


REPO_ROOT = Path(__file__).resolve().parents[2]


class _FakeResponse:
    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"assistant":{"text":"ok"}}'


def test_runtime_request_uses_local_identity_header_without_bearer_auth(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(http_request, *, timeout):  # noqa: ANN001
        captured["headers"] = {
            key.lower(): value for key, value in http_request.header_items()
        }
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(runtime_bridge, "urlopen", fake_urlopen)

    payload = runtime_bridge._request_json(
        method="POST",
        url="http://127.0.0.1:8000/v1/runtime/invoke",
        user_id="00000000-0000-0000-0000-000000000001",
        payload={"message": "hello"},
        timeout_seconds=7,
    )

    assert payload == {"assistant": {"text": "ok"}}
    assert captured["headers"]["x-alicebot-user-id"] == (
        "00000000-0000-0000-0000-000000000001"
    )
    assert "authorization" not in captured["headers"]
    assert captured["timeout"] == 7


def test_autogen_bridge_forwards_only_retained_provider_runtime_fields(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_request_json(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "assistant": {"text": "Runtime reply"},
            "trace": {"request_id": "trace-1"},
            "metadata": {"provider": "local"},
        }

    monkeypatch.setattr(runtime_bridge, "_request_json", fake_request_json)
    client = runtime_bridge.AutoGenAliceRuntimeClient(
        api_base_url="http://127.0.0.1:8000/",
        user_id="00000000-0000-0000-0000-000000000001",
        provider_id="provider-1",
        thread_id="thread-1",
        model="  model-1  ",
    )

    result = client.create(
        messages=[
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "latest"},
        ]
    )

    assert captured["url"] == "http://127.0.0.1:8000/v1/runtime/invoke"
    assert captured["user_id"] == "00000000-0000-0000-0000-000000000001"
    assert captured["payload"] == {
        "provider_id": "provider-1",
        "thread_id": "thread-1",
        "message": "latest",
        "model": "model-1",
    }
    assert result["content"] == "Runtime reply"


def test_autogen_bridge_has_no_retired_model_pack_seam() -> None:
    source = (
        REPO_ROOT / "scripts" / "run_phase11_autogen_runtime_bridge.py"
    ).read_text(encoding="utf-8")

    assert "pack_id" not in source
    assert "pack_version" not in source
    assert "--pack-id" not in source
    assert "--pack-version" not in source
    assert "model-pack" not in source.lower()
    assert "session_token" not in source
    assert "Authorization" not in source
    assert "Bearer" not in source
    assert "X-AliceBot-User-Id" in source
