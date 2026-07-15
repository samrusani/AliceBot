from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest

import scripts.run_phase11_local_provider_e2e as local_provider_e2e
import scripts.run_phase14_openai_compatible_smoke as openai_compatible_smoke


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_USER_ID = "00000000-0000-0000-0000-000000000001"


class _FakeResponse:
    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"status":"ok"}'


@pytest.mark.parametrize(
    "module",
    (local_provider_e2e, openai_compatible_smoke),
)
def test_provider_demo_requests_use_local_identity_without_bearer_auth(
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(http_request: Any, *, timeout: int) -> _FakeResponse:
        captured["headers"] = {
            key.lower(): value for key, value in http_request.header_items()
        }
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    payload = module._request_json(
        method="POST",
        url="http://127.0.0.1:8000/v1/workspaces/bootstrap",
        user_id=LOCAL_USER_ID,
        payload={},
    )

    assert payload == {"status": "ok"}
    assert captured["headers"]["x-alicebot-user-id"] == LOCAL_USER_ID
    assert "authorization" not in captured["headers"]
    assert captured["timeout"] == 30


def test_local_provider_e2e_bootstraps_before_provider_calls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request_json(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        url = kwargs["url"]
        if url.endswith("/v1/workspaces/bootstrap"):
            return {"workspace": {"bootstrap_status": "ready"}}
        if url.endswith("/v1/providers/ollama/register"):
            return {
                "provider": {"id": "provider-1"},
                "capabilities": {"health_status": "ok"},
            }
        if url.endswith("/v1/providers/test"):
            return {"result": {"status": "succeeded"}}
        if url.endswith("/v1/runtime/invoke"):
            return {"assistant": {"text": "runtime ok"}}
        raise AssertionError(f"unexpected request: {kwargs}")

    monkeypatch.setattr(local_provider_e2e, "_request_json", fake_request_json)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_phase11_local_provider_e2e.py",
            "--api-base-url",
            "http://alice.test/",
            "--user-id",
            LOCAL_USER_ID,
            "--thread-id",
            "thread-1",
            "--provider",
            "ollama",
            "--model",
            "model-1",
        ],
    )

    assert local_provider_e2e.main() == 0

    assert [call["url"] for call in calls] == [
        "http://alice.test/v1/workspaces/bootstrap",
        "http://alice.test/v1/providers/ollama/register",
        "http://alice.test/v1/providers/test",
        "http://alice.test/v1/runtime/invoke",
    ]
    assert all(call["user_id"] == LOCAL_USER_ID for call in calls)
    assert calls[0]["payload"] == {}
    assert calls[1]["payload"]["metadata"] == {
        "source": "local_self_hosted_e2e"
    }
    assert json.loads(capsys.readouterr().out)["runtime_assistant"] == {
        "text": "runtime ok"
    }


def test_openai_compatible_smoke_bootstraps_before_provider_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request_json(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        url = kwargs["url"]
        if url.endswith("/v1/workspaces/bootstrap"):
            return {"workspace": {"bootstrap_status": "ready"}}
        if url.endswith("/v1/providers"):
            return {
                "provider": {"id": "provider-1"},
                "capabilities": {"health_status": "ok"},
            }
        if url.endswith("/v1/providers/test"):
            return {"result": {"status": "succeeded"}}
        if url.endswith("/v1/runtime/invoke"):
            return {"assistant": {"text": "runtime ok"}}
        raise AssertionError(f"unexpected request: {kwargs}")

    monkeypatch.setattr(openai_compatible_smoke, "_request_json", fake_request_json)

    result = openai_compatible_smoke._run_flow(
        api_base_url="http://alice.test/",
        user_id=LOCAL_USER_ID,
        thread_id="thread-1",
        provider_base_url="http://provider.test/v1",
        display_name="Provider",
        model="model-1",
        test_prompt="test",
        message="invoke",
    )

    assert [call["url"] for call in calls] == [
        "http://alice.test/v1/workspaces/bootstrap",
        "http://alice.test/v1/providers",
        "http://alice.test/v1/providers/test",
        "http://alice.test/v1/runtime/invoke",
    ]
    assert all(call["user_id"] == LOCAL_USER_ID for call in calls)
    assert calls[0]["payload"] == {}
    assert result["runtime_assistant"] == {"text": "runtime ok"}


def test_provider_demo_scripts_have_no_hosted_session_auth_seam() -> None:
    for relative_path in (
        "scripts/run_phase11_local_provider_e2e.py",
        "scripts/run_phase14_openai_compatible_smoke.py",
    ):
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "session_token" not in source
        assert "--session-token" not in source
        assert "Authorization" not in source
        assert "Bearer" not in source
        assert "X-AliceBot-User-Id" in source
        assert "/v1/workspaces/bootstrap" in source
        assert "phase14_local_self_hosted_e2e" not in source
